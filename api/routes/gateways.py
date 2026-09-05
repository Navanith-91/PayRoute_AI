"""
FastAPI Routes for Gateway Platform Settings, API Credentials, and Live Connection Testing.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_db
from api.schemas import (
    GatewayCredentialSchema,
    GatewayCredentialUpdateSchema,
    GatewayTestConnectionResponseSchema,
)
from database.db_manager import DatabaseManager
from src.gateways.gateway_manager import GatewayManager
from src.utils.logger import get_logger

logger = get_logger("GatewaysAPI")

router = APIRouter(prefix="/api/v1/gateways", tags=["Gateway Platforms & API Integrations"])


def get_gateway_manager(db: DatabaseManager = Depends(get_db)) -> GatewayManager:
    """Dependency provider for GatewayManager."""
    return GatewayManager(db_manager=db)


@router.get(
    "/credentials",
    response_model=List[GatewayCredentialSchema],
    status_code=status.HTTP_200_OK,
    summary="List All Gateway Platform Credentials",
    description="Returns all configured gateway platforms (Razorpay, PhonePe, Google Pay) with masked secrets.",
)
async def list_gateway_credentials(
    manager: GatewayManager = Depends(get_gateway_manager),
) -> List[GatewayCredentialSchema]:
    """Retrieves all configured gateway credentials with masked secret keys."""
    creds_list = manager.list_all_credentials(mask_secrets=True)
    return [GatewayCredentialSchema(**c) for c in creds_list]


@router.get(
    "/{provider_id}/credentials",
    response_model=GatewayCredentialSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Specific Gateway Credentials",
)
async def get_gateway_credential(
    provider_id: str,
    manager: GatewayManager = Depends(get_gateway_manager),
) -> GatewayCredentialSchema:
    """Retrieves credentials for a specific provider."""
    c = manager.get_credentials(provider_id.upper(), mask_secrets=True)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials configured for provider '{provider_id}'.",
        )
    return GatewayCredentialSchema(**c)


@router.post(
    "/{provider_id}/credentials",
    response_model=GatewayTestConnectionResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update Gateway API Credentials",
    description="Saves updated API keys for Razorpay, PhonePe, or Google Pay and runs an automated pre-flight connection test.",
)
async def save_gateway_credentials(
    provider_id: str,
    payload: GatewayCredentialUpdateSchema,
    manager: GatewayManager = Depends(get_gateway_manager),
) -> GatewayTestConnectionResponseSchema:
    """Saves API keys and runs live connectivity probe."""
    try:
        p_id = provider_id.upper()
        test_result = manager.save_credentials(p_id, payload.model_dump())
        return GatewayTestConnectionResponseSchema(
            provider_id=p_id,
            success=test_result.get("success", False),
            status=test_result.get("status", "UNCONFIGURED"),
            message=test_result.get("message", "Credentials saved."),
            latency_ms=test_result.get("latency_ms", 0),
            environment=payload.environment,
        )
    except Exception as e:
        logger.error(f"Failed to update gateway credentials for {provider_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save gateway credentials: {str(e)}",
        )


@router.post(
    "/{provider_id}/test-connection",
    response_model=GatewayTestConnectionResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Test Active Gateway Connection",
    description="Runs a live API probe against Razorpay, PhonePe, or Google Pay using currently stored credentials.",
)
async def test_gateway_connection(
    provider_id: str,
    manager: GatewayManager = Depends(get_gateway_manager),
) -> GatewayTestConnectionResponseSchema:
    """Executes live probe against gateway servers and measures real latency."""
    p_id = provider_id.upper()
    test_result = manager.test_connection(p_id)
    return GatewayTestConnectionResponseSchema(
        provider_id=p_id,
        success=test_result.get("success", False),
        status=test_result.get("status", "UNCONFIGURED"),
        message=test_result.get("message", "Test completed."),
        latency_ms=test_result.get("latency_ms", 0),
        environment=test_result.get("environment", "SANDBOX"),
    )
