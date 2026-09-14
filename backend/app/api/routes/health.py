from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_session

router = APIRouter()


@router.get("/health", summary="Estado de la API")
def get_api_health() -> dict[str, str]:
    return {"status": "ok", "service": "db-health-monitor"}


@router.get("/health/ready", summary="Disponibilidad de dependencias internas")
def get_readiness(session: Session = Depends(get_session)) -> dict[str, str]:
    """Comprueba PostgreSQL sin exponer errores de conexión ni credenciales."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El almacenamiento interno no está disponible.",
        ) from error
    return {"status": "ready", "service": "db-health-monitor"}
