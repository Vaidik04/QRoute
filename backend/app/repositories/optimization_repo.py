from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.optimization import (
    OptimizationRun,
    OptimizationSolution,
    OptimizationMetrics,
    OptimizationIteration
)
from backend.app.repositories.base import BaseRepository

class OptimizationRepository(BaseRepository[OptimizationRun]):
    def __init__(self):
        super().__init__(OptimizationRun)

    def save_solution(self, db: Session, solution: OptimizationSolution) -> OptimizationSolution:
        db.add(solution)
        db.commit()
        db.refresh(solution)
        return solution

    def save_metrics(self, db: Session, metrics: OptimizationMetrics) -> OptimizationMetrics:
        db.add(metrics)
        db.commit()
        db.refresh(metrics)
        return metrics

    def save_iterations(self, db: Session, iterations: List[OptimizationIteration]):
        db.add_all(iterations)
        db.commit()

    def get_solutions_for_run(self, db: Session, run_id: str) -> List[OptimizationSolution]:
        return db.query(OptimizationSolution).filter(OptimizationSolution.optimization_run_id == run_id).all()

    def get_iterations_for_run(self, db: Session, run_id: str) -> List[OptimizationIteration]:
        return db.query(OptimizationIteration).filter(OptimizationIteration.optimization_run_id == run_id).order_by(OptimizationIteration.iteration).all()

    def get_metrics_for_run(self, db: Session, run_id: str) -> Optional[OptimizationMetrics]:
        return db.query(OptimizationMetrics).filter(OptimizationMetrics.optimization_run_id == run_id).first()
