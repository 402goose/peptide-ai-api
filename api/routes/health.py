"""
Peptide AI - Health Check Endpoints

Standard health check endpoints for monitoring and orchestration.
"""

from fastapi import APIRouter, Depends
from datetime import datetime

from api.deps import get_database

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check - always returns OK if API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
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
