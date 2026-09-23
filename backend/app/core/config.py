from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Q-TRANSIT NEXUS Backend"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Core configuration required per spec
    DATABASE_URL: str = "postgresql://qtransit:qtransit_pass@localhost:5432/qtransit_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SUMO_BINARY: str = "sumo"
    SUMO_CONFIG: str = "data/sumo/bhopal.sumocfg"
    OSM_DATA_PATH: str = "data/osm/bhopal.osm.pbf"
    TRAFFIC_PROVIDER_KEY: str = "demo_traffic_key_secret"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
