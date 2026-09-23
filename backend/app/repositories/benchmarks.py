from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.benchmarks import BenchmarkRun, BenchmarkResult

class BenchmarkRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, name: str, description: Optional[str] = None, dataset_name: str = "bhopal_core") -> BenchmarkRun:
        run = BenchmarkRun(
            name=name,
            description=description,
            dataset_name=dataset_name
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def add_result(self, benchmark_id: str, metric_name: str, baseline_val: float, opt_val: float) -> BenchmarkResult:
        improvement = ((baseline_val - opt_val) / baseline_val * 100.0) if baseline_val > 0 else 0.0
        res = BenchmarkResult(
            benchmark_id=benchmark_id,
            metric_name=metric_name,
            baseline_value=baseline_val,
            optimized_value=opt_val,
            improvement_percentage=round(improvement, 2)
        )
        self.db.add(res)
        self.db.commit()
        self.db.refresh(res)
        return res

    def get_run(self, benchmark_id: str) -> Optional[BenchmarkRun]:
        return self.db.query(BenchmarkRun).filter(BenchmarkRun.id == benchmark_id).first()

    def list_all(self) -> List[BenchmarkRun]:
        return self.db.query(BenchmarkRun).order_by(BenchmarkRun.created_at.desc()).all()
