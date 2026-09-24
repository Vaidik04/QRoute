from typing import List
from pydantic import BaseModel, Field

class BenchmarkRunRequest(BaseModel):
    dataset: str = Field("Bhopal_VRP_Benchmark_100", example="Bhopal_VRP_Benchmark_100")
    instance: str = Field("Peak_Hour_Scenario", example="Peak_Hour_Scenario")
    algorithms: List[str] = Field(default_factory=lambda: ["PSO", "GA", "ACO", "QPSO", "Adaptive D-QPSO"])
    population_size: int = Field(50, example=50)
    iterations: int = Field(100, example=100)
    seed: int = Field(42, example=42)

class AlgorithmBenchmarkResult(BaseModel):
    name: str
    mean: float
    std: float
    runtime_ms: float

class BenchmarkResponse(BaseModel):
    benchmark_id: str
    dataset: str
    instance: str
    algorithms: List[AlgorithmBenchmarkResult]
