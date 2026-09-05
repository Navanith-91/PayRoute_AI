"""
3-State Dynamic Circuit Breaker and Real-Time Route Health Tracking Engine.
"""

from collections import deque
from enum import Enum
from typing import Any, Deque, Dict, Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger("CircuitBreaker")


class CircuitState(str, Enum):
    """Circuit breaker operational states."""
    CLOSED = "CLOSED"        # Normal operational state: fully eligible for traffic
    OPEN = "OPEN"            # Tripped/Degraded state: excluded from candidate selection
    HALF_OPEN = "HALF_OPEN"  # Recovery testing state: allows limited test probes


class RouteHealthTracker:
    """
    Maintains bounded rolling telemetry and circuit breaker state transitions for a single route.
    """

    def __init__(
        self,
        route_id: str,
        failure_rate_threshold: float = 0.40,
        minimum_transactions: int = 20,
        recovery_timeout_seconds: float = 30.0,
        rolling_window_size: int = 100,
        baseline_success_rate: float = 0.95,
        baseline_latency_ms: int = 150,
    ) -> None:
        self.route_id = route_id
        self.failure_rate_threshold = failure_rate_threshold
        self.minimum_transactions = minimum_transactions
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.rolling_window_size = rolling_window_size
        self.baseline_success_rate = baseline_success_rate
        self.baseline_latency_ms = baseline_latency_ms

        self.state: CircuitState = CircuitState.CLOSED
        self.tripped_at: Optional[float] = None
        self.last_transition_time: Optional[float] = None

        # Bounded deques for rolling stats
        self.rolling_outcomes: Deque[int] = deque(maxlen=rolling_window_size)  # 1=fail, 0=success
        self.rolling_latencies: Deque[int] = deque(maxlen=rolling_window_size)

        # Lifetime counters
        self.total_transactions: int = 0
        self.total_successes: int = 0
        self.total_failures: int = 0
        self.half_open_probes: int = 0

    @property
    def rolling_failure_rate(self) -> float:
        """Computes current failure rate over the active rolling window."""
        if not self.rolling_outcomes:
            return 1.0 - self.baseline_success_rate
        return sum(self.rolling_outcomes) / len(self.rolling_outcomes)

    @property
    def rolling_success_rate(self) -> float:
        """Computes current success rate over the active rolling window."""
        return 1.0 - self.rolling_failure_rate

    @property
    def median_latency_ms(self) -> float:
        """Calculates median latency over recent transactions."""
        if not self.rolling_latencies:
            return float(self.baseline_latency_ms)
        return float(sorted(self.rolling_latencies)[len(self.rolling_latencies) // 2])

    def can_route(
        self,
        current_time: float,
        is_probe_eligible: bool = False,
    ) -> Tuple[bool, CircuitState]:
        """
        Determines whether the route can receive a transaction.

        Args:
            current_time: Simulation timestamp in seconds.
            is_probe_eligible: Flag indicating if transaction qualifies as a health probe.

        Returns:
            Tuple of (is_eligible: bool, current_state: CircuitState).
        """
        if self.state == CircuitState.CLOSED:
            return True, CircuitState.CLOSED

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self.tripped_at is not None and (current_time - self.tripped_at) >= self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_transition_time = current_time
                logger.info(f"Circuit Breaker [{self.route_id}]: OPEN -> HALF_OPEN (Testing recovery).")
                if is_probe_eligible:
                    return True, CircuitState.HALF_OPEN
                return False, CircuitState.HALF_OPEN
            return False, CircuitState.OPEN

        if self.state == CircuitState.HALF_OPEN:
            if is_probe_eligible:
                return True, CircuitState.HALF_OPEN
            return False, CircuitState.HALF_OPEN

        return False, self.state

    def record_outcome(
        self,
        payment_status: int,  # 0 = SUCCESS, 1 = FAILED
        latency_ms: int,
        current_time: float,
        is_probe: bool = False,
    ) -> None:
        """
        Records transaction result and executes dynamic state transition logic.

        Args:
            payment_status: 0 for success, 1 for failure.
            latency_ms: Observed transaction latency.
            current_time: Current simulation timestamp.
            is_probe: Whether this transaction was a HALF_OPEN health test probe.
        """
        is_failure = (payment_status == 1)
        self.rolling_outcomes.append(1 if is_failure else 0)
        self.rolling_latencies.append(latency_ms)

        self.total_transactions += 1
        if is_failure:
            self.total_failures += 1
        else:
            self.total_successes += 1

        # State Transition Machine
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_probes += 1
            if not is_failure:
                # Probe succeeded -> Route recovered! Transition back to CLOSED
                self.state = CircuitState.CLOSED
                self.tripped_at = None
                self.last_transition_time = current_time
                logger.info(f"Circuit Breaker [{self.route_id}]: HALF_OPEN -> CLOSED (Route successfully recovered).")
            else:
                # Probe failed -> Route still unhealthy. Trip back to OPEN
                self.state = CircuitState.OPEN
                self.tripped_at = current_time
                self.last_transition_time = current_time
                logger.warning(f"Circuit Breaker [{self.route_id}]: HALF_OPEN -> OPEN (Probe failed, re-tripping).")

        elif self.state == CircuitState.CLOSED:
            # Check if rolling failure rate exceeds threshold after minimum transaction sample
            if len(self.rolling_outcomes) >= self.minimum_transactions:
                if self.rolling_failure_rate >= self.failure_rate_threshold:
                    self.state = CircuitState.OPEN
                    self.tripped_at = current_time
                    self.last_transition_time = current_time
                    logger.warning(
                        f"Circuit Breaker [{self.route_id}]: CLOSED -> OPEN "
                        f"(Failure Rate {self.rolling_failure_rate*100:.1f}% >= Threshold {self.failure_rate_threshold*100:.1f}% "
                        f"over {len(self.rolling_outcomes)} txns)."
                    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current route health and circuit state to dictionary."""
        return {
            "route_id": self.route_id,
            "circuit_state": self.state.value,
            "rolling_success_rate": round(self.rolling_success_rate, 4),
            "rolling_failure_rate": round(self.rolling_failure_rate, 4),
            "median_latency_ms": round(self.median_latency_ms, 1),
            "total_transactions": self.total_transactions,
            "total_failures": self.total_failures,
            "tripped_at": self.tripped_at,
        }
