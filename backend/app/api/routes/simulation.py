from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.services.simulation_service import SimulationService
from app.schemas.simulation import SimulationStartRequest, SimulationRunResponse, SimulationMetricResponse

router = APIRouter(prefix="/simulation", tags=["SUMO Simulation Integration"])

@router.post("/start", response_model=SimulationRunResponse)
def start_simulation(req: SimulationStartRequest = Body(SimulationStartRequest()), db: Session = Depends(get_db)):
    return SimulationService(db).start_simulation(req.sumo_config_path)

@router.post("/stop", response_model=SimulationRunResponse)
def stop_simulation(sim_id: str, db: Session = Depends(get_db)):
    return SimulationService(db).stop_simulation(sim_id)

@router.post("/pause", response_model=SimulationRunResponse)
def pause_simulation(sim_id: str, db: Session = Depends(get_db)):
    return SimulationService(db).pause_simulation(sim_id)

@router.post("/resume", response_model=SimulationRunResponse)
def resume_simulation(sim_id: str, db: Session = Depends(get_db)):
    return SimulationService(db).resume_simulation(sim_id)

@router.get("/{sim_id}", response_model=SimulationRunResponse)
def get_simulation(sim_id: str, db: Session = Depends(get_db)):
    return SimulationService(db).get_simulation(sim_id)

@router.post("/{sim_id}/incident")
def inject_simulation_incident(sim_id: str, payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    edge_id = payload.get("edge_id", "edge_01")
    speed_limit = float(payload.get("speed_limit_kph", 15.0))
    success = SimulationService(db).inject_incident(sim_id, edge_id, speed_limit)
    return {"status": "INJECTED" if success else "FAILED", "edge_id": edge_id, "speed_limit_kph": speed_limit}

@router.get("/{sim_id}/metrics", response_model=List[SimulationMetricResponse])
def get_simulation_metrics(sim_id: str, db: Session = Depends(get_db)):
    return SimulationService(db).get_metrics(sim_id)
