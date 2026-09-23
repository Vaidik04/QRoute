from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.benchmarks import AnalyticsComparisonResponse, BenchmarkRunResponse

router = APIRouter(prefix="/analytics", tags=["Analytics & Benchmarks"])

@router.get("/optimization")
def get_optimization_analytics(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_optimization_analytics()

@router.get("/traffic")
def get_traffic_analytics(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_traffic_analytics()

@router.get("/simulation")
def get_simulation_analytics(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_simulation_analytics()

@router.get("/benchmark", response_model=List[BenchmarkRunResponse])
def list_benchmark_runs(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_benchmarks()

@router.get("/comparison", response_model=AnalyticsComparisonResponse)
def compare_optimization_runs(baseline: str, optimized: str, db: Session = Depends(get_db)):
    return AnalyticsService(db).compare_runs(baseline, optimized)
