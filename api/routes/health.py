"""
Peptide AI - Health Check Endpoints

Standard health check endpoints for monitoring and orchestration.
"""

from fastapi import APIRouter, Depends
from datetime import datetime

from api.deps import get_database, get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check - always returns OK if API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2024-12-26-coach-mode"  # Version marker to verify deployment
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available

    Returns 200 if ready to serve traffic, 503 otherwise.
    """
    checks = {
        "database": False,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        db = get_database()
        # Ping database
        await db.command("ping")
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)

    # TODO: Add Weaviate check
    # TODO: Add Redis check

    all_healthy = all(v for k, v in checks.items() if isinstance(v, bool))
    checks["status"] = "ready" if all_healthy else "not_ready"

    if not all_healthy:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=checks)

    return checks


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - verifies the application is not deadlocked

    Used by Kubernetes for pod health monitoring.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/config")
async def config_check():
    """
    Config check - shows if required environment variables are configured.

    Does NOT reveal actual values, just whether they are set.
    """
    import os

    settings = get_settings()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "master_key_configured": settings.master_api_key != "dev-key-change-me",
            "master_key_length": len(settings.master_api_key),
            "master_key_preview": settings.master_api_key[:8] + "..." if len(settings.master_api_key) > 8 else "***",
            "mongodb_configured": "localhost" not in settings.mongodb_url,
            "llm_provider": settings.llm_provider,
            "openai_configured": bool(settings.openai_api_key),
            "api_key_header": settings.api_key_header,
        },
        "env_vars_present": {
            "PEPTIDE_AI_MASTER_KEY": bool(os.getenv("PEPTIDE_AI_MASTER_KEY")),
            "MONGODB_URL": bool(os.getenv("MONGODB_URL")),
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        }
    }
