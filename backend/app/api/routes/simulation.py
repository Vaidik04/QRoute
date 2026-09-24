from fastapi import APIRouter, Depends, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.db.session import get_db
from backend.app.schemas.simulation import (
    SimulationStartRequest,
    SimulationStartResponse,
    SimulationStateResponse,
    SimulationMetricsResponse
)
from backend.app.services.simulation_service import simulation_service
from backend.app.services.orchestration_service import orchestration_service

router = APIRouter()

@router.post("/simulation/start", response_model=SimulationStartResponse)
def start_simulation(req: SimulationStartRequest, db: Session = Depends(get_db)):
    return simulation_service.start_simulation(db, req)

@router.get("/simulation/{sim_id}", response_model=SimulationStateResponse)
def get_simulation_state(sim_id: str = Path(...), db: Session = Depends(get_db)):
    return simulation_service.get_simulation_state(db, sim_id)

@router.post("/simulation/{sim_id}/stop")
def stop_simulation(sim_id: str = Path(...), db: Session = Depends(get_db)):
    success = simulation_service.stop_simulation(db, sim_id)
    return {"simulation_id": sim_id, "status": "STOPPED" if success else "FAILED"}

@router.post("/simulation/{sim_id}/pause")
def pause_simulation(sim_id: str = Path(...)):
    return {"simulation_id": sim_id, "status": "PAUSED"}

@router.post("/simulation/{sim_id}/resume")
def resume_simulation(sim_id: str = Path(...)):
    return {"simulation_id": sim_id, "status": "RUNNING"}

@router.post("/simulation/{sim_id}/incident")
async def inject_simulation_incident(
    req: Dict[str, Any],
    sim_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """Inject artificial event into SUMO simulation and trigger Q-TRANSIT dynamic rerouting loop."""
    affected_edges = req.get("affected_edges", ["R17", "R18"])
    simulation_service.inject_incident(db, sim_id, affected_edges)

    # Execute dynamic rerouting loop orchestrator
    event_data = {
        "simulation_id": sim_id,
        "affected_edges": affected_edges,
        "severity": req.get("severity", "HIGH"),
        "reason": req.get("reason", "ROAD_CLOSURE")
    }
    res = await orchestration_service.handle_traffic_change_event(db, event_data)

    return {
        "simulation_id": sim_id,
        "status": "INCIDENT_INJECTED",
        "orchestration": res
    }

@router.get("/simulation/{sim_id}/metrics", response_model=SimulationMetricsResponse)
def get_simulation_metrics(sim_id: str = Path(...), db: Session = Depends(get_db)):
    return simulation_service.get_metrics(db, sim_id)
