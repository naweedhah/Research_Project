from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def apply_rls_context(db: Session, facility_id: str | None, role: str | None, bypass: bool = False) -> None:
    """Set request-scoped PostgreSQL GUCs used by RLS policies."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    db.execute(text("SELECT set_config('app.rls_bypass', :v, true)"), {"v": "1" if bypass else "0"})
    db.execute(text("SELECT set_config('app.facility_id', :v, true)"), {"v": facility_id or ""})
    db.execute(text("SELECT set_config('app.user_role', :v, true)"), {"v": role or ""})


@event.listens_for(engine, "connect")
def _register_uuid(dbapi_connection, connection_record):  # noqa: ARG001
    return
