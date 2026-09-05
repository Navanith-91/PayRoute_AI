"""
Unit tests for the Smart Routing Algorithm, Route Scorer, and 3-State Dynamic Circuit Breakers.
"""

import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.router.candidate_filter import filter_candidate_routes
from src.router.circuit_breaker import CircuitState, RouteHealthTracker
from src.router.router import SmartRouter
from src.router.scorer import RouteScorer


class TestSmartRouter(unittest.TestCase):
    """Test suite for validating candidate filtering, utility scoring, circuit breakers, and routing."""

    @classmethod
    def setUpClass(cls):
        """Initializes SmartRouter instance with deterministic seed."""
        cls.router = SmartRouter(random_seed=42)

    def test_candidate_filtering_by_method_and_bank(self):
        """Verifies candidate filter matches payment method, bank, and active status."""
        req_upi = {"payment_method": "UPI", "bank": "HDFC", "amount": 500.0}
        eligible, excluded = filter_candidate_routes(
            payment_request=req_upi,
            all_routes=self.router.routes,
            health_trackers=self.router.health_trackers,
            current_time=0.0,
        )

        eligible_ids = {r["route_id"] for r in eligible}
        self.assertIn("ROUTE_HDFC_RAZORPAY", eligible_ids)
        self.assertIn("ROUTE_HDFC_CASHFREE", eligible_ids)
        self.assertIn("ROUTE_HDFC_PAYU", eligible_ids)
        self.assertNotIn("ROUTE_SBI_RAZORPAY", eligible_ids)

    def test_multi_objective_scorer_utility(self):
        """Verifies that the route scorer calculates correct weighted utility scores."""
        scorer = RouteScorer(weights={"success": 0.60, "latency": 0.20, "cost": 0.10, "health": 0.10})
        candidates = [
            {
                "route_id": "ROUTE_A",
                "success_probability": 0.95,
                "failure_probability": 0.05,
                "expected_latency_ms": 100,
                "base_fee_pct": 1.5,
                "rolling_health": 0.96,
            },
            {
                "route_id": "ROUTE_B",
                "success_probability": 0.70,
                "failure_probability": 0.30,
                "expected_latency_ms": 350,
                "base_fee_pct": 1.8,
                "rolling_health": 0.75,
            },
        ]
        ranked = scorer.score_candidates(candidates)
        self.assertEqual(len(ranked), 2)
        # Route A has higher success, lower latency, lower fee -> must rank #1
        self.assertEqual(ranked[0]["route_id"], "ROUTE_A")
        self.assertGreater(ranked[0]["utility_score"], ranked[1]["utility_score"])

    def test_circuit_breaker_minimum_transactions_guard(self):
        """Verifies circuit breaker does NOT trip before minimum transactions (N < 20)."""
        tracker = RouteHealthTracker(
            route_id="TEST_ROUTE",
            failure_rate_threshold=0.40,
            minimum_transactions=20,
        )
        # Record 10 consecutive failures
        for i in range(10):
            tracker.record_outcome(payment_status=1, latency_ms=500, current_time=float(i))

        # Must remain CLOSED because total transactions (10) < min transactions (20)
        self.assertEqual(tracker.state, CircuitState.CLOSED)
        can_pass, state = tracker.can_route(current_time=10.0)
        self.assertTrue(can_pass)
        self.assertEqual(state, CircuitState.CLOSED)

    def test_circuit_breaker_trips_to_open(self):
        """Verifies circuit breaker trips to OPEN after reaching threshold over >= 20 txns."""
        tracker = RouteHealthTracker(
            route_id="TEST_ROUTE_TRIP",
            failure_rate_threshold=0.40,
            minimum_transactions=20,
        )
        # Record 10 successes and 15 failures (15 / 25 = 60% failure rate)
        for i in range(10):
            tracker.record_outcome(payment_status=0, latency_ms=100, current_time=float(i))
        for i in range(15):
            tracker.record_outcome(payment_status=1, latency_ms=600, current_time=float(10 + i))

        self.assertEqual(tracker.state, CircuitState.OPEN)
        can_pass, state = tracker.can_route(current_time=25.0)
        self.assertFalse(can_pass)
        self.assertEqual(state, CircuitState.OPEN)

    def test_circuit_breaker_recovery_flow(self):
        """Verifies transition from OPEN -> HALF_OPEN -> CLOSED on successful health probe."""
        tracker = RouteHealthTracker(
            route_id="TEST_RECOVER",
            failure_rate_threshold=0.40,
            minimum_transactions=20,
            recovery_timeout_seconds=30.0,
        )
        # Trip the circuit at t = 100
        for _ in range(25):
            tracker.record_outcome(payment_status=1, latency_ms=700, current_time=100.0)
        self.assertEqual(tracker.state, CircuitState.OPEN)

        # Before timeout (t = 120s, elapsed = 20s < 30s) -> remains OPEN
        can_pass_early, state_early = tracker.can_route(current_time=120.0, is_probe_eligible=True)
        self.assertFalse(can_pass_early)
        self.assertEqual(state_early, CircuitState.OPEN)

        # After timeout (t = 135s, elapsed = 35s >= 30s) -> transitions to HALF_OPEN
        can_pass_probe, state_probe = tracker.can_route(current_time=135.0, is_probe_eligible=True)
        self.assertTrue(can_pass_probe)
        self.assertEqual(state_probe, CircuitState.HALF_OPEN)

        # Probe transaction succeeds -> transitions back to CLOSED!
        tracker.record_outcome(payment_status=0, latency_ms=120, current_time=136.0, is_probe=True)
        self.assertEqual(tracker.state, CircuitState.CLOSED)
        self.assertIsNone(tracker.tripped_at)

    def test_open_route_excluded_from_smart_router(self):
        """Verifies that an OPEN circuit route is never chosen by SmartRouter."""
        # Trip ROUTE_HDFC_RAZORPAY circuit
        tracker = self.router.health_trackers["ROUTE_HDFC_RAZORPAY"]
        for _ in range(25):
            tracker.record_outcome(payment_status=1, latency_ms=800, current_time=10.0)
        self.assertEqual(tracker.state, CircuitState.OPEN)

        req = {"payment_method": "UPI", "bank": "HDFC", "amount": 1000.0}
        decision = self.router.route_payment(req, current_time=15.0, enable_exploration=False)

        # Primary route must NOT be ROUTE_HDFC_RAZORPAY
        self.assertNotEqual(decision["primary_route"], "ROUTE_HDFC_RAZORPAY")
        self.assertIn(decision["primary_route"], ["ROUTE_HDFC_CASHFREE", "ROUTE_HDFC_PAYU"])
        self.assertEqual(decision["routing_strategy"], "CIRCUIT_BREAKER_OVERRIDE")

        # Cleanup: reset tracker
        tracker.state = CircuitState.CLOSED
        tracker.rolling_outcomes.clear()

    def test_no_route_available_condition(self):
        """Verifies handling when all routes for a bank are in OPEN state."""
        # Temporarily trip all SBI routes
        sbi_routes = ["ROUTE_SBI_RAZORPAY", "ROUTE_SBI_CASHFREE", "ROUTE_SBI_DIRECT"]
        for r_id in sbi_routes:
            t = self.router.health_trackers[r_id]
            for _ in range(25):
                t.record_outcome(payment_status=1, latency_ms=900, current_time=50.0)
            self.assertEqual(t.state, CircuitState.OPEN)

        req = {"payment_method": "UPI", "bank": "SBI", "amount": 1500.0}
        decision = self.router.route_payment(req, current_time=55.0, enable_exploration=False)

        self.assertEqual(decision["status"], "NO_ROUTE_AVAILABLE")
        self.assertIsNone(decision["primary_route"])
        self.assertIsNone(decision["fallback_route"])

        # Cleanup
        for r_id in sbi_routes:
            t = self.router.health_trackers[r_id]
            t.state = CircuitState.CLOSED
            t.rolling_outcomes.clear()

    def test_fallback_route_selected_correctly(self):
        """Verifies fallback route is the second-best candidate."""
        req = {"payment_method": "UPI", "bank": "ICICI", "amount": 2000.0}
        decision = self.router.route_payment(req, current_time=1.0, enable_exploration=False)

        self.assertIsNotNone(decision["primary_route"])
        self.assertIsNotNone(decision["fallback_route"])
        self.assertNotEqual(decision["primary_route"], decision["fallback_route"])


if __name__ == "__main__":
    unittest.main()
