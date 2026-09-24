from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.adapters.traffic_adapter import TrafficAdapter
from backend.app.repositories.traffic_repo import TrafficRepository
from backend.app.models.traffic import TrafficState, TrafficPrediction
from backend.app.schemas.traffic import TrafficStateSchema, TrafficPredictionSchema
import uuid

class TrafficService:
    def __init__(self):
        self.adapter = TrafficAdapter()
        self.repo = TrafficRepository()

    def get_current_traffic(self, db: Session) -> List[TrafficStateSchema]:
        """Fetch current traffic state across network edges."""
        states = self.repo.get_all_latest_states(db)
        if not states:
            # Seed/Generate live synthetic states for key Bhopal edges
            edges = ["R17", "R18", "R19", "R20", "R21", "R22", "R23", "R24"]
            result = []
            for eid in edges:
                data = self.adapter.get_live_edge_state(eid)
                st = TrafficState(
                    id=str(uuid.uuid4()),
                    edge_id=eid,
                    timestamp=datetime.utcnow(),
                    speed_kmh=data["speed_kmh"],
                    travel_time_sec=data["travel_time_sec"],
                    density=data["density"],
                    flow=data["flow"],
                    congestion=data["congestion"],
                    queue_length=data["queue_length"],
                    status=data["status"],
                    source=data["source"]
                )
                db.add(st)
                result.append(TrafficStateSchema(**data))
            db.commit()
            return result
        return [
            TrafficStateSchema(
                edge_id=s.edge_id,
                timestamp=s.timestamp,
                speed_kmh=s.speed_kmh,
                travel_time_sec=s.travel_time_sec,
                density=s.density,
                flow=s.flow,
                congestion=s.congestion,
                queue_length=s.queue_length,
                status=s.status,
                source=s.source
            )
            for s in states
        ]

    def get_edge_traffic(self, db: Session, edge_id: str) -> TrafficStateSchema:
        state = self.repo.get_latest_edge_state(db, edge_id)
        if not state:
            data = self.adapter.get_live_edge_state(edge_id)
            return TrafficStateSchema(**data)
        return TrafficStateSchema(
            edge_id=state.edge_id,
            timestamp=state.timestamp,
            speed_kmh=state.speed_kmh,
            travel_time_sec=state.travel_time_sec,
            density=state.density,
            flow=state.flow,
            congestion=state.congestion,
            queue_length=state.queue_length,
            status=state.status,
            source=state.source
        )

    def get_traffic_prediction(self, db: Session, edge_id: str, horizon_min: int = 10) -> TrafficPredictionSchema:
        data = self.adapter.get_edge_prediction(edge_id, horizon_min)
        pred = TrafficPrediction(
            id=str(uuid.uuid4()),
            edge_id=edge_id,
            generated_at=datetime.utcnow(),
            target_time=datetime.fromisoformat(data["target_time"].replace("Z", "")),
            horizon_min=horizon_min,
            predicted_speed=data["predicted_speed"],
            predicted_travel_time=data["predicted_travel_time"],
            model_name=data["model_name"],
            confidence=data["confidence"]
        )
        self.repo.save_prediction(db, pred)
        return TrafficPredictionSchema(**data)

traffic_service = TrafficService()
