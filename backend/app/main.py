import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import (
    QTransitException,
    qtransit_exception_handler,
    unhandled_exception_handler
)
from backend.app.db.session import SessionLocal
from backend.app.db.init_db import init_db
from backend.app.workers.task_worker import worker_pool
from backend.app.api.routes import api_router
from backend.app.api.websocket import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Q-TRANSIT NEXUS Backend Services...")
    # 1. Initialize Database Tables & Seed Bhopal Graph Data
    db = SessionLocal()
    try:
        init_db(db)
        logger.info("Database initialized & Bhopal road network seeded successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        db.close()

    # 2. Start Background Worker Pool
    worker_pool.start()

    yield

    # Shutdown
    logger.info("Shutting down background workers...")
    worker_pool.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(QTransitException, qtransit_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Include API Router under /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix=settings.API_V1_STR)
