import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import engine
from app.db.base import Base
from app.models import *  # ensure all models are registered
from app.core.logging import logger

def init_database():
    logger.info(f"Initializing database tables on dialect: {engine.dialect.name}...")
    
    # Disable GeoAlchemy2 Spatialite triggers when running on plain SQLite (dev/test environments)
    if engine.dialect.name == "sqlite":
        try:
            import geoalchemy2.admin.dialects.sqlite as sqlite_admin
            sqlite_admin.after_create = lambda *args, **kwargs: None
        except Exception:
            pass

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully created all 22 database tables!")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise e

if __name__ == "__main__":
    init_database()
