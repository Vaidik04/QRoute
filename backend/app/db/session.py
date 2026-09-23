from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings

# Create engine for database operations
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Register SQLite spatial function stubs for environments without Spatialite C extension
@event.listens_for(engine, "connect")
def _register_sqlite_spatial_functions(dbapi_connection, connection_record):
    if hasattr(dbapi_connection, "create_function"):
        try:
            dbapi_connection.create_function("AsEWKB", 1, lambda val: val)
            dbapi_connection.create_function("ST_AsEWKB", 1, lambda val: val)
            dbapi_connection.create_function("GeomFromEWKT", 1, lambda val: val)
            dbapi_connection.create_function("ST_GeomFromEWKT", 1, lambda val: val)
            dbapi_connection.create_function("GeomFromText", 1, lambda val: val)
            dbapi_connection.create_function("ST_GeomFromText", 1, lambda val: val)
            dbapi_connection.create_function("CheckSpatialIndex", 2, lambda a, b: 1)
            dbapi_connection.create_function("RecoverGeometryColumn", 5, lambda *args: 1)
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
