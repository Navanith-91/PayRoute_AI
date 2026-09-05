"""
Unit and Integration Tests for Traffic Simulation, Event Logging, and Decision Policy Engine.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from database.db_manager import DatabaseManager
from src.decision_engine.event_logger import EventLogger
from src.decision_engine.policy_engine import DecisionAction, DecisionPolicyEngine, DecisionResult
from src.decision_engine.traffic_simulator import (
    DemoScenario,
    LoadLevel,
    RouteStatus,
    TrafficSimulator,
)
from src.router.router import SmartRouter


class TestTrafficSimulator(unittest.TestCase):
    """Verifies route load generation, latency surges, and scenario controls."""

    def setUp(self):
        self.sample_routes = [
            {
                "route_id": "ROUTE_HDFC_RAZORPAY",
                "bank": "HDFC",
                "gateway": "RAZORPAY_SIM",
                "supported_payment_methods": ["UPI", "CREDIT_CARD"],
                "expected_latency_ms": 130,
                "baseline_success_rate": 0.95,
            },
            {
                "route_id": "ROUTE_SBI_RAZORPAY",
                "bank": "SBI",
                "gateway": "RAZORPAY_SIM",
                "supported_payment_methods": ["UPI", "NET_BANKING"],
                "expected_latency_ms": 220,
                "baseline_success_rate": 0.90,
            },
            {
                "route_id": "ROUTE_SBI_CASHFREE",
                "bank": "SBI",
                "gateway": "CASHFREE_SIM",
                "supported_payment_methods": ["UPI", "CREDIT_CARD"],
                "expected_latency_ms": 240,
                "baseline_success_rate": 0.89,
            },
        ]
        self.simulator = TrafficSimulator(routes=self.sample_routes, random_seed=42)

    def test_load_levels_and_effective_latency(self):
        self.assertEqual(self.simulator.get_load_level(0.20), LoadLevel.LOW)
        self.assertEqual(self.simulator.get_load_level(0.55), LoadLevel.MODERATE)
        self.assertEqual(self.simulator.get_load_level(0.78), LoadLevel.HIGH)
        self.assertEqual(self.simulator.get_load_level(0.95), LoadLevel.CRITICAL)

        # Baseline latency surge
        eff_lat = self.simulator.compute_effective_latency("ROUTE_HDFC_RAZORPAY", 130)
        self.assertTrue(eff_lat >= 130)

    def test_route_status_evaluation(self):
        # Healthy
        status_healthy = self.simulator.evaluate_route_status(
            "ROUTE_HDFC_RAZORPAY",
            circuit_state="CLOSED",
            rolling_success_rate=0.96,
            median_latency_ms=140,
        )
        self.assertEqual(status_healthy, RouteStatus.HEALTHY)

        # Unavailable (circuit open)
        status_unavail = self.simulator.evaluate_route_status(
            "ROUTE_HDFC_RAZORPAY",
            circuit_state="OPEN",
            rolling_success_rate=0.95,
            median_latency_ms=130,
        )
        self.assertEqual(status_unavail, RouteStatus.UNAVAILABLE)

    def test_scenario_switching(self):
        res = self.simulator.set_scenario("HIGH_TRAFFIC")
        self.assertEqual(res["scenario"], "HIGH_TRAFFIC")
        load_razorpay = self.simulator.get_route_load("ROUTE_HDFC_RAZORPAY")
        self.assertTrue(load_razorpay >= 0.70)

        # Bank degradation
        res_bank = self.simulator.set_scenario("BANK_DEGRADATION", target_bank="SBI")
        self.assertEqual(res_bank["target_bank"], "SBI")
        load_sbi = self.simulator.get_route_load("ROUTE_SBI_RAZORPAY")
        self.assertTrue(load_sbi >= 0.80)


class TestEventLogger(unittest.TestCase):
    """Verifies real-time intelligence event logging."""

    def test_log_and_retrieve_events(self):
        logger = EventLogger(maxlen=10)
        evt = logger.log_event(
            event_type="ROUTE_SWITCHED",
            title="Route Switch Test",
            description="Switched from Route A to Route B",
            route_id="ROUTE_TEST",
            severity="WARNING",
        )
        self.assertEqual(evt.event_type, "ROUTE_SWITCHED")

        events = logger.get_recent_events(limit=5)
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[0]["title"], "Route Switch Test")


class TestDecisionPolicyEngine(unittest.TestCase):
    """Verifies decision policy actions and rationales."""

    def setUp(self):
        self.engine = DecisionPolicyEngine()

    def test_process_now_policy(self):
        ranked = [
            {
                "route_id": "ROUTE_HDFC_RAZORPAY",
                "current_load": 0.25,
                "route_status": "HEALTHY",
                "success_probability": 0.94,
                "expected_latency_ms": 130,
            }
        ]
        res = self.engine.evaluate_decision(
            payment_request={"payment_method": "UPI", "bank": "HDFC"},
            ranked_candidates=ranked,
            excluded_candidates=[],
        )
        self.assertEqual(res.action, DecisionAction.PROCESS_NOW)

    def test_switch_route_policy(self):
        ranked = [
            {
                "route_id": "ROUTE_SBI_CASHFREE",
                "current_load": 0.35,
                "route_status": "HEALTHY",
                "success_probability": 0.88,
                "expected_latency_ms": 180,
            },
            {
                "route_id": "ROUTE_SBI_RAZORPAY",
                "current_load": 0.92,
                "route_status": "CRITICAL",
                "success_probability": 0.60,
                "expected_latency_ms": 380,
            },
        ]
        res = self.engine.evaluate_decision(
            payment_request={"payment_method": "UPI", "bank": "SBI"},
            ranked_candidates=ranked,
            excluded_candidates=[],
        )
        self.assertEqual(res.action, DecisionAction.SWITCH_ROUTE)
        self.assertEqual(res.recommended_route, "ROUTE_SBI_CASHFREE")
        self.assertTrue(res.success_uplift_pct > 0)

    def test_wait_and_retry_policy(self):
        ranked = [
            {
                "route_id": "ROUTE_SBI_RAZORPAY",
                "current_load": 0.95,
                "route_status": "CRITICAL",
                "success_probability": 0.52,
                "expected_latency_ms": 650,
            },
            {
                "route_id": "ROUTE_SBI_CASHFREE",
                "current_load": 0.94,
                "route_status": "CRITICAL",
                "success_probability": 0.50,
                "expected_latency_ms": 680,
            },
        ]
        res = self.engine.evaluate_decision(
            payment_request={"payment_method": "UPI", "bank": "SBI"},
            ranked_candidates=ranked,
            excluded_candidates=[],
        )
        self.assertEqual(res.action, DecisionAction.WAIT_AND_RETRY)
        self.assertEqual(res.suggested_wait_seconds, 15)


    def test_alternative_payment_method_policy(self):
        ranked = [
            {
                "route_id": "ROUTE_SBI_RAZORPAY",
                "current_load": 0.85,
                "route_status": "DEGRADED",
                "success_probability": 0.58,
                "expected_latency_ms": 400,
            }
        ]
        method_alts = {"UPI": 0.58, "CREDIT_CARD": 0.89, "NET_BANKING": 0.82}
        res = self.engine.evaluate_decision(
            payment_request={"payment_method": "UPI", "bank": "SBI"},
            ranked_candidates=ranked,
            excluded_candidates=[],
            method_alternatives=method_alts,
        )
        self.assertEqual(res.action, DecisionAction.USE_ALTERNATIVE_PAYMENT_METHOD)
        self.assertEqual(res.alternative_payment_method, "CREDIT_CARD")


class TestUnifiedAPIEndpoints(unittest.TestCase):
    """Verifies FastAPI unified pre-payment analysis and execution endpoints."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_decision_api.db")
        self.db = DatabaseManager(db_path=self.db_path)
        self.db.initialize_schema()
        self.db.seed_initial_entities()

        from api.dependencies import get_db, get_router
        self.router_engine = SmartRouter(random_seed=42)
        self.app = create_app()
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[get_router] = lambda: self.router_engine
        self.client = TestClient(self.app)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_analyze_payment_endpoint(self):
        payload = {
            "amount": 8500.0,
            "currency": "INR",
            "payment_method": "UPI",
            "bank": "SBI",
        }
        res = self.client.post("/api/v1/payment/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("risk", data)
        self.assertIn("infrastructure", data)
        self.assertIn("decision", data)
        self.assertIn("routes", data)
        self.assertTrue(len(data["routes"]) >= 1)

    def test_process_payment_endpoint(self):
        payload = {
            "amount": 5000.0,
            "currency": "INR",
            "payment_method": "UPI",
            "bank": "HDFC",
        }
        res = self.client.post("/api/v1/payment/process", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertIn("latency_ms", data)
        self.assertIn("route_id", data)

    def test_scenario_and_status_endpoints(self):
        sc_res = self.client.post(
            "/api/v1/simulation/scenario",
            json={"scenario": "HIGH_TRAFFIC"},
        )
        self.assertEqual(sc_res.status_code, 200)
        self.assertEqual(sc_res.json()["scenario"], "HIGH_TRAFFIC")

        stat_res = self.client.get("/api/v1/system/status")
        self.assertEqual(stat_res.status_code, 200)
        self.assertEqual(stat_res.json()["active_scenario"], "HIGH_TRAFFIC")

        evt_res = self.client.get("/api/v1/events/recent?limit=5")
        self.assertEqual(evt_res.status_code, 200)
        self.assertTrue(evt_res.json()["total_events"] >= 1)


if __name__ == "__main__":
    unittest.main()
