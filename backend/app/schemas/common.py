from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class LatLon(BaseModel):
    lat: float = Field(..., example=23.2599)
    lon: float = Field(..., example=77.4126)

class ObjectiveWeights(BaseModel):
    time: float = Field(0.5, example=0.5)
    distance: float = Field(0.2, example=0.2)
    congestion: float = Field(0.3, example=0.3)

class GeoJSONGeometry(BaseModel):
    type: str = Field("LineString", example="LineString")
    coordinates: List[List[float]] = Field(..., example=[[77.4126, 23.2599], [77.4316, 23.2156]])

class GeoJSONFeature(BaseModel):
    type: str = Field("Feature", example="Feature")
    geometry: GeoJSONGeometry
    properties: Dict[str, Any] = Field(default_factory=dict)

class GeoJSONFeatureCollection(BaseModel):
    type: str = Field("FeatureCollection", example="FeatureCollection")
    features: List[GeoJSONFeature] = Field(default_factory=list)

class StandardErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class StandardErrorResponse(BaseModel):
    error: StandardErrorDetail
