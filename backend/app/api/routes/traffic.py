from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from typing import List
from backend.app.db.session import get_db
from backend.app.schemas.traffic import TrafficStateSchema, TrafficPredictionSchema
from backend.app.services.traffic_service import traffic_service

router = APIRouter()

@router.get("/traffic/current", response_model=List[TrafficStateSchema])
def get_current_traffic(db: Session = Depends(get_db)):
    return traffic_service.get_current_traffic(db)

@router.get("/traffic/edge/{edge_id}", response_model=TrafficStateSchema)
def get_edge_traffic(edge_id: str = Path(...), db: Session = Depends(get_db)):
    return traffic_service.get_edge_traffic(db, edge_id)

@router.get("/traffic/prediction", response_model=TrafficPredictionSchema)
def get_traffic_prediction(
    edge_id: str = Query("R17"),
    horizon_min: int = Query(10),
    db: Session = Depends(get_db)
):
    return traffic_service.get_traffic_prediction(db, edge_id, horizon_min)
