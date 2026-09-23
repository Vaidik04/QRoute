from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class BenchmarkResultResponse(BaseModel):
    id: str
    metric_name: str
    baseline_value: float
    optimized_value: float
    improvement_percentage: float
    model_config = ConfigDict(from_attributes=True)

class BenchmarkRunResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    dataset_name: str
    created_at: datetime
    results: List[BenchmarkResultResponse] = []
    model_config = ConfigDict(from_attributes=True)

class ComparisonMetricDetail(BaseModel):
    metric: str
    baseline: float
    optimized: float
    delta: float
    improvement_percentage: float

class AnalyticsComparisonResponse(BaseModel):
    baseline_run_id: str
    optimized_run_id: str
    total_travel_distance_meters: ComparisonMetricDetail
    total_travel_time_seconds: ComparisonMetricDetail
    fleet_utilization_ratio: ComparisonMetricDetail
    computed_at: datetime
