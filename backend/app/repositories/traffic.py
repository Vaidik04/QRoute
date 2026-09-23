from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models.traffic import TrafficState, TrafficPrediction, Incident, IncidentEdge
from app.schemas.traffic import TrafficStateCreate, IncidentCreate, IncidentUpdate

class TrafficRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_traffic_state(self, obj_in: TrafficStateCreate) -> TrafficState:
        db_obj = TrafficState(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_latest_traffic(self, limit: int = 100) -> List[TrafficState]:
        return self.db.query(TrafficState).order_by(TrafficState.timestamp.desc()).limit(limit).all()

    def get_by_edge_id(self, edge_id: str) -> Optional[TrafficState]:
        return self.db.query(TrafficState).filter(
            TrafficState.internal_edge_id == edge_id
        ).order_by(TrafficState.timestamp.desc()).first()

    def get_predictions(self, edge_id: Optional[str] = None) -> List[TrafficPrediction]:
        query = self.db.query(TrafficPrediction)
        if edge_id:
            query = query.filter(TrafficPrediction.internal_edge_id == edge_id)
        return query.order_by(TrafficPrediction.prediction_time.asc()).all()

class IncidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        return self.db.query(Incident).filter(Incident.id == incident_id).first()

    def list_all(self, active_only: bool = False) -> List[Incident]:
        query = self.db.query(Incident)
        if active_only:
            query = query.filter(Incident.status == "ACTIVE")
        return query.order_by(Incident.reported_at.desc()).all()

    def create(self, obj_in: IncidentCreate) -> Incident:
        incident_data = obj_in.model_dump(exclude={'affected_edge_ids', 'impact_factor'})
        incident = Incident(**incident_data)
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)

        for edge_id in obj_in.affected_edge_ids:
            inc_edge = IncidentEdge(
                incident_id=incident.id,
                internal_edge_id=edge_id,
                impact_factor=obj_in.impact_factor
            )
            self.db.add(inc_edge)
        
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def update(self, incident: Incident, obj_in: IncidentUpdate) -> Incident:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(incident, field, value)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def delete(self, incident_id: str) -> bool:
        incident = self.get_by_id(incident_id)
        if incident:
            self.db.delete(incident)
            self.db.commit()
            return True
        return False
