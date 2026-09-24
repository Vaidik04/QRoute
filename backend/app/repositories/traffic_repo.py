from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.traffic import TrafficState, TrafficPrediction
from backend.app.repositories.base import BaseRepository

class TrafficRepository(BaseRepository[TrafficState]):
    def __init__(self):
        super().__init__(TrafficState)

    def get_latest_edge_state(self, db: Session, edge_id: str) -> Optional[TrafficState]:
        return db.query(TrafficState).filter(TrafficState.edge_id == edge_id).order_by(desc(TrafficState.timestamp)).first()

    def get_all_latest_states(self, db: Session) -> List[TrafficState]:
        # Distinct edge latest state query
        subquery = db.query(TrafficState.edge_id).distinct().subquery()
        return db.query(TrafficState).filter(TrafficState.edge_id.in_(subquery)).order_by(desc(TrafficState.timestamp)).all()

    def save_prediction(self, db: Session, prediction: TrafficPrediction) -> TrafficPrediction:
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction

    def get_edge_predictions(self, db: Session, edge_id: str) -> List[TrafficPrediction]:
        return db.query(TrafficPrediction).filter(TrafficPrediction.edge_id == edge_id).order_by(desc(TrafficPrediction.generated_at)).all()
