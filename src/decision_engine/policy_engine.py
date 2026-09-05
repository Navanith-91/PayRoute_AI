"""
Decision Policy Engine for PayRoute AI.
Synthesizes ML failure predictions, route loads, infrastructure states, and multi-rail alternatives
into actionable user recommendations (PROCESS_NOW, SWITCH_ROUTE, WAIT_AND_RETRY, USE_ALTERNATIVE_PAYMENT_METHOD, NO_ROUTE_AVAILABLE).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.decision_engine.traffic_simulator import RouteStatus
from src.utils.logger import get_logger

logger = get_logger("DecisionPolicyEngine")


class DecisionAction(str, Enum):
    """Actionable recommendation categories produced by the decision policy."""
    PROCESS_NOW = "PROCESS_NOW"
    SWITCH_ROUTE = "SWITCH_ROUTE"
    WAIT_AND_RETRY = "WAIT_AND_RETRY"
    USE_ALTERNATIVE_PAYMENT_METHOD = "USE_ALTERNATIVE_PAYMENT_METHOD"
    NO_ROUTE_AVAILABLE = "NO_ROUTE_AVAILABLE"


@dataclass
class DecisionResult:
    """Structured decision output containing rationale, routes, and quantified uplift."""
    action: DecisionAction
    title: str
    message: str
    recommended_route: Optional[str]
    original_route: Optional[str]
    fallback_route: Optional[str]
    expected_success_prob: float
    expected_latency_ms: int
    success_uplift_pct: Optional[float] = None
    latency_reduction_ms: Optional[int] = None
    alternative_payment_method: Optional[str] = None
    suggested_wait_seconds: int = 0
    key_drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts dataclass to serializable dictionary."""
        return {
            "action": self.action.value,
            "title": self.title,
            "message": self.message,
            "recommended_route": self.recommended_route,
            "original_route": self.original_route,
            "fallback_route": self.fallback_route,
            "expected_success_prob": round(self.expected_success_prob, 4),
            "expected_latency_ms": self.expected_latency_ms,
            "success_uplift_pct": round(self.success_uplift_pct, 2) if self.success_uplift_pct is not None else None,
            "latency_reduction_ms": self.latency_reduction_ms,
            "alternative_payment_method": self.alternative_payment_method,
            "suggested_wait_seconds": self.suggested_wait_seconds,
            "key_drivers": self.key_drivers,
        }


class DecisionPolicyEngine:
    """
    Evaluates candidates and environmental signals to generate optimized decision policies.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        policy_cfg = self.config.get("decision_policy", {})
        self.switch_success_delta = policy_cfg.get("switch_success_threshold_delta", 0.05)
        self.high_traffic_threshold = policy_cfg.get("high_traffic_load_threshold", 0.75)
        self.wait_retry_load = policy_cfg.get("wait_retry_load_threshold", 0.88)
        self.wait_seconds = policy_cfg.get("wait_retry_duration_seconds", 15)
        self.alt_method_uplift = policy_cfg.get("alternative_method_uplift_threshold", 0.12)

    def evaluate_decision(
        self,
        payment_request: Dict[str, Any],
        ranked_candidates: List[Dict[str, Any]],
        excluded_candidates: List[Dict[str, Any]],
        method_alternatives: Optional[Dict[str, float]] = None,
    ) -> DecisionResult:
        """
        Executes multi-criteria decision rules on candidate evaluations.

        Args:
            payment_request: Original payment request context.
            ranked_candidates: Evaluated candidate routes ranked by utility score.
            excluded_candidates: Excluded routes (e.g. circuit OPEN).
            method_alternatives: Dict of alternative payment method -> expected success probability.

        Returns:
            DecisionResult dataclass instance.
        """
        # 1. Check for NO_ROUTE_AVAILABLE
        if not ranked_candidates:
            return DecisionResult(
                action=DecisionAction.NO_ROUTE_AVAILABLE,
                title="PAYMENT ROUTES TEMPORARILY UNAVAILABLE",
                message="All available payment routes are currently experiencing problems. Please try again shortly.",
                recommended_route=None,
                original_route=None,
                fallback_route=None,
                expected_success_prob=0.0,
                expected_latency_ms=0,
                key_drivers=[
                    "All candidate circuits OPEN or unreachable",
                    "Gateway downtime detected",
                ],
            )

        top_candidate = ranked_candidates[0]
        fallback_candidate = ranked_candidates[1] if len(ranked_candidates) > 1 else None

        top_route_id = top_candidate["route_id"]
        top_name = top_candidate.get("route_name", top_route_id)
        top_load = top_candidate.get("current_load", 0.25)
        top_status = top_candidate.get("route_status", RouteStatus.HEALTHY.value)
        top_succ = float(top_candidate.get("success_probability", 0.90))
        top_lat = int(top_candidate.get("expected_latency_ms", 150))

        # Default route is typically the primary direct/aggregator route before smart intervention
        default_candidate = ranked_candidates[-1] if len(ranked_candidates) > 1 else top_candidate
        default_route_id = default_candidate["route_id"]
        default_name = default_candidate.get("route_name", default_route_id)
        default_load = default_candidate.get("current_load", 0.25)
        default_succ = float(default_candidate.get("success_probability", 0.70))
        default_lat = int(default_candidate.get("expected_latency_ms", 220))

        # 2. Check for USE_ALTERNATIVE_PAYMENT_METHOD
        # If current payment method has degraded expected success, but alternative method (e.g. CARD) is significantly better
        current_method = payment_request.get("payment_method", "UPI")
        if method_alternatives and top_succ < 0.75:
            for alt_method, alt_succ in method_alternatives.items():
                if alt_method != current_method and (alt_succ - top_succ) >= self.alt_method_uplift:
                    uplift = (alt_succ - top_succ) * 100.0
                    alt_display = alt_method.replace("_", " ").title()
                    return DecisionResult(
                        action=DecisionAction.USE_ALTERNATIVE_PAYMENT_METHOD,
                        title="PAYMENT METHOD TEMPORARILY CONGESTED",
                        message=(
                            f"{current_method} is currently experiencing high traffic ({top_load*100:.0f}% load). "
                            f"{alt_display} payments are currently operating normally."
                        ),
                        recommended_route=top_route_id,
                        original_route=default_route_id,
                        fallback_route=fallback_candidate["route_id"] if fallback_candidate else None,
                        expected_success_prob=top_succ,
                        expected_latency_ms=top_lat,
                        success_uplift_pct=uplift,
                        alternative_payment_method=alt_method,
                        key_drivers=[
                            f"{current_method} rail is congested",
                            f"{alt_display} has {alt_succ*100:.0f}% estimated success (+{uplift:.0f}% lift)",
                            "User must explicitly choose to switch payment method",
                        ],
                    )

        # 3. Check for WAIT_AND_RETRY
        # If ALL candidate routes are severely congested (> 88% load or CRITICAL status)
        all_congested = all(
            c.get("current_load", 0.0) >= self.wait_retry_load or c.get("route_status") == RouteStatus.CRITICAL.value
            for c in ranked_candidates
        )
        if all_congested and top_succ < 0.65:
            return DecisionResult(
                action=DecisionAction.WAIT_AND_RETRY,
                title="HIGH TRAFFIC DETECTED",
                message=(
                    f"Your selected payment route is currently experiencing heavy traffic ({top_load*100:.0f}% load). "
                    f"Please wait approximately {self.wait_seconds} seconds and continue your payment."
                ),
                recommended_route=top_route_id,
                original_route=default_route_id,
                fallback_route=fallback_candidate["route_id"] if fallback_candidate else None,
                expected_success_prob=top_succ,
                expected_latency_ms=top_lat,
                suggested_wait_seconds=self.wait_seconds,
                key_drivers=[
                    f"Current route traffic is high ({top_load*100:.0f}%)",
                    f"Route latency is elevated ({top_lat}ms)",
                    "Recent payment success rate decreased",
                    f"Waiting {self.wait_seconds} seconds provides better expected reliability",
                ],
            )

        # 4. Check for SWITCH_ROUTE
        # If default route is congested/degraded AND top ranked candidate is materially better
        is_default_degraded = (
            default_load >= self.high_traffic_threshold
            or default_candidate.get("route_status") in [RouteStatus.BUSY.value, RouteStatus.DEGRADED.value, RouteStatus.CRITICAL.value]
            or any("CIRCUIT_BREAKER_OPEN" in ex.get("reason", "") for ex in excluded_candidates)
        )

        has_better_route = (
            len(ranked_candidates) > 1
            and top_route_id != default_route_id
            and ((top_succ - default_succ) >= self.switch_success_delta or (default_lat - top_lat) >= 40)
        )

        if is_default_degraded and has_better_route:
            succ_uplift = (top_succ - default_succ) * 100.0
            lat_diff = default_lat - top_lat
            return DecisionResult(
                action=DecisionAction.SWITCH_ROUTE,
                title="HEALTHIER PAYMENT ROUTE FOUND",
                message=(
                    f"Your current payment route ({default_name}) is experiencing heavy traffic ({default_load*100:.0f}% load). "
                    f"{top_name} is currently operating normally ({top_load*100:.0f}% load)."
                ),
                recommended_route=top_route_id,
                original_route=default_route_id,
                fallback_route=fallback_candidate["route_id"] if fallback_candidate else None,
                expected_success_prob=top_succ,
                expected_latency_ms=top_lat,
                success_uplift_pct=succ_uplift,
                latency_reduction_ms=lat_diff if lat_diff > 0 else 0,
                key_drivers=[
                    f"Current route traffic is high ({default_load*100:.0f}%)",
                    f"Route latency is elevated ({default_lat}ms)",
                    "Recent payment success rate decreased",
                    f"{top_name} currently has lower payment risk ({top_succ*100:.0f}% expected success)",
                ],
            )

        # 5. Default: PROCESS_NOW
        return DecisionResult(
            action=DecisionAction.PROCESS_NOW,
            title="PAYMENT ROUTE IS HEALTHY",
            message=f"Your payment route ({top_name}) is healthy and operating normally (Traffic: {top_load*100:.0f}%, Latency: {top_lat}ms). Your payment can continue normally.",
            recommended_route=top_route_id,
            original_route=top_route_id,
            fallback_route=fallback_candidate["route_id"] if fallback_candidate else None,
            expected_success_prob=top_succ,
            expected_latency_ms=top_lat,
            key_drivers=[
                f"Route traffic is normal ({top_load*100:.0f}%)",
                f"Provider latency is fast ({top_lat}ms)",
                f"Expected payment success rate is high ({top_succ*100:.0f}%)",
                "Circuit breaker is healthy and CLOSED",
            ],
        )

