from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.simulation import SimulationRun, SimulationMetrics
from backend.app.repositories.base import BaseRepository

class SimulationRepository(BaseRepository[SimulationRun]):
    def __init__(self):
        super().__init__(SimulationRun)

    def save_metrics(self, db: Session, metrics: SimulationMetrics) -> SimulationMetrics:
        db.add(metrics)
        db.commit()
        db.refresh(metrics)
        return metrics

    def get_latest_metrics(self, db: Session, simulation_id: str) -> Optional[SimulationMetrics]:
        return db.query(SimulationMetrics).filter(SimulationMetrics.simulation_id == simulation_id).order_by(desc(SimulationMetrics.timestamp)).first()
