from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, DateTime
from backend.app.db.base import Base

class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(String, primary_key=True, index=True) # BENCH_500
    dataset = Column(String, default="Bhopal_VRP_Benchmark_100")
    instance = Column(String, default="Peak_Hour_Scenario")
    algorithm = Column(String, default="Adaptive D-QPSO")
    seed = Column(Integer, default=42)
    population_size = Column(Integer, default=50)
    iterations = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(String, primary_key=True, index=True)
    benchmark_run_id = Column(String, ForeignKey("benchmark_runs.id"), index=True, nullable=False)
    best_fitness = Column(Float, nullable=False)
    mean_fitness = Column(Float, default=0.0)
    std_dev = Column(Float, default=0.0)
    runtime_ms = Column(Float, default=0.0)
    feasible = Column(Boolean, default=True)
    optimality_gap = Column(Float, default=0.0)
