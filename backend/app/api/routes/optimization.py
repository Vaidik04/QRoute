from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from typing import List
from backend.app.db.session import get_db
from backend.app.schemas.optimization import (
    DeliveryOptimizationRequest,
    OptimizationSubmissionResponse,
    OptimizationRunStatusResponse,
    OptimizationIterationPoint,
    OptimizationMetricsResponse
)
from backend.app.services.optimization_service import optimization_service

router = APIRouter()

@router.post("/optimization/delivery", response_model=OptimizationSubmissionResponse)
def submit_delivery_optimization(req: DeliveryOptimizationRequest, db: Session = Depends(get_db)):
    opt_id = optimization_service.submit_delivery_optimization(db, req)
    return OptimizationSubmissionResponse(
        optimization_id=opt_id,
        status="QUEUED"
    )

@router.post("/optimization/run", response_model=OptimizationSubmissionResponse)
def run_optimization_alias(req: DeliveryOptimizationRequest, db: Session = Depends(get_db)):
    opt_id = optimization_service.submit_delivery_optimization(db, req)
    return OptimizationSubmissionResponse(
        optimization_id=opt_id,
        status="QUEUED"
    )

@router.get("/optimization/{opt_id}", response_model=OptimizationRunStatusResponse)
def get_optimization_status(opt_id: str = Path(...), db: Session = Depends(get_db)):
    return optimization_service.get_run_status(db, opt_id)

@router.get("/optimization/{opt_id}/convergence", response_model=List[OptimizationIterationPoint])
def get_optimization_convergence(opt_id: str = Path(...), db: Session = Depends(get_db)):
    return optimization_service.get_run_convergence(db, opt_id)

@router.get("/optimization/{opt_id}/metrics", response_model=OptimizationMetricsResponse)
def get_optimization_metrics(opt_id: str = Path(...), db: Session = Depends(get_db)):
    return optimization_service.get_run_metrics(db, opt_id)
