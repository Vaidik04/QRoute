from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.session import get_db

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "OK"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "UNAVAILABLE"

    return {
        "status": "ok" if db_status == "OK" else "degraded",
        "service": "q-transit-backend",
        "version": "1.0.0",
        "components": {
            "database": db_status,
            "optimization": "OK",
            "sumo": "OK",
            "traffic": "OK"
        }
    }
