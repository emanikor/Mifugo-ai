"""
Computed alert feed for Milestone 4.

Deliberately NOT a stored table: an "alert" here is just a way of framing
data that already lives in climate_bulletins and disease_reports. Storing
a separate alerts table would mean keeping two things in sync (the
underlying bulletin/report, and an alert record about it) for no benefit —
per the project's own scope-control rule to avoid hidden complexity.

An alert is:
  - A region's MOST RECENT climate bulletin, if its drought_status isn't
    'normal' (older non-normal bulletins are superseded, not alerts anymore).
  - Any disease report still in 'reported' or 'confirmed' status (i.e. not
    yet dismissed as a false alarm) — these stay "active" until reviewed,
    however old, since an unresolved report should not quietly age out.
"""
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ClimateBulletin, DiseaseReport, Region
from app.schemas import AlertOut

# Ties disease severity to a consistent ordering with drought status for
# sorting the combined feed by urgency, worst first.
_SEVERITY_RANK = {
    "emergency": 4, "critical": 4,
    "alarm": 3, "high": 3,
    "alert": 2, "medium": 2,
    "normal": 0, "low": 1,
}


def get_active_alerts(db: Session) -> list[AlertOut]:
    alerts: list[AlertOut] = []

    # --- Drought alerts: latest bulletin per region, if not 'normal' ---
    # Subquery: most recent bulletin_date per region.
    latest_dates = (
        db.query(
            ClimateBulletin.region_id,
            func.max(ClimateBulletin.bulletin_date).label("max_date"),
        )
        .group_by(ClimateBulletin.region_id)
        .subquery()
    )
    latest_bulletins = (
        db.query(ClimateBulletin)
        .join(
            latest_dates,
            (ClimateBulletin.region_id == latest_dates.c.region_id)
            & (ClimateBulletin.bulletin_date == latest_dates.c.max_date),
        )
        .all()
    )
    for bulletin in latest_bulletins:
        if bulletin.drought_status == "normal":
            continue
        region = db.get(Region, bulletin.region_id)
        alerts.append(
            AlertOut(
                type="drought",
                severity=bulletin.drought_status,
                region_id=bulletin.region_id,
                region_name=region.name if region else "Unknown",
                title=f"Drought status: {bulletin.drought_status.upper()}",
                detail=(
                    f"{bulletin.rainfall_mm} mm rainfall reported"
                    if bulletin.rainfall_mm is not None
                    else "No rainfall figure reported"
                ) + f" (source: {bulletin.source})",
                date=bulletin.bulletin_date,
            )
        )

    # --- Disease alerts: anything not yet dismissed ---
    open_reports = (
        db.query(DiseaseReport)
        .filter(DiseaseReport.review_status != "false_alarm")
        .order_by(DiseaseReport.report_date.desc())
        .all()
    )
    for report in open_reports:
        region = db.get(Region, report.region_id)
        status_label = (
            "Confirmed" if report.review_status == "confirmed" else "Unverified report"
        )
        alerts.append(
            AlertOut(
                type="disease",
                severity=report.severity,
                region_id=report.region_id,
                region_name=region.name if region else "Unknown",
                title=f"{status_label}: {report.disease_name}",
                detail=(
                    f"{report.affected_count} animals affected — "
                    if report.affected_count is not None
                    else ""
                ) + (report.symptoms or "No symptom details provided"),
                date=report.report_date,
            )
        )

    alerts.sort(key=lambda a: a.date, reverse=True)
    alerts.sort(key=lambda a: _SEVERITY_RANK.get(a.severity, 0), reverse=True)
    return alerts
