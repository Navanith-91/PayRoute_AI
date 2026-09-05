"""
Unit tests for the Streamlit Dashboard API Client.
Verifies network resilience, error trapping, and response serialization.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import PayRouteAPIClient


class TestDashboardAPIClient(unittest.TestCase):
    """Test suite for PayRouteAPIClient."""

    def setUp(self):
        self.client = PayRouteAPIClient(base_url="http://localhost:8000")

    def test_client_init_and_url_formatting(self):
        """Verifies trailing slash normalization."""
        c = PayRouteAPIClient(base_url="http://localhost:8000///")
        self.assertEqual(c.base_url, "http://localhost:8000")

    def test_connection_error_graceful_handling(self):
        """Verifies client catches connection failures without raising uncaught exceptions."""
        unreachable_client = PayRouteAPIClient(base_url="http://localhost:59999", timeout=0.2)
        res = unreachable_client.check_health()
        self.assertFalse(res["online"])
        self.assertIn("error", res)

        res_predict = unreachable_client.predict_failure({"amount": 100})
        self.assertFalse(res_predict["success"])
        self.assertIn("error", res_predict)

    @patch("requests.post")
    def test_predict_failure_success_parsing(self, mock_post):
        """Verifies successful response parsing for predict_failure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "transaction_id": "txn_123",
            "failure_probability": 0.12,
            "success_probability": 0.88,
            "risk_level": "LOW",
        }
        mock_post.return_value = mock_resp

        res = self.client.predict_failure({"amount": 500.0})
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["failure_probability"], 0.12)
        self.assertEqual(res["data"]["risk_level"], "LOW")

    @patch("requests.post")
    def test_recommend_route_success_parsing(self, mock_post):
        """Verifies successful response parsing for recommend_route."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "ROUTE_SELECTED",
            "primary_route": "ROUTE_HDFC_RAZORPAY",
            "fallback_route": "ROUTE_HDFC_CASHFREE",
            "routing_strategy": "AI_OPTIMAL",
        }
        mock_post.return_value = mock_resp

        res = self.client.recommend_route({"amount": 1000.0, "bank": "HDFC"})
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["primary_route"], "ROUTE_HDFC_RAZORPAY")
        self.assertEqual(res["data"]["routing_strategy"], "AI_OPTIMAL")

    @patch("requests.get")
    def test_gateway_health_success_parsing(self, mock_get):
        """Verifies successful response parsing for get_gateway_health."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "routes": [
                {"route_id": "ROUTE_A", "circuit_state": "CLOSED", "rolling_success_rate": 0.95}
            ],
            "timestamp": "2026-08-30T13:00:00Z",
        }
        mock_get.return_value = mock_resp

        res = self.client.get_gateway_health()
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]["routes"]), 1)
        self.assertEqual(res["data"]["routes"][0]["circuit_state"], "CLOSED")


if __name__ == "__main__":
    unittest.main()
