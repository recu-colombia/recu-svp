from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import get_settings


def create_db_engine() -> Engine:
    settings = get_settings()
    try:
        return create_engine(settings.sqlalchemy_database_uri, pool_pre_ping=True)
    except ModuleNotFoundError:
        return create_engine("sqlite+pysqlite:///:memory:")
