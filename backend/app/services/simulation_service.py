import uuid
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.adapters.sumo_adapter import SUMOAdapter
from backend.app.repositories.simulation_repo import SimulationRepository
from backend.app.models.simulation import SimulationRun, SimulationMetrics
from backend.app.schemas.simulation import (
    SimulationStartRequest,
    SimulationStartResponse,
    SimulationStateResponse,
    SimulatedVehicleState,
    SimulationMetricsResponse
)
from backend.app.api.websocket import ws_manager
from backend.app.core.exceptions import NotFoundException

class SimulationService:
    def __init__(self):
        self.adapter = SUMOAdapter()
        self.repo = SimulationRepository()

    def start_simulation(
        self,
        db: Session,
        req: SimulationStartRequest
    ) -> SimulationStartResponse:
        sim_id = f"SIM_{uuid.uuid4().hex[:6].upper()}"

        run = SimulationRun(
            id=sim_id,
            scenario=req.scenario,
            seed=42,
            duration_sec=req.duration_sec,
            active_vehicles=req.vehicles,
            status="STARTED",
            started_at=datetime.utcnow()
        )
        self.repo.create(db, run)

        self.adapter.start_simulation(
            simulation_id=sim_id,
            scenario=req.scenario,
            vehicles_count=req.vehicles,
            duration_sec=req.duration_sec
        )

        return SimulationStartResponse(
            simulation_id=sim_id,
            status="STARTED"
        )

    def get_simulation_state(self, db: Session, sim_id: str) -> SimulationStateResponse:
        run = self.repo.get(db, sim_id)
        if not run:
            raise NotFoundException("SimulationRun", sim_id)

        adapter_state = self.adapter.step_simulation(sim_id, delta_sec=5.0)
        vehicles_out = []
        for v in adapter_state.get("vehicles", []):
            vehicles_out.append(SimulatedVehicleState(
                id=v["id"],
                lat=v["lat"],
                lon=v["lon"],
                speed_kmh=v["speed_kmh"],
                route_id=v.get("route_id"),
                status=v.get("status", "MOVING")
            ))

        return SimulationStateResponse(
            simulation_id=sim_id,
            simulation_time=adapter_state.get("simulation_time", 120.0),
            status=run.status if run.status != "STARTED" else "RUNNING",
            vehicles=vehicles_out
        )

    def inject_incident(self, db: Session, sim_id: str, affected_edges: List[str]) -> bool:
        run = self.repo.get(db, sim_id)
        if not run:
            raise NotFoundException("SimulationRun", sim_id)

        success = self.adapter.inject_incident(sim_id, affected_edges)
        return success

    def get_metrics(self, db: Session, sim_id: str) -> SimulationMetricsResponse:
        metrics = self.repo.get_latest_metrics(db, sim_id)
        if not metrics:
            metrics = SimulationMetrics(
                id=str(uuid.uuid4()),
                simulation_id=sim_id,
                timestamp=datetime.utcnow(),
                average_speed=28.5,
                average_delay=8.2,
                queue_length=12.4,
                throughput=820.0,
                waiting_time=14.5,
                reroutes=3
            )
            self.repo.save_metrics(db, metrics)

        return SimulationMetricsResponse(
            simulation_id=sim_id,
            timestamp=metrics.timestamp,
            average_speed=metrics.average_speed,
            average_delay=metrics.average_delay,
            queue_length=metrics.queue_length,
            throughput=metrics.throughput,
            waiting_time=metrics.waiting_time,
            reroutes=metrics.reroutes
        )

    def stop_simulation(self, db: Session, sim_id: str) -> bool:
        run = self.repo.get(db, sim_id)
        if run:
            run.status = "STOPPED"
            run.completed_at = datetime.utcnow()
            db.commit()
            self.adapter.stop_simulation(sim_id)
            return True
        return False

simulation_service = SimulationService()
