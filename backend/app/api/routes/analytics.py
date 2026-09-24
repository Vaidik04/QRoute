from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.schemas.analytics import ComparisonAnalyticsResponse, DashboardAnalyticsResponse
from backend.app.services.analytics_service import analytics_service

router = APIRouter()

@router.get("/analytics/comparison", response_model=ComparisonAnalyticsResponse)
def get_comparison(
    baseline: str = Query("BASE_001"),
    optimized: str = Query("OPT_1024"),
    db: Session = Depends(get_db)
):
    return analytics_service.get_comparison(db, baseline, optimized)

@router.get("/analytics/traffic", response_model=DashboardAnalyticsResponse)
def get_traffic_analytics(db: Session = Depends(get_db)):
    return analytics_service.get_dashboard_metrics(db)

@router.get("/analytics/simulation")
def get_simulation_analytics(db: Session = Depends(get_db)):
    return {
        "active_simulations": 1,
        "total_vehicles": 50,
        "average_speed_kmh": 28.5,
        "total_reroutes": 5,
        "delay_reduction_percent": 31.77
    }

@router.get("/analytics/optimization")
def get_optimization_analytics(db: Session = Depends(get_db)):
    return {
        "total_optimization_runs": 14,
        "avg_runtime_ms": 912.4,
        "avg_quantum_convergence_iters": 42,
        "feasibility_rate": 1.0
    }
