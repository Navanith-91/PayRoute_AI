"""
Transaction Execution Simulation, Persistence, and Lookup Endpoints.
"""

from datetime import datetime, timezone
import random
import time
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_db, get_predictor, get_router
from api.schemas import (
    ExplanationResponseSchema,
    TransactionExecuteRequestSchema,
    TransactionExecuteResponseSchema,
)
from database.db_manager import DatabaseManager
from src.ml.predictor import PaymentPredictor
from src.router.router import SmartRouter
from src.utils.logger import get_logger

logger = get_logger("TransactionRouter")
router = APIRouter(prefix="/api/v1", tags=["Transactions & Execution"])


@router.post(
    "/transactions/execute",
    response_model=TransactionExecuteResponseSchema,
    summary="Simulate & Execute Payment Transaction",
    status_code=status.HTTP_200_OK,
)
def execute_transaction(
    payload: TransactionExecuteRequestSchema,
    smart_router: SmartRouter = Depends(get_router),
    predictor: PaymentPredictor = Depends(get_predictor),
    db: DatabaseManager = Depends(get_db),
) -> TransactionExecuteResponseSchema:
    """
    Executes a simulated payment transaction through PayRoute AI:
    1. Selects optimal route via SmartRouter (or accepts manual override).
    2. Simulates realistic payment outcome, network latency, and failure mode.
    3. Updates in-memory route health and evaluates circuit breaker transitions.
    4. Persists the transaction and routing audit trail into SQLite.
    """
    try:
        req_data = payload.payment_request.to_dict()
        txn_id = req_data["transaction_id"]
        current_time = time.time()

        # 1. Route Selection
        if payload.preferred_route:
            selected_route = payload.preferred_route
            strategy = "MANUAL_OVERRIDE"
            routing_decision = {
                "transaction_id": txn_id,
                "primary_route": selected_route,
                "routing_strategy": strategy,
                "primary_fail_prob": 0.15,
                "explanation": {},
            }
        else:
            decision = smart_router.route_payment(
                payment_request=req_data,
                current_time=current_time,
                enable_exploration=True,
                include_explanation=True,
            )
            selected_route = decision.get("primary_route")
            strategy = decision.get("routing_strategy", "AI_OPTIMAL")
            routing_decision = decision
            routing_decision["transaction_id"] = txn_id

        if not selected_route:
            # All routes down / incompatible
            return TransactionExecuteResponseSchema(
                transaction_id=txn_id,
                status="FAILED",
                payment_status=1,
                selected_route=None,
                routing_strategy="NO_ROUTE_AVAILABLE",
                latency_ms=10,
                failure_reason="NO_HEALTHY_ROUTE_AVAILABLE",
                circuit_state="OPEN",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        # 2. Simulate Payment Execution Outcome
        tracker = smart_router.health_trackers.get(selected_route)
        circuit_state = tracker.state.value if tracker else "CLOSED"

        if payload.simulate_outage:
            is_failure = random.random() < 0.80
            observed_latency = random.randint(650, 950)
            reason = "BANK_DOWNTIME" if is_failure else None
        else:
            # Predict risk for the selected route
            req_data["bank_latency_ms"] = int(tracker.median_latency_ms) if tracker else 150
            req_data["bank_success_rate"] = tracker.rolling_success_rate if tracker else 0.95
            risk_eval = predictor.predict_failure(req_data)
            p_fail = risk_eval["failure_probability"]

            is_failure = random.random() < p_fail
            base_lat = tracker.median_latency_ms if tracker else 160
            observed_latency = max(20, int(base_lat + random.gauss(0, 30)))

            if is_failure:
                reason_eval = predictor.predict_failure_reason(req_data)
                reason = reason_eval["predicted_reason"]
            else:
                reason = None

        payment_status = 1 if is_failure else 0
        status_label = "FAILED" if is_failure else "SUCCESS"

        # 3. Update Real-Time Circuit Breaker & Health State
        smart_router.record_outcome(
            route_id=selected_route,
            payment_status=payment_status,
            latency_ms=observed_latency,
            current_time=current_time,
        )

        # 4. Persist to SQLite
        req_data["payment_status"] = payment_status
        req_data["failure_reason"] = reason
        req_data["bank_latency_ms"] = observed_latency // 2
        req_data["gateway_latency_ms"] = observed_latency // 2
        db.create_transaction(req_data)

        routing_decision["predicted_failure_reason"] = reason
        db.create_routing_decision(routing_decision)

        # Record gateway health snapshot
        if tracker:
            db.record_gateway_health(
                gateway_id=selected_route,
                bank=req_data.get("bank", "HDFC"),
                rolling_5m_success_rate=tracker.rolling_success_rate,
                median_latency_ms=int(tracker.median_latency_ms),
                circuit_state=tracker.state.value,
            )

        return TransactionExecuteResponseSchema(
            transaction_id=txn_id,
            status=status_label,
            payment_status=payment_status,
            selected_route=selected_route,
            routing_strategy=strategy,
            latency_ms=observed_latency,
            failure_reason=reason,
            circuit_state=tracker.state.value if tracker else "CLOSED",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"Error during transaction execution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction execution failed: {str(e)}",
        )


@router.get(
    "/transactions/{transaction_id}",
    summary="Retrieve Persisted Transaction Record",
)
def get_transaction_by_id(
    transaction_id: str,
    db: DatabaseManager = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves full transaction record and associated smart routing decision from SQLite."""
    txn = db.get_transaction(transaction_id)
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found.",
        )

    decision = db.get_routing_decision(transaction_id)
    return {
        "transaction": txn,
        "routing_decision": decision,
    }


@router.get(
    "/explain/{transaction_id}",
    response_model=ExplanationResponseSchema,
    summary="Retrieve ML Explainability Attribution for Transaction",
)
def explain_transaction(
    transaction_id: str,
    db: DatabaseManager = Depends(get_db),
) -> ExplanationResponseSchema:
    """Retrieves local ML feature attribution (risk contributors & protective factors) for a transaction."""
    decision = db.get_routing_decision(transaction_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routing decision audit not found for transaction '{transaction_id}'.",
        )

    explanation = decision.get("explanation", {})
    return ExplanationResponseSchema(
        transaction_id=transaction_id,
        selected_route=decision.get("primary_route_id", "UNKNOWN"),
        failure_probability=float(decision.get("primary_fail_prob", 0.0)),
        routing_strategy=decision.get("routing_strategy", "AI_OPTIMAL"),
        predicted_failure_reason=decision.get("predicted_failure_reason"),
        top_risk_contributors=explanation.get("top_risk_contributors", []),
        top_protective_factors=explanation.get("top_protective_factors", []),
    )
