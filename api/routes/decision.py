"""
Unified Payment Journey & Decision Engine API Endpoints.
Provides pre-payment risk analysis, dynamic traffic-aware routing execution, scenario injection, and live telemetry feeds.
"""

import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_db, get_router
from api.schemas import (
    EventFeedResponseSchema,
    PaymentAnalysisResponseSchema,
    PaymentProcessRequestSchema,
    PaymentProcessResponseSchema,
    ScenarioInjectionRequestSchema,
    ScenarioInjectionResponseSchema,
    SystemStatusResponseSchema,
    TransactionListResponseSchema,
    TransactionStatusResponseSchema,
)
from database.db_manager import DatabaseManager
from src.router.router import SmartRouter
from src.utils.logger import get_logger



logger = get_logger("DecisionAPI")

router = APIRouter(tags=["Unified Payment Journey & Decision Engine"])


@router.post(
    "/api/v1/payment/analyze",
    response_model=PaymentAnalysisResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Unified Pre-Payment Real-Time Analysis",
    description="Evaluates transaction failure probability, infrastructure traffic load, route health conditions, and returns an actionable decision recommendation.",
)
async def analyze_payment(
    payload: Dict[str, Any],
    router_engine: SmartRouter = Depends(get_router),
) -> PaymentAnalysisResponseSchema:
    """Pre-payment intelligent analysis returning risk, route candidate telemetry, and decision policy."""
    try:
        result = router_engine.analyze_payment(payment_request=payload)
        return PaymentAnalysisResponseSchema(**result)
    except Exception as e:
        logger.error(f"Error during pre-payment analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pre-payment analysis failed: {str(e)}",
        )


@router.post(
    "/api/v1/payment/process",
    response_model=PaymentProcessResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Execute Payment via Recommended Route",
    description="Processes transaction through the AI-recommended or overridden route, updates circuit breaker deques, records SQLite history, and returns execution metrics.",
)
async def process_payment(
    payload: PaymentProcessRequestSchema,
    router_engine: SmartRouter = Depends(get_router),
    db: DatabaseManager = Depends(get_db),
) -> PaymentProcessResponseSchema:
    """Dispatches transaction through the routing engine with live telemetry and SQLite persistence."""
    try:
        req_dict = payload.model_dump()
        result = router_engine.process_payment(
            payment_request=req_dict,
            preferred_route=payload.preferred_route,
            simulate_forced_failure=payload.simulate_forced_failure,
        )

        # Persist transaction in SQLite
        try:
            p_status = result["payment_status"]
            db_record = {
                "transaction_id": result["transaction_id"],
                "merchant_id": req_dict.get("merchant_id", "m_ecom_01"),
                "customer_id": req_dict.get("customer_id", "cust_live_01"),
                "amount": float(result["amount"]),
                "currency": req_dict.get("currency", "INR"),
                "payment_method": result["payment_method"],
                "bank": result["bank"],
                "gateway_id": result.get("route_id", "UNKNOWN"),
                "route_id": result.get("route_id", "UNKNOWN"),
                "merchant_category": req_dict.get("merchant_category", "ECOMMERCE"),
                "payment_status": p_status,
                "failure_reason": result.get("failure_reason"),
                "lifecycle_status": "SUCCESS" if p_status == 0 else "FAILED",
                "customer_debit_status": "CONFIRMED" if p_status == 0 else "FAILED",
                "merchant_confirmation_status": "CONFIRMED" if p_status == 0 else "FAILED",
                "bank_latency_ms": int(result["latency_ms"] * 0.6),
                "gateway_latency_ms": int(result["latency_ms"] * 0.4),
                "total_latency_ms": int(result["latency_ms"]),
                "created_at": datetime.datetime.now().isoformat(),
            }
            db.insert_transaction(db_record)
        except Exception as db_err:
            logger.warning(f"Failed to record transaction to database: {str(db_err)}")

        return PaymentProcessResponseSchema(**result)
    except Exception as e:
        logger.error(f"Error during payment execution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment execution failed: {str(e)}",
        )


@router.get(
    "/api/v1/transactions/{transaction_id}/status",
    response_model=TransactionStatusResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Transaction Lifecycle Status & Timeline",
    description="Retrieves the real-time lifecycle state, debit confirmation, merchant settlement, and stage timeline for a transaction.",
)
async def get_transaction_status(
    transaction_id: str,
    db: DatabaseManager = Depends(get_db),
) -> TransactionStatusResponseSchema:
    """Queries SQLite for transaction lifecycle, debit status, and step timeline."""
    status_data = db.get_transaction_status(transaction_id)
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"We couldn't find a transaction with ID '{transaction_id}'. Please check the Transaction ID and try again.",
        )
    return TransactionStatusResponseSchema(**status_data)


@router.get(
    "/api/v1/transactions",
    response_model=TransactionListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="List Transactions Audit History",
    description="Retrieves paginated SQLite transaction records with status and search filters.",
)
async def list_transactions(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None),
    search_query: Optional[str] = Query(default=None),
    db: DatabaseManager = Depends(get_db),
) -> TransactionListResponseSchema:
    """Queries SQLite for transaction history with filtering."""
    result = db.get_all_transactions(
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        search_query=search_query,
    )
    return TransactionListResponseSchema(**result)




@router.post(
    "/api/v1/simulation/scenario",
    response_model=ScenarioInjectionResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Set Active Simulation Scenario",
    description="Applies a demo scenario (NORMAL, HIGH_TRAFFIC, BANK_DEGRADATION, GATEWAY_OUTAGE, UPI_CONGESTION, FLASH_SALE) to backend routes.",
)
async def set_simulation_scenario(
    payload: ScenarioInjectionRequestSchema,
    router_engine: SmartRouter = Depends(get_router),
) -> ScenarioInjectionResponseSchema:
    """Injects live scenario conditions across route loads and providers."""
    res = router_engine.set_simulation_scenario(
        scenario=payload.scenario,
        target_bank=payload.target_bank,
        target_gateway=payload.target_gateway,
    )
    return ScenarioInjectionResponseSchema(**res)


@router.get(
    "/api/v1/system/status",
    response_model=SystemStatusResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get System Health & Live Telemetry",
    description="Returns current load factors, route status classifications, circuit breaker states, and session KPI metrics.",
)
async def get_system_status(
    router_engine: SmartRouter = Depends(get_router),
) -> SystemStatusResponseSchema:
    """Retrieves real-time infrastructure overview and session KPIs."""
    routes_snapshot = router_engine.get_system_health_snapshot()
    session_kpis = router_engine.get_session_kpis()
    now_iso = datetime.datetime.now().isoformat()
    return SystemStatusResponseSchema(
        active_scenario=router_engine.traffic_simulator.active_scenario.value,
        scenario_description=router_engine.traffic_simulator.get_scenario_description(),
        routes=routes_snapshot,
        session_kpis=session_kpis,
        timestamp=now_iso,
    )


@router.get(
    "/api/v1/events/recent",
    response_model=EventFeedResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Routing Intelligence Event Stream",
    description="Returns chronological stream of recent infrastructure degradation, circuit trips, route switches, and recovery events.",
)
async def get_recent_events(
    limit: int = Query(default=15, ge=1, le=50, description="Max events to return"),
    router_engine: SmartRouter = Depends(get_router),
) -> EventFeedResponseSchema:
    """Returns chronological stream of recent intelligence events."""
    events = router_engine.get_recent_events(limit=limit)
    return EventFeedResponseSchema(
        events=events,
        total_events=len(events),
    )
