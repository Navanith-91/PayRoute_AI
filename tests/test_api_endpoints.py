"""
Unit and Integration Tests for FastAPI Backend Endpoints.
Uses FastAPI TestClient to validate route recommendations, ML failure predictions,
transaction executions, database persistence, and analytics.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from api.dependencies import init_app_services
from api.main import app


class TestAPIEndpoints(unittest.TestCase):
    """Test suite for PayRoute AI REST API."""

    @classmethod
    def setUpClass(cls):
        """Initializes test database and FastAPI TestClient."""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = Path(cls.temp_dir.name) / "test_api_payroute.db"

        # Initialize services with temporary test database
        init_app_services(db_path=cls.test_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        """Cleans up temporary files."""
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_health_probes(self):
        """Verifies root /health and /api/v1/health endpoints."""
        res_root = self.client.get("/health")
        self.assertEqual(res_root.status_code, 200)
        self.assertEqual(res_root.json()["status"], "healthy")

        res_v1 = self.client.get("/api/v1/health")
        self.assertEqual(res_v1.status_code, 200)
        self.assertEqual(res_v1.json()["database"], "connected")
        self.assertEqual(res_v1.json()["ml_engine"], "ready")

    def test_02_predict_failure_success(self):
        """Verifies POST /api/v1/predict/failure returns calibrated probabilities and diagnosis."""
        payload = {
            "amount": 2500.0,
            "payment_method": "UPI",
            "bank": "HDFC",
            "merchant_category": "FOOD",
            "hour": 15,
            "device_type": "MOBILE",
            "network_type": "5G",
        }
        res = self.client.post("/api/v1/predict/failure", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("failure_probability", data)
        self.assertIn("success_probability", data)
        self.assertIn("risk_level", data)
        self.assertIn("predicted_failure_reason", data)
        self.assertGreaterEqual(data["failure_probability"], 0.0)
        self.assertLessEqual(data["failure_probability"], 1.0)
        self.assertAlmostEqual(data["failure_probability"] + data["success_probability"], 1.0, places=3)

    def test_03_predict_failure_validation_error(self):
        """Verifies HTTP 422 on invalid amount or unapproved bank."""
        bad_payload = {
            "amount": -50.0,  # Invalid amount <= 0
            "payment_method": "UPI",
            "bank": "UNKNOWN_BANK",  # Unsupported bank
        }
        res = self.client.post("/api/v1/predict/failure", json=bad_payload)
        self.assertEqual(res.status_code, 422)

    def test_04_route_recommendation(self):
        """Verifies POST /api/v1/route/recommend selects primary and fallback routes."""
        payload = {
            "amount": 4500.0,
            "payment_method": "NET_BANKING",
            "bank": "SBI",
            "merchant_category": "TRAVEL",
            "hour": 14,
        }
        res = self.client.post("/api/v1/route/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "ROUTE_SELECTED")
        self.assertIsNotNone(data["primary_route"])
        self.assertIsNotNone(data["fallback_route"])
        self.assertIn(data["routing_strategy"], ["AI_OPTIMAL", "EXPLORATION", "SINGLE_ROUTE"])
        self.assertGreater(len(data["candidates"]), 1)
        self.assertIn("explanation", data)

    def test_05_transaction_execution_and_persistence(self):
        """Verifies POST /api/v1/transactions/execute processes payment and persists to SQLite."""
        payload = {
            "payment_request": {
                "transaction_id": "txn_test_exec_001",
                "amount": 1200.0,
                "payment_method": "UPI",
                "bank": "ICICI",
                "merchant_category": "ECOMMERCE",
            },
            "simulate_outage": False,
        }
        res = self.client.post("/api/v1/transactions/execute", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["transaction_id"], "txn_test_exec_001")
        self.assertIn(data["status"], ["SUCCESS", "FAILED"])
        self.assertIn(data["payment_status"], [0, 1])
        self.assertIsNotNone(data["selected_route"])
        self.assertGreater(data["latency_ms"], 0)

        # Lookup the persisted transaction in SQLite via GET endpoint
        get_res = self.client.get("/api/v1/transactions/txn_test_exec_001")
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.json()
        self.assertEqual(get_data["transaction"]["transaction_id"], "txn_test_exec_001")
        self.assertEqual(get_data["transaction"]["bank"], "ICICI")
        self.assertIsNotNone(get_data["routing_decision"])

    def test_06_transaction_lookup_not_found(self):
        """Verifies HTTP 404 on non-existent transaction ID."""
        res = self.client.get("/api/v1/transactions/non_existent_txn_9999")
        self.assertEqual(res.status_code, 404)

    def test_07_explain_transaction_endpoint(self):
        """Verifies GET /api/v1/explain/{transaction_id} returns feature attribution."""
        # First execute a transaction
        txn_id = "txn_test_explain_002"
        exec_payload = {
            "payment_request": {
                "transaction_id": txn_id,
                "amount": 7500.0,
                "payment_method": "CREDIT_CARD",
                "bank": "AXIS",
                "merchant_category": "ENTERTAINMENT",
            }
        }
        self.client.post("/api/v1/transactions/execute", json=exec_payload)

        # Retrieve explanation
        res = self.client.get(f"/api/v1/explain/{txn_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["transaction_id"], txn_id)
        self.assertIn("top_risk_contributors", data)
        self.assertIn("top_protective_factors", data)

    def test_08_gateways_health_endpoint(self):
        """Verifies GET /api/v1/gateways/health returns all active route states."""
        res = self.client.get("/api/v1/gateways/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("routes", data)
        self.assertGreater(len(data["routes"]), 5)
        for r in data["routes"]:
            self.assertIn("route_id", r)
            self.assertIn(r["circuit_state"], ["CLOSED", "OPEN", "HALF_OPEN"])
            self.assertGreaterEqual(r["rolling_success_rate"], 0.0)

    def test_09_analytics_summary_endpoint(self):
        """Verifies GET /api/v1/analytics/summary returns aggregated counts."""
        res = self.client.get("/api/v1/analytics/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_transactions", data)
        self.assertIn("overall_success_rate_pct", data)
        self.assertIn("gateways_count", data)
        self.assertGreater(data["gateways_count"], 0)


if __name__ == "__main__":
    unittest.main()
