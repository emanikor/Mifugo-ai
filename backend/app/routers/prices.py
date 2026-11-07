"""
Price entry endpoints — the core agent workflow:
  agent logs in -> selects region/species -> enters price -> outlier check
  runs immediately -> result (valid/flagged/rejected) is shown back to them.

Agents see the outlier result right away rather than finding out later,
so they can double check a genuinely unusual-but-correct price on the spot
(e.g. a drought-driven price spike) instead of it just vanishing from
reports silently.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, PriceEntry, Region, Species
from app.outlier_detection import evaluate_new_price
from app.schemas import PriceEntryCreate, PriceEntryOut, RegionOut, SpeciesOut
from app.security import get_current_agent

router = APIRouter(tags=["prices"])


# ---- Lookups (populate dropdowns in the React form) ----

@router.get("/regions", response_model=list[RegionOut])
def list_regions(db: Session = Depends(get_db)):
    return db.query(Region).order_by(Region.name).all()


@router.get("/species", response_model=list[SpeciesOut])
def list_species(db: Session = Depends(get_db)):
    return db.query(Species).order_by(Species.name).all()


# ---- Price entry ----

@router.post("/prices", response_model=PriceEntryOut, status_code=status.HTTP_201_CREATED)
def create_price_entry(
    payload: PriceEntryCreate,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    region = db.get(Region, payload.region_id)
    species = db.get(Species, payload.species_id)
    if region is None or species is None:
        raise HTTPException(status_code=400, detail="Unknown region or species")

    result = evaluate_new_price(
        db,
        region_id=payload.region_id,
        species_id=payload.species_id,
        price_kes=payload.price_kes,
    )

    entry = PriceEntry(
        region_id=payload.region_id,
        species_id=payload.species_id,
        agent_id=agent.id,
        price_kes=payload.price_kes,
        market_date=payload.market_date,
        notes=payload.notes,
        outlier_status=result.status,
        outlier_reason=result.reason,
        outlier_score=result.score,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/prices", response_model=list[PriceEntryOut])
def list_price_entries(
    region_id: Optional[int] = None,
    species_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Recent price entries, optionally filtered. Used by the dashboard view
    and by officials reviewing flagged entries."""
    query = db.query(PriceEntry)
    if region_id is not None:
        query = query.filter(PriceEntry.region_id == region_id)
    if species_id is not None:
        query = query.filter(PriceEntry.species_id == species_id)
    if status_filter is not None:
        query = query.filter(PriceEntry.outlier_status == status_filter)

    return (
        query.order_by(PriceEntry.market_date.desc(), PriceEntry.entered_at.desc())
        .limit(min(limit, 500))
        .all()
    )


@router.patch("/prices/{entry_id}/review", response_model=PriceEntryOut)
def review_flagged_entry(
    entry_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    # Only officials/admins can override an outlier decision — agents
    # entering data shouldn't be able to un-flag their own submissions.
    agent: Agent = Depends(get_current_agent),
):
    if agent.role not in ("official", "admin"):
        raise HTTPException(status_code=403, detail="Requires official or admin role")
    if new_status not in ("valid", "flagged", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status")

    entry = db.get(PriceEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Price entry not found")

    entry.outlier_status = new_status
    entry.outlier_reason = (
        f"{entry.outlier_reason or ''} [Manually reviewed by {agent.username}, "
        f"set to '{new_status}']"
    ).strip()
    db.commit()
    db.refresh(entry)
    return entry
