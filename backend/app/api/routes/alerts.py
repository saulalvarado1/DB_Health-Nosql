from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.api.schemas.alerts import AlertResponse
from app.infrastructure.persistence.models import User
from app.services.alerts import AlertManagementService

router = APIRouter(prefix="/alerts")

AlertStatusFilter = Literal["open", "acknowledged", "resolved"]


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    status_filter: AlertStatusFilter | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AlertResponse]:
    alerts = AlertManagementService(session).list_for_owner(current_user.id, status_filter)
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlertResponse:
    alert = AlertManagementService(session).acknowledge(alert_id, current_user.id)
    return AlertResponse.model_validate(alert)
