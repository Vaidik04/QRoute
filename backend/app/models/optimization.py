from sqlalchemy import String, Float, DateTime, ForeignKey, func, Integer, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
import uuid
from app.db.base import Base

class OptimizationStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INFEASIBLE = "INFEASIBLE"

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), default=OptimizationStatus.QUEUED.value, index=True)
    algorithm_name: Mapped[str] = mapped_column(String(50), default="D-QPSO")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    solutions = relationship("OptimizationSolution", back_populates="run", cascade="all, delete-orphan")
    metrics = relationship("OptimizationMetric", back_populates="run", uselist=False, cascade="all, delete-orphan")
    iterations = relationship("OptimizationIteration", back_populates="run", order_by="OptimizationIteration.iteration_number", cascade="all, delete-orphan")

class OptimizationSolution(Base):
    __tablename__ = "optimization_solutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_runs.id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    customer_sequence_json: Mapped[str] = mapped_column(Text, nullable=False) # JSON array of customer IDs
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_distance: Mapped[float] = mapped_column(Float, default=0.0)

    run = relationship("OptimizationRun", back_populates="solutions")

class OptimizationMetric(Base):
    __tablename__ = "optimization_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_runs.id"), nullable=False, unique=True)
    total_runtime_ms: Mapped[float] = mapped_column(Float, default=0.0)
    total_distance: Mapped[float] = mapped_column(Float, default=0.0)
    fleet_utilization: Mapped[float] = mapped_column(Float, default=0.0)

    run = relationship("OptimizationRun", back_populates="metrics")

class OptimizationIteration(Base):
    __tablename__ = "optimization_iterations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_runs.id"), nullable=False)
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False)
    best_cost: Mapped[float] = mapped_column(Float, nullable=False)
    average_cost: Mapped[float] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    run = relationship("OptimizationRun", back_populates="iterations")
