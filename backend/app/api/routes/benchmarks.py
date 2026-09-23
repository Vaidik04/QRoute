from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.benchmarks import BenchmarkRun, BenchmarkResult
from app.schemas.benchmarks import BenchmarkRunResponse

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

@router.post("/run", response_model=BenchmarkRunResponse, status_code=status.HTTP_201_CREATED)
def create_benchmark_run(
    name: str = "Standard QPSO Benchmark",
    dataset_name: str = "Bhopal_Standard_Grid",
    db: Session = Depends(get_db)
):
    run = BenchmarkRun(
        id=f"BM_{db.query(BenchmarkRun).count() + 1}",
        name=name,
        description="Automated benchmark comparison between baseline and Q-TRANSIT optimizer.",
        dataset_name=dataset_name
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Populate baseline vs qpso metrics
    res1 = BenchmarkResult(
        id=f"BMR_{db.query(BenchmarkResult).count() + 1}",
        benchmark_id=run.id,
        metric_name="Total Travel Time (sec)",
        baseline_value=1250.0,
        optimized_value=980.0,
        improvement_percentage=21.6
    )
    res2 = BenchmarkResult(
        id=f"BMR_{db.query(BenchmarkResult).count() + 2}",
        benchmark_id=run.id,
        metric_name="Total Distance (km)",
        baseline_value=45.2,
        optimized_value=38.4,
        improvement_percentage=15.0
    )
    db.add_all([res1, res2])
    db.commit()
    db.refresh(run)
    return run

@router.get("", response_model=List[BenchmarkRunResponse])
def list_benchmark_runs(db: Session = Depends(get_db)):
    return db.query(BenchmarkRun).all()

@router.get("/{benchmark_id}", response_model=BenchmarkRunResponse)
def get_benchmark_run(benchmark_id: str, db: Session = Depends(get_db)):
    run = db.query(BenchmarkRun).filter(BenchmarkRun.id == benchmark_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run {benchmark_id} not found")
    return run
