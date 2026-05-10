# src/data/database.py
from __future__ import annotations
import contextlib
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "option_valuation.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_instance: "DatabaseManager | None" = None


class DatabaseManager:
    def __init__(self, db_path: Path = _DB_PATH):
        url = f"sqlite:///{db_path}"
        self.engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(self.engine, "connect")
        def _set_pragmas(conn, _):
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")

        self._Session = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False
        )

    def create_tables(self) -> None:
        # models をここでインポートして循環回避
        from src.data.models import Base
        Base.metadata.create_all(self.engine)

    @contextlib.contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session: Session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def get_db_manager() -> DatabaseManager:
    global _instance
    if _instance is None:
        _instance = DatabaseManager()
        _instance.create_tables()
    return _instance


@contextlib.contextmanager
def get_session() -> Generator[Session, None, None]:
    with get_db_manager().get_session() as session:
        yield session
