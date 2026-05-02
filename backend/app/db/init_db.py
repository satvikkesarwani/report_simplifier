from typing import Optional

from sqlalchemy import inspect, text

from app.db.session import Base, get_engine
from app.models import entities  # noqa: F401


def init_db(database_url: Optional[str] = None) -> None:
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
    _apply_compatibility_migrations(engine)


def _apply_compatibility_migrations(engine) -> None:
    inspector = inspect(engine)
    if "reports" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("reports")}
        if "user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE reports ADD COLUMN user_id INTEGER"))
