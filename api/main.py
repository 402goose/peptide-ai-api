"""
Peptide AI - FastAPI Application

Main entry point for the API layer.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from api.routes import chat, search, journey, health
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.auth import AuthMiddleware
from api.deps import init_database, close_database, init_weaviate, close_weaviate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    logger.info("Starting Peptide AI API...")
    await init_database()
    logger.info("Database initialized")
    await init_weaviate()
    logger.info("Weaviate initialized")
    yield
    # Shutdown
    logger.info("Shutting down Peptide AI API...")
    await close_weaviate()
    await close_database()


app = FastAPI(
    title="Peptide AI",
    description="Research-grade peptide knowledge platform powered by RAG",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Authentication middleware
app.add_middleware(AuthMiddleware)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "type": "validation_error"}
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    return JSONResponse(
        status_code=403,
        content={"error": str(exc), "type": "permission_error"}
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(journey.router, prefix="/api/v1", tags=["Journey"])


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "Peptide AI",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs"
    }
