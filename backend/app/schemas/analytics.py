from typing import Dict, Any, List
from pydantic import BaseModel

class MetricComparisonDetail(BaseModel):
    baseline: float
    optimized: float
    change_percent: float

class ComparisonAnalyticsResponse(BaseModel):
    travel_time: MetricComparisonDetail
    delay: MetricComparisonDetail
    congestion_index: MetricComparisonDetail
    emissions_kg: MetricComparisonDetail

class DashboardAnalyticsResponse(BaseModel):
    average_speed: float
    average_delay_min: float
    congestion_index: float
    throughput: int
    active_incidents: int
