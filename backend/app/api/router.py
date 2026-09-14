from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.authentication import router as authentication_router
from app.api.routes.health import router as health_router
from app.api.routes.monitored_databases import router as monitored_databases_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(authentication_router, tags=["authentication"])
api_router.include_router(monitored_databases_router, tags=["monitored databases"])
api_router.include_router(alerts_router, tags=["alerts"])
