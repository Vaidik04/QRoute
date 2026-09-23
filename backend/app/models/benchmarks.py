from sqlalchemy import String, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.db.base import Base

class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    dataset_name: Mapped[str] = mapped_column(String(100), default="bhopal_core")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    results = relationship("BenchmarkResult", back_populates="benchmark", cascade="all, delete-orphan")

class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    benchmark_id: Mapped[str] = mapped_column(String(36), ForeignKey("benchmark_runs.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. total_travel_time, emissions, fleet_size
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    optimized_value: Mapped[float] = mapped_column(Float, nullable=False)
    improvement_percentage: Mapped[float] = mapped_column(Float, nullable=False) # computed from stored data

    benchmark = relationship("BenchmarkRun", back_populates="results")
