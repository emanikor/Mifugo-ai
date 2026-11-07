"""
SMS Alerts (Bush Link SMS) endpoints.

Design choices worth calling out:
  - Broadcasting is a MANUAL action (POST /sms-broadcast/{price_entry_id}),
    not automatic on every price entry. SMS costs real money per message
    and a slow/unreachable gateway shouldn't be able to block or slow down
    the core act of saving a price. An official/agent chooses when to
    broadcast, similar to a daily digest rather than a blast per entry.
  - Self-service opt-in (texting "SUBSCRIBE <region> <species>" or "STOP")
    is processed via an explicit "check inbox" action, not a background
    poller — this keeps the system's behavior visible and debuggable
    rather than a hidden cron job silently mutating the subscriber list.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, PriceEntry, Region, SmsSubscriber, Species
from app.schemas import (
    SmsBroadcastResult,
    SmsInboxResult,
    SmsSubscriberCreate,
    SmsSubscriberOut,
)
from app.security import get_current_agent
from app.sms_client import SmsGatewayUnavailableError, fetch_inbox, send_sms

router = APIRouter(prefix="/sms", tags=["sms"])

VALID_ROLES = ("pastoralist", "buyer")


# ---- Subscriber management ----

@router.post("/subscribers", response_model=SmsSubscriberOut, status_code=201)
def register_subscriber(
    payload: SmsSubscriberCreate,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    if payload.subscriber_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"subscriber_role must be one of {VALID_ROLES}")
    if payload.region_id is not None and db.get(Region, payload.region_id) is None:
        raise HTTPException(status_code=400, detail="Unknown region")
    if payload.species_id is not None and db.get(Species, payload.species_id) is None:
        raise HTTPException(status_code=400, detail="Unknown species")

    existing = (
        db.query(SmsSubscriber)
        .filter(
            SmsSubscriber.phone_number == payload.phone_number,
            SmsSubscriber.region_id == payload.region_id,
            SmsSubscriber.species_id == payload.species_id,
        )
        .first()
    )
    if existing:
        existing.is_active = True
        existing.full_name = payload.full_name or existing.full_name
        db.commit()
        db.refresh(existing)
        return existing

    subscriber = SmsSubscriber(
        phone_number=payload.phone_number,
        full_name=payload.full_name,
        region_id=payload.region_id,
        species_id=payload.species_id,
        subscriber_role=payload.subscriber_role,
        source="agent_registered",
        registered_by=agent.id,
    )
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)
    return subscriber


@router.get("/subscribers", response_model=list[SmsSubscriberOut])
def list_subscribers(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    query = db.query(SmsSubscriber)
    if is_active is not None:
        query = query.filter(SmsSubscriber.is_active == is_active)
    return query.order_by(SmsSubscriber.created_at.desc()).all()


@router.patch("/subscribers/{subscriber_id}/unsubscribe", response_model=SmsSubscriberOut)
def unsubscribe(
    subscriber_id: int,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    subscriber = db.get(SmsSubscriber, subscriber_id)
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    subscriber.is_active = False
    db.commit()
    db.refresh(subscriber)
    return subscriber


# ---- Self-service opt-in via inbound SMS ----

def _parse_command(text: str, db: Session) -> tuple[str, Optional[Region], Optional[Species]]:
    """Parses 'SUBSCRIBE <region> <species>' or 'STOP'. Region/species
    matching is case-insensitive substring matching against known names —
    same approach as rag/retriever.py, kept simple deliberately."""
    text_upper = text.strip().upper()

    if text_upper == "STOP" or text_upper.startswith("STOP "):
        return "stop", None, None

    if text_upper.startswith("SUBSCRIBE"):
        parts = text.strip().split()
        region = None
        species = None
        for part in parts[1:]:
            if region is None:
                match = db.query(Region).filter(Region.name.ilike(f"%{part}%")).first()
                if match:
                    region = match
                    continue
            if species is None:
                match = db.query(Species).filter(Species.name.ilike(f"%{part}%")).first()
                if match:
                    species = match
        return "subscribe", region, species

    return "unrecognized", None, None


@router.post("/subscribers/check-inbox", response_model=SmsInboxResult)
def check_inbox(
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    try:
        messages = fetch_inbox()
    except SmsGatewayUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    new_subs = 0
    unsubs = 0
    unrecognized = 0

    for msg in messages:
        phone = msg.get("Number", "")
        text = msg.get("Text", "")
        action, region, species = _parse_command(text, db)

        if action == "stop":
            subs = db.query(SmsSubscriber).filter(SmsSubscriber.phone_number == phone).all()
            for s in subs:
                s.is_active = False
            unsubs += len(subs)
        elif action == "subscribe":
            existing = (
                db.query(SmsSubscriber)
                .filter(
                    SmsSubscriber.phone_number == phone,
                    SmsSubscriber.region_id == (region.id if region else None),
                    SmsSubscriber.species_id == (species.id if species else None),
                )
                .first()
            )
            if existing:
                existing.is_active = True
            else:
                db.add(
                    SmsSubscriber(
                        phone_number=phone,
                        region_id=region.id if region else None,
                        species_id=species.id if species else None,
                        source="self_service",
                    )
                )
            new_subs += 1
        else:
            unrecognized += 1

    db.commit()

    return SmsInboxResult(
        messages_processed=len(messages),
        new_subscriptions=new_subs,
        unsubscribes=unsubs,
        unrecognized=unrecognized,
        detail=f"Processed {len(messages)} message(s).",
    )


# ---- Manual broadcast ----

@router.post("/broadcast/{price_entry_id}", response_model=SmsBroadcastResult)
def broadcast_price(
    price_entry_id: int,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    entry = db.get(PriceEntry, price_entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Price entry not found")
    if entry.outlier_status != "valid":
        raise HTTPException(
            status_code=400,
            detail="Only validated (non-flagged) prices can be broadcast via SMS.",
        )

    subscribers = (
        db.query(SmsSubscriber)
        .filter(
            SmsSubscriber.is_active.is_(True),
            (SmsSubscriber.region_id.is_(None)) | (SmsSubscriber.region_id == entry.region_id),
            (SmsSubscriber.species_id.is_(None)) | (SmsSubscriber.species_id == entry.species_id),
        )
        .all()
    )

    region = db.get(Region, entry.region_id)
    species = db.get(Species, entry.species_id)
    message = (
        f"Mifugo AI: {species.name.title()} price in {region.name} — "
        f"{entry.price_kes:,} KES ({entry.market_date}). Reply STOP to unsubscribe."
    )

    sent = 0
    try:
        for sub in subscribers:
            send_sms(sub.phone_number, message)
            sent += 1
    except SmsGatewayUnavailableError as exc:
        # Report partial progress rather than a bare 503 — the official
        # broadcasting this needs to know how many actually went out.
        raise HTTPException(
            status_code=503,
            detail=f"{str(exc)} ({sent} of {len(subscribers)} sent before failure)",
        )

    return SmsBroadcastResult(
        recipients_attempted=len(subscribers),
        recipients_sent=sent,
        detail=f"Broadcast sent to {sent} of {len(subscribers)} matching subscriber(s).",
    )
