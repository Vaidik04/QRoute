from sqlalchemy.orm import Session
from typing import List, Optional
from app.repositories.simulation import SimulationRepository
from app.adapters.sumo_adapter import SUMOAdapter
from app.schemas.simulation import SimulationRunResponse, SimulationMetricResponse
from app.core.exceptions import ResourceNotFoundException, ValidationException

class SimulationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SimulationRepository(db)
        self.adapter = SUMOAdapter()

    def start_simulation(self, config_path: str = "data/sumo/bhopal.sumocfg") -> SimulationRunResponse:
        self.adapter.start_simulation(config_path)
        run = self.repo.create_run(config_path)
        return SimulationRunResponse.model_validate(run)

    def stop_simulation(self, sim_id: str) -> SimulationRunResponse:
        run = self.repo.get_run(sim_id)
        if not run:
            raise ResourceNotFoundException("SimulationRun", sim_id)
        self.adapter.stop_simulation()
        run = self.repo.update_status(sim_id, "STOPPED")
        return SimulationRunResponse.model_validate(run)

    def pause_simulation(self, sim_id: str) -> SimulationRunResponse:
        run = self.repo.get_run(sim_id)
        if not run:
            raise ResourceNotFoundException("SimulationRun", sim_id)
        self.adapter.pause_simulation()
        run = self.repo.update_status(sim_id, "PAUSED")
        return SimulationRunResponse.model_validate(run)

    def resume_simulation(self, sim_id: str) -> SimulationRunResponse:
        run = self.repo.get_run(sim_id)
        if not run:
            raise ResourceNotFoundException("SimulationRun", sim_id)
        self.adapter.resume_simulation()
        run = self.repo.update_status(sim_id, "RUNNING")
        return SimulationRunResponse.model_validate(run)

    def inject_incident(self, sim_id: str, edge_id: str, speed_limit_kph: float) -> bool:
        run = self.repo.get_run(sim_id)
        if not run:
            raise ResourceNotFoundException("SimulationRun", sim_id)
        return self.adapter.inject_incident(edge_id, speed_limit_kph)

    def get_simulation(self, sim_id: str) -> SimulationRunResponse:
        run = self.repo.get_run(sim_id)
        if not run:
            raise ResourceNotFoundException("SimulationRun", sim_id)
        return SimulationRunResponse.model_validate(run)

    def get_metrics(self, sim_id: str) -> List[SimulationMetricResponse]:
        metrics = self.repo.get_metrics(sim_id)
        if not metrics:
            # Generate step metric via adapter for demo
            step_info = self.adapter.step_simulation()
            self.repo.add_metric(sim_id, step_info["step"], step_info["active_vehicles"], step_info["avg_speed"], step_info["emissions"])
            metrics = self.repo.get_metrics(sim_id)
        return [SimulationMetricResponse.model_validate(m) for m in metrics]
