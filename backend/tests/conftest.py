import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Disable GeoAlchemy2 Spatialite triggers & functions on plain SQLite test database
from sqlalchemy.ext.compiler import compiles
from geoalchemy2 import Geometry

@compiles(Geometry, 'sqlite')
def compile_geometry_sqlite(type_, compiler, **kw):
    return "TEXT"

try:
    import geoalchemy2.admin.dialects.sqlite as sqlite_admin
    sqlite_admin.after_create = lambda *args, **kwargs: None
    sqlite_admin.before_create = lambda *args, **kwargs: None
    sqlite_admin.after_drop = lambda *args, **kwargs: None
    sqlite_admin.before_drop = lambda *args, **kwargs: None
except Exception:
    pass

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# In-memory SQLite for rapid automated unit testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

@event.listens_for(engine, "connect")
def _register_test_sqlite_spatial_functions(dbapi_connection, connection_record):
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

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except PermissionError:
            pass

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
