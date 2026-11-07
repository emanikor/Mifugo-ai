"""
Disease report endpoints. Follows the exact same never-delete, always-
reviewable pattern as app/routers/prices.py: an agent's report is saved
and visible immediately, and only an official/admin can move it to
'confirmed' or 'false_alarm' — a wrongly-suppressed real outbreak is a far
worse failure mode than a false alarm sitting flagged for review.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, DiseaseReport, Region, Species
from app.schemas import DiseaseReportCreate, DiseaseReportOut
from app.security import get_current_agent

router = APIRouter(prefix="/disease-reports", tags=["disease"])

VALID_SEVERITIES = ("low", "medium", "high", "critical")


@router.post("", response_model=DiseaseReportOut, status_code=201)
def create_disease_report(
    payload: DiseaseReportCreate,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400, detail=f"severity must be one of {VALID_SEVERITIES}"
        )
    region = db.get(Region, payload.region_id)
    species = db.get(Species, payload.species_id)
    if region is None or species is None:
        raise HTTPException(status_code=400, detail="Unknown region or species")

    report = DiseaseReport(
        region_id=payload.region_id,
        species_id=payload.species_id,
        agent_id=agent.id,
        report_date=payload.report_date,
        disease_name=payload.disease_name,
        symptoms=payload.symptoms,
        affected_count=payload.affected_count,
        severity=payload.severity,
        review_status="reported",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("", response_model=list[DiseaseReportOut])
def list_disease_reports(
    region_id: Optional[int] = None,
    species_id: Optional[int] = None,
    review_status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    query = db.query(DiseaseReport)
    if region_id is not None:
        query = query.filter(DiseaseReport.region_id == region_id)
    if species_id is not None:
        query = query.filter(DiseaseReport.species_id == species_id)
    if review_status is not None:
        query = query.filter(DiseaseReport.review_status == review_status)
    return (
        query.order_by(DiseaseReport.report_date.desc())
        .limit(min(limit, 500))
        .all()
    )


@router.patch("/{report_id}/review", response_model=DiseaseReportOut)
def review_disease_report(
    report_id: int,
    new_status: str,
    review_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    if agent.role not in ("official", "admin"):
        raise HTTPException(status_code=403, detail="Requires official or admin role")
    if new_status not in ("reported", "confirmed", "false_alarm"):
        raise HTTPException(status_code=400, detail="Invalid review status")

    report = db.get(DiseaseReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Disease report not found")

    report.review_status = new_status
    if review_notes:
        report.review_notes = review_notes
    db.commit()
    db.refresh(report)
    return report
