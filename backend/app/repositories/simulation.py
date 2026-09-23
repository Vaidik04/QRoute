from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models.simulation import SimulationRun, SimulationMetric

class SimulationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, sumo_config_path: str) -> SimulationRun:
        sim = SimulationRun(
            sumo_config_path=sumo_config_path,
            status="RUNNING",
            started_at=datetime.utcnow()
        )
        self.db.add(sim)
        self.db.commit()
        self.db.refresh(sim)
        return sim

    def get_run(self, sim_id: str) -> Optional[SimulationRun]:
        return self.db.query(SimulationRun).filter(SimulationRun.id == sim_id).first()

    def update_status(self, sim_id: str, status: str) -> Optional[SimulationRun]:
        sim = self.get_run(sim_id)
        if sim:
            sim.status = status
            if status in ["STOPPED", "COMPLETED", "FAILED"]:
                sim.stopped_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(sim)
        return sim

    def add_metric(self, sim_id: str, step_number: int, active_vehicles: int, avg_speed: float, emissions: float):
        metric = SimulationMetric(
            simulation_id=sim_id,
            step_number=step_number,
            active_vehicles=active_vehicles,
            average_speed_kph=avg_speed,
            total_emissions=emissions
        )
        self.db.add(metric)
        self.db.commit()

    def get_metrics(self, sim_id: str) -> List[SimulationMetric]:
        return self.db.query(SimulationMetric).filter(
            SimulationMetric.simulation_id == sim_id
        ).order_by(SimulationMetric.step_number.asc()).all()
