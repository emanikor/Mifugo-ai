"""
Unified alerts feed — combines active drought status and unresolved
disease reports into one endpoint the dashboard/ticker can poll. See
app/alerts.py for why this is computed rather than stored.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alerts import get_active_alerts
from app.database import get_db
from app.models import Agent
from app.schemas import AlertOut
from app.security import get_current_agent

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    return get_active_alerts(db)
