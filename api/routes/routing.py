"""
Smart Routing and Route Recommendation Endpoints.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_router
from api.schemas import PaymentContextInput, RoutingRecommendationResponseSchema
from src.router.router import SmartRouter
from src.utils.logger import get_logger

logger = get_logger("RoutingRouter")
router = APIRouter(prefix="/api/v1/route", tags=["Smart Routing"])


@router.post(
    "/recommend",
    response_model=RoutingRecommendationResponseSchema,
    summary="Recommend Optimal Payment Route",
    status_code=status.HTTP_200_OK,
)
def recommend_payment_route(
    payload: PaymentContextInput,
    smart_router: SmartRouter = Depends(get_router),
) -> RoutingRecommendationResponseSchema:
    """
    Evaluates all eligible payment routes for an incoming transaction and selects the route
    with the highest expected utility score based on ML failure prediction, latency, cost,
    and 3-state circuit breaker health.

    Returns:
    - **primary_route**: Recommended best payment route.
    - **fallback_route**: Recommended backup route if primary fails.
    - **routing_strategy**: Strategy label (`AI_OPTIMAL`, `CIRCUIT_BREAKER_OVERRIDE`, `EXPLORATION`, `SINGLE_ROUTE`, `NO_ROUTE_AVAILABLE`).
    - **candidates**: Complete evaluated and ranked candidate matrix.
    - **explanation**: Feature attribution explaining why the recommended route was selected.
    """
    try:
        data = payload.to_dict()
        current_time = time.time()

        decision = smart_router.route_payment(
            payment_request=data,
            current_time=current_time,
            enable_exploration=True,
            include_explanation=True,
        )

        return RoutingRecommendationResponseSchema(
            status=decision["status"],
            transaction_id=data["transaction_id"],
            primary_route=decision.get("primary_route"),
            fallback_route=decision.get("fallback_route"),
            routing_strategy=decision["routing_strategy"],
            primary_predicted_success_prob=decision.get("primary_predicted_success_prob"),
            primary_predicted_failure_prob=decision.get("primary_predicted_failure_prob"),
            primary_utility_score=decision.get("primary_utility_score"),
            primary_circuit_state=decision.get("primary_circuit_state"),
            candidates=decision.get("candidates", []),
            excluded_candidates=decision.get("excluded_candidates", []),
            explanation=decision.get("explanation"),
        )
    except Exception as e:
        logger.error(f"Error during route recommendation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Smart routing engine error: {str(e)}",
        )
