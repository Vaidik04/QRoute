from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.optimization_service import OptimizationService
from app.schemas.optimization import OptimizationDeliveryRequest, OptimizationRunResponse

router = APIRouter(prefix="/optimization", tags=["Optimization Engine Integration"])

@router.post("/delivery", response_model=OptimizationRunResponse, status_code=status.HTTP_200_OK)
def optimize_delivery(req: OptimizationDeliveryRequest, db: Session = Depends(get_db)):
    return OptimizationService(db).create_run(req)

@router.post("/run", response_model=OptimizationRunResponse, status_code=status.HTTP_200_OK)
def trigger_optimization_run(req: OptimizationDeliveryRequest, db: Session = Depends(get_db)):
    return OptimizationService(db).create_run(req)

@router.get("/{run_id}", response_model=OptimizationRunResponse)
def get_optimization_run(run_id: str, db: Session = Depends(get_db)):
    return OptimizationService(db).get_run(run_id)
