import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
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
    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
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

    @app.on_event("startup")
    def run_migrations_on_startup() -> None:
        try:
            import os

            from alembic import command
            from alembic.config import Config

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ini_path = os.path.join(base_dir, "alembic.ini")
            if os.path.exists(ini_path):
                cfg = Config(ini_path)
                command.upgrade(cfg, "head")
        except Exception:  # noqa: BLE001, S110
            pass

    @app.on_event("startup")
    def startup_telegram_listener() -> None:
        token = (
            settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else None
        )
        if token:
            from app.services.telegram_bot import TelegramBotListener

            listener = TelegramBotListener(bot_token=token)
            listener.start_background()

    return app


app = create_application()
