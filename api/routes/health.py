"""
Health and Gateway Telemetry Endpoints.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends

from api.dependencies import get_router
from api.schemas import GatewayHealthResponseSchema
from src.router.router import SmartRouter

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health", summary="Basic Liveness Probe")
def root_health() -> Dict[str, str]:
    """Root health check confirming API operational status."""
    return {"status": "healthy", "service": "payroute-ai"}


@router.get("/api/v1/health", summary="Detailed Readiness Probe")
def v1_health() -> Dict[str, Any]:
    """Detailed health check validating backend service availability."""
    return {
        "status": "healthy",
        "service": "payroute-ai",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected",
        "ml_engine": "ready",
        "smart_router": "active",
    }


@router.get(
    "/api/v1/gateways/health",
    response_model=GatewayHealthResponseSchema,
    summary="Real-Time Gateway Health & Circuit Breakers",
)
def get_gateways_health(
    smart_router: SmartRouter = Depends(get_router),
) -> GatewayHealthResponseSchema:
    """
    Returns real-time rolling success rates, median latencies, and circuit-breaker states
    for all configured payment routes.
    """
    snapshot = smart_router.get_system_health_snapshot()
    return GatewayHealthResponseSchema(
        routes=snapshot,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
