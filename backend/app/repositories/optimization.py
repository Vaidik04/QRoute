from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models.optimization import (
    OptimizationRun,
    OptimizationSolution,
    OptimizationMetric,
    OptimizationIteration,
    OptimizationStatus
)

class OptimizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, algorithm_name: str = "D-QPSO") -> OptimizationRun:
        run = OptimizationRun(
            status=OptimizationStatus.QUEUED.value,
            algorithm_name=algorithm_name
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: str) -> Optional[OptimizationRun]:
        return self.db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()

    def update_status(self, run_id: str, status: str, finished: bool = False) -> Optional[OptimizationRun]:
        run = self.get_run(run_id)
        if run:
            run.status = status
            if finished:
                run.finished_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(run)
        return run

    def add_iteration(self, run_id: str, iteration_number: int, best_cost: float, average_cost: Optional[float] = None):
        iteration = OptimizationIteration(
            run_id=run_id,
            iteration_number=iteration_number,
            best_cost=best_cost,
            average_cost=average_cost
        )
        self.db.add(iteration)
        self.db.commit()

    def add_solution(self, run_id: str, vehicle_id: str, sequence_json: str, total_cost: float, total_distance: float):
        solution = OptimizationSolution(
            run_id=run_id,
            vehicle_id=vehicle_id,
            customer_sequence_json=sequence_json,
            total_cost=total_cost,
            total_distance=total_distance
        )
        self.db.add(solution)
        self.db.commit()

    def set_metrics(self, run_id: str, runtime_ms: float, total_distance: float, fleet_utilization: float):
        metric = OptimizationMetric(
            run_id=run_id,
            total_runtime_ms=runtime_ms,
            total_distance=total_distance,
            fleet_utilization=fleet_utilization
        )
        self.db.add(metric)
        self.db.commit()
