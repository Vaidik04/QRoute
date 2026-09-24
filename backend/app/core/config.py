import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Q-TRANSIT NEXUS Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "qtransit_nexus_super_secret_key_2026_change_in_prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Database (Defaults to SQLite for portable local run, can be overridden with PostgreSQL/PostGIS)
    DATABASE_URL: str = "sqlite:///./qtransit.db"
    
    # Cache / Message Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Simulation & External Tools
    SUMO_BINARY: str = "sumo"
    SUMO_HOME: str = "C:/Program Files (x86)/Eclipse/Sumo"
    OSM_DATA_PATH: str = "./data/bhopal_network.json"
    
    # Optional Free-Tier External Service Keys (100% free fallback if empty)
    TOMTOM_TRAFFIC_API_KEY: str = "" # Free tier: 2,500 requests/day
    MAPBOX_API_KEY: str = ""         # Free tier: 100,000 requests/month
    OPENWEATHER_API_KEY: str = ""    # Free tier: 1,000 requests/day
    NOMINATIM_USER_AGENT: str = "QTransitNexus/1.0" # 100% Free OpenStreetMap search
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "*"
    ]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
