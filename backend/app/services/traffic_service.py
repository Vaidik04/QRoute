from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.repositories.traffic import TrafficRepository, IncidentRepository
from app.adapters.traffic_adapter import TrafficAdapter
from app.schemas.traffic import TrafficStateResponse, TrafficPredictionResponse, IncidentCreate, IncidentUpdate, IncidentResponse
from app.core.exceptions import ResourceNotFoundException

class TrafficService:
    def __init__(self, db: Session):
        self.db = db
        self.traffic_repo = TrafficRepository(db)
        self.incident_repo = IncidentRepository(db)

    def ingest_traffic_update(self, raw_data: Dict[str, Any]) -> TrafficStateResponse:
        # Phase 4 constraint: Normalize and reject invalid inputs via TrafficAdapter before optimizer
        validated_state = TrafficAdapter.normalize_traffic_payload(raw_data)
        db_obj = self.traffic_repo.create_traffic_state(validated_state)
        return TrafficStateResponse.model_validate(db_obj)

    def get_current_traffic(self) -> List[TrafficStateResponse]:
        return [TrafficStateResponse.model_validate(ts) for ts in self.traffic_repo.get_latest_traffic()]

    def get_edge_traffic(self, edge_id: str) -> TrafficStateResponse:
        ts = self.traffic_repo.get_by_edge_id(edge_id)
        if not ts:
            raise ResourceNotFoundException("TrafficState for edge", edge_id)
        return TrafficStateResponse.model_validate(ts)

    def get_predictions(self, edge_id: Optional[str] = None) -> List[TrafficPredictionResponse]:
        return [TrafficPredictionResponse.model_validate(tp) for tp in self.traffic_repo.get_predictions(edge_id)]

    # Incidents CRUD
    def create_incident(self, data: IncidentCreate) -> IncidentResponse:
        return IncidentResponse.model_validate(self.incident_repo.create(data))

    def get_incident(self, incident_id: str) -> IncidentResponse:
        inc = self.incident_repo.get_by_id(incident_id)
        if not inc:
            raise ResourceNotFoundException("Incident", incident_id)
        return IncidentResponse.model_validate(inc)

    def list_incidents(self, active_only: bool = False) -> List[IncidentResponse]:
        return [IncidentResponse.model_validate(inc) for inc in self.incident_repo.list_all(active_only=active_only)]

    def update_incident(self, incident_id: str, data: IncidentUpdate) -> IncidentResponse:
        inc = self.incident_repo.get_by_id(incident_id)
        if not inc:
            raise ResourceNotFoundException("Incident", incident_id)
        return IncidentResponse.model_validate(self.incident_repo.update(inc, data))

    def delete_incident(self, incident_id: str):
        if not self.incident_repo.delete(incident_id):
            raise ResourceNotFoundException("Incident", incident_id)
