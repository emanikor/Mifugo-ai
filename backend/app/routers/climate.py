"""
Climate bulletin endpoints — sync-when-online, use-offline (see
app/models.py ClimateBulletin docstring). Any authenticated agent can log
an observation or transcribe an official bulletin; there's no review
workflow here (unlike disease reports) since a rainfall figure/drought
status doesn't carry the same false-alarm risk a disease report does.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, ClimateBulletin, Region
from app.schemas import ClimateBulletinCreate, ClimateBulletinOut
from app.security import get_current_agent

router = APIRouter(prefix="/climate", tags=["climate"])

VALID_STATUSES = ("normal", "alert", "alarm", "emergency")


@router.post("", response_model=ClimateBulletinOut, status_code=201)
def log_climate_bulletin(
    payload: ClimateBulletinCreate,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    if payload.drought_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"drought_status must be one of {VALID_STATUSES}",
        )
    region = db.get(Region, payload.region_id)
    if region is None:
        raise HTTPException(status_code=400, detail="Unknown region")

    bulletin = ClimateBulletin(
        region_id=payload.region_id,
        agent_id=agent.id,
        bulletin_date=payload.bulletin_date,
        drought_status=payload.drought_status,
        rainfall_mm=payload.rainfall_mm,
        temperature_c=payload.temperature_c,
        source=payload.source,
        notes=payload.notes,
    )
    db.add(bulletin)
    db.commit()
    db.refresh(bulletin)
    return bulletin


@router.get("", response_model=list[ClimateBulletinOut])
def list_climate_bulletins(
    region_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    query = db.query(ClimateBulletin)
    if region_id is not None:
        query = query.filter(ClimateBulletin.region_id == region_id)
    return (
        query.order_by(ClimateBulletin.bulletin_date.desc())
        .limit(min(limit, 500))
        .all()
    )
