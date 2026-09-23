from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.traffic_service import TrafficService
from app.schemas.traffic import IncidentCreate, IncidentUpdate, IncidentResponse

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    return TrafficService(db).create_incident(data)

@router.get("", response_model=List[IncidentResponse])
def list_incidents(active_only: bool = False, db: Session = Depends(get_db)):
    return TrafficService(db).list_incidents(active_only=active_only)

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    return TrafficService(db).get_incident(incident_id)

@router.put("/{incident_id}", response_model=IncidentResponse)
def update_incident(incident_id: str, data: IncidentUpdate, db: Session = Depends(get_db)):
    return TrafficService(db).update_incident(incident_id, data)

@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: str, db: Session = Depends(get_db)):
    TrafficService(db).delete_incident(incident_id)
