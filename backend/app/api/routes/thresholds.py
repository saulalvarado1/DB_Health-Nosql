from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.api.presenters import threshold_profile_response
from app.api.schemas.thresholds import (
    ThresholdProfileResponse,
    UpdateThresholdRuleRequest,
)
from app.infrastructure.persistence.models import User
from app.services.thresholds import ThresholdManagementService

router = APIRouter(prefix="/databases")


@router.get("/{database_id}/thresholds", response_model=ThresholdProfileResponse)
def get_threshold_profile(
    database_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ThresholdProfileResponse:
    profile = ThresholdManagementService(session).get_for_owner(
        database_id=database_id,
        owner_id=current_user.id,
    )
    return threshold_profile_response(profile)


@router.put(
    "/{database_id}/thresholds/{metric_code}",
    response_model=ThresholdProfileResponse,
)
def update_threshold_rule(
    database_id: UUID,
    metric_code: str,
    request: UpdateThresholdRuleRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ThresholdProfileResponse:
    profile = ThresholdManagementService(session).update_rule(
        database_id=database_id,
        owner_id=current_user.id,
        metric_code=metric_code,
        warning_value=request.warning_value,
        critical_value=request.critical_value,
    )
    return threshold_profile_response(profile)
