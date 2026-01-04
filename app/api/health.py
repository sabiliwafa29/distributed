from fastapi import APIRouter, status
from app.utils.cache import redis_client, cache_service
from app.database import engine
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/",
    summary="Health check",
    description="Basic health check endpoint."
)
def health_check():
    """Simple health check."""
    return {"status": "healthy"}


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check if all services (DB, Redis) are ready."
)
def readiness_check():
    """
    Readiness check for all dependencies.
    
    Returns status of:
    - Database connection
    - Redis connection
    """
    checks = {
        "database": False,
        "redis": False
    }
    
    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)
    
    # Check Redis
    try:
        redis_client.ping()
        checks["redis"] = True
    except Exception as e:
        checks["redis_error"] = str(e)
    
    # Determine overall status
    all_healthy = all([checks["database"], checks["redis"]])
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }


@router.get(
    "/cache/stats",
    summary="Cache statistics",
    description="Get Redis cache statistics."
)
def cache_stats():
    """Get cache statistics."""
    try:
        info = redis_client.info()
        return {
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "total_keys": redis_client.dbsize(),
            "uptime_seconds": info.get("uptime_in_seconds")
        }
    except Exception as e:
        return {"error": str(e)}
