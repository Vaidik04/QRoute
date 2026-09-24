from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from typing import List
from backend.app.db.session import get_db
from backend.app.schemas.incident import IncidentCreateSchema, IncidentResponseSchema
from backend.app.services.incident_service import incident_service

router = APIRouter()

@router.get("/incidents", response_model=List[IncidentResponseSchema])
def get_incidents(db: Session = Depends(get_db)):
    return incident_service.get_active_incidents(db)

@router.post("/incidents", response_model=IncidentResponseSchema)
def create_incident(req: IncidentCreateSchema, db: Session = Depends(get_db)):
    return incident_service.create_incident(db, req)

@router.delete("/incidents/{inc_id}")
def delete_incident(inc_id: str = Path(...), db: Session = Depends(get_db)):
    from backend.app.models.incident import Incident
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if inc:
        inc.status = "RESOLVED"
        db.commit()
        return {"status": "RESOLVED", "id": inc_id}
    return {"status": "NOT_FOUND", "id": inc_id}
