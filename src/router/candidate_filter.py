"""
Candidate Route Filtering and Compatibility Validation Engine.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.router.circuit_breaker import CircuitState, RouteHealthTracker
from src.utils.logger import get_logger

logger = get_logger("CandidateFilter")


def filter_candidate_routes(
    payment_request: Dict[str, Any],
    all_routes: List[Dict[str, Any]],
    health_trackers: Dict[str, RouteHealthTracker],
    current_time: float = 0.0,
    is_probe_eligible: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Identifies all valid, healthy, and compatible candidate payment routes for a transaction request.

    Args:
        payment_request: Incoming payment request dictionary (amount, payment_method, bank...).
        all_routes: Complete list of configured route definitions from routes_config.yaml.
        health_trackers: Dictionary mapping route_id to active RouteHealthTracker instances.
        current_time: Current simulation timestamp in seconds.
        is_probe_eligible: Whether this transaction qualifies for a HALF_OPEN health test probe.

    Returns:
        Tuple of (eligible_routes: List[dict], excluded_routes: List[dict]).
    """
    requested_method = str(payment_request.get("payment_method", "")).upper()
    requested_bank = str(payment_request.get("bank", "")).upper()

    eligible = []
    excluded = []

    for route in all_routes:
        route_id = route["route_id"]
        tracker = health_trackers.get(route_id)

        # 1. Check Active Status
        if not route.get("active", True):
            excluded.append({
                "route_id": route_id,
                "route": route,
                "reason": "ROUTE_INACTIVE",
            })
            continue

        # 2. Check Bank Compatibility
        route_bank = str(route.get("bank", "")).upper()
        if requested_bank and route_bank != requested_bank:
            excluded.append({
                "route_id": route_id,
                "route": route,
                "reason": f"BANK_MISMATCH (Expected {requested_bank}, Got {route_bank})",
            })
            continue

        # 3. Check Payment Method Compatibility
        supported_methods = [str(m).upper() for m in route.get("supported_payment_methods", [])]
        if requested_method not in supported_methods:
            excluded.append({
                "route_id": route_id,
                "route": route,
                "reason": f"PAYMENT_METHOD_UNSUPPORTED (Requires {requested_method})",
            })
            continue

        # 4. Check Circuit Breaker State
        if tracker is not None:
            can_pass, circuit_state = tracker.can_route(current_time, is_probe_eligible=is_probe_eligible)
            if not can_pass:
                excluded.append({
                    "route_id": route_id,
                    "route": route,
                    "circuit_state": circuit_state.value,
                    "reason": f"CIRCUIT_BREAKER_{circuit_state.value}",
                })
                continue
            
            # Enrich route with current circuit state and rolling health
            enriched_route = route.copy()
            enriched_route["circuit_state"] = circuit_state.value
            enriched_route["rolling_health"] = tracker.rolling_success_rate
            enriched_route["median_latency"] = tracker.median_latency_ms
            eligible.append(enriched_route)
        else:
            enriched_route = route.copy()
            enriched_route["circuit_state"] = CircuitState.CLOSED.value
            enriched_route["rolling_health"] = route.get("baseline_success_rate", 0.95)
            enriched_route["median_latency"] = route.get("expected_latency_ms", 150)
            eligible.append(enriched_route)

    return eligible, excluded
