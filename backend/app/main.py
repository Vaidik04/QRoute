from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    BaseAppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler
)
from app.api.routes import api_router
from app.api.routes.health import router as health_router
from app.api.websocket import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [Debug Mode: {settings.DEBUG}]")
    yield
    logger.info("Shutting down Q-TRANSIT NEXUS backend...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for Q-TRANSIT NEXUS (Optimized Transportation System)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware setup for mobile application clients & testing tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(BaseAppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Include API Router under /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Top-level route aliases for convenience
app.include_router(health_router, prefix="")
app.include_router(ws_router, prefix="")
