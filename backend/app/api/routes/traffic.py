from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.db.session import get_db
from app.services.traffic_service import TrafficService
from app.services.orchestrator import OrchestratorService
from app.schemas.traffic import TrafficStateResponse, TrafficPredictionResponse

router = APIRouter(prefix="/traffic", tags=["Traffic Data & Predictions"])

@router.get("/current", response_model=List[TrafficStateResponse])
def get_current_traffic(db: Session = Depends(get_db)):
    return TrafficService(db).get_current_traffic()

@router.get("/edge/{edge_id}", response_model=TrafficStateResponse)
def get_edge_traffic(edge_id: str, db: Session = Depends(get_db)):
    return TrafficService(db).get_edge_traffic(edge_id)

@router.get("/prediction", response_model=List[TrafficPredictionResponse])
def get_traffic_prediction(edge_id: Optional[str] = None, db: Session = Depends(get_db)):
    return TrafficService(db).get_predictions(edge_id)

@router.post("/update", status_code=status.HTTP_200_OK, summary="Ingest traffic update & trigger dynamic rerouting loop")
async def ingest_traffic_update(raw_payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    # Phase 8 orchestration: ingest event -> evaluate re-routing -> call Member 1 -> push route_changed WebSocket
    result = await OrchestratorService(db).handle_traffic_state_changed(raw_payload)
    return result
