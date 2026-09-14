from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Clase base para los modelos persistentes."""


engine = create_engine(
    str(settings.database_url),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db_session() -> Generator[Session, None, None]:
    """Entrega una sesión transaccional y garantiza su cierre."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
