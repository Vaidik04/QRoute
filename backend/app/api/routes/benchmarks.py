from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.schemas.benchmark import BenchmarkRunRequest, BenchmarkResponse
from backend.app.services.benchmark_service import benchmark_service

router = APIRouter()

@router.post("/benchmarks/run", response_model=BenchmarkResponse)
def run_benchmark_suite(req: BenchmarkRunRequest, db: Session = Depends(get_db)):
    return benchmark_service.run_benchmark(db, req)

@router.get("/benchmarks/{bench_id}", response_model=BenchmarkResponse)
def get_benchmark_result(bench_id: str = Path(...), db: Session = Depends(get_db)):
    req = BenchmarkRunRequest()
    return benchmark_service.run_benchmark(db, req)
