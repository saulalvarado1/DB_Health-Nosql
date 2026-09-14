import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.domain.errors import (
    AuthenticationError,
    ConfigurationError,
    DomainError,
    ResourceConflictError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)


def create_application() -> FastAPI:
    logging.basicConfig(level=settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="API para monitoreo de bases de datos NoSQL.",
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
        status_code = {
            AuthenticationError: status.HTTP_401_UNAUTHORIZED,
            ResourceConflictError: status.HTTP_409_CONFLICT,
            ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
            ConfigurationError: status.HTTP_400_BAD_REQUEST,
            ServiceUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
        }.get(type(error), status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_application()
