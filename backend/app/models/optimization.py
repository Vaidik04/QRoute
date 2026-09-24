from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, DateTime
from backend.app.db.base import Base

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(String, primary_key=True, index=True) # OPT_1024
    problem_type = Column(String, default="vrp_delivery") # vrp_delivery, trip_route, ev_routing
    algorithm = Column(String, default="adaptive_d_qpso") # adaptive_d_qpso, qpso, pso, ga, aco
    population_size = Column(Integer, default=50)
    iterations = Column(Integer, default=100)
    seed = Column(Integer, default=42)
    status = Column(String, default="QUEUED", index=True) # QUEUED, RUNNING, COMPLETED, FAILED, INFEASIBLE, CANCELLED
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    runtime_ms = Column(Float, default=0.0)
    best_fitness = Column(Float, default=0.0)
    feasible = Column(Boolean, default=True)

class OptimizationSolution(Base):
    __tablename__ = "optimization_solutions"

    id = Column(String, primary_key=True, index=True)
    optimization_run_id = Column(String, ForeignKey("optimization_runs.id"), index=True, nullable=False)
    vehicle_id = Column(String, nullable=False)
    customer_sequence_json = Column(Text, nullable=False) # JSON array of customer IDs
    distance_m = Column(Float, default=0.0)
    travel_time_sec = Column(Float, default=0.0)
    geometry_json = Column(Text, nullable=True) # GeoJSON Feature/LineString

class OptimizationMetrics(Base):
    __tablename__ = "optimization_metrics"

    id = Column(String, primary_key=True, index=True)
    optimization_run_id = Column(String, ForeignKey("optimization_runs.id"), index=True, nullable=False)
    distance = Column(Float, default=0.0)
    travel_time = Column(Float, default=0.0)
    congestion_cost = Column(Float, default=0.0)
    penalty = Column(Float, default=0.0)
    vehicles_used = Column(Integer, default=1)
    constraint_violations = Column(Integer, default=0)
    reroutes = Column(Integer, default=0)
    objective_value = Column(Float, default=0.0)

class OptimizationIteration(Base):
    __tablename__ = "optimization_iterations"

    id = Column(String, primary_key=True, index=True)
    optimization_run_id = Column(String, ForeignKey("optimization_runs.id"), index=True, nullable=False)
    iteration = Column(Integer, nullable=False)
    best_fitness = Column(Float, nullable=False)
    mean_fitness = Column(Float, default=0.0)
    diversity = Column(Float, default=0.0)
    alpha = Column(Float, default=0.0)
