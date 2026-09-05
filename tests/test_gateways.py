"""
Unit and Integration Tests for Razorpay, PhonePe, and Google Pay Gateway Adapters & Settings API.
"""

import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from api.dependencies import init_app_services
from api.main import app
from database.db_manager import DatabaseManager
from src.gateways.gateway_manager import GatewayManager
from src.gateways.gpay_adapter import GPayAdapter
from src.gateways.phonepe_adapter import PhonePeAdapter
from src.gateways.razorpay_adapter import RazorpayAdapter


class TestGatewayAdapters(unittest.TestCase):
    """Unit tests for individual gateway adapters."""

    def test_razorpay_adapter_offline_sandbox(self):
        creds = {"api_key_id": "rzp_test_1234567890", "api_key_secret": "secret12345678", "environment": "SANDBOX"}
        result = RazorpayAdapter.test_connection(creds)
        self.assertIn("status", result)
        self.assertIn("latency_ms", result)
        self.assertIn("message", result)
        self.assertIn(result["status"], ["CONNECTED", "ERROR", "SIMULATED_SANDBOX", "NETWORK_ERROR", "AUTHENTICATION_FAILED"])

    def test_phonepe_adapter_checksum_and_test(self):
        checksum = PhonePeAdapter.calculate_checksum('{"merchantId":"PGTESTPAYUAT"}', "/pg/v1/pay", "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399", "1")
        self.assertTrue(checksum.endswith("###1"))
        
        creds = {
            "merchant_id": "PGTESTPAYUAT",
            "salt_key": "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399",
            "salt_index": "1",
            "environment": "SANDBOX",
        }
        result = PhonePeAdapter.test_connection(creds)
        self.assertIn("status", result)
        self.assertIn("latency_ms", result)
        self.assertIn("message", result)

    def test_gpay_adapter_vpa_and_intent(self):
        self.assertTrue(GPayAdapter.validate_vpa("merchant@icici"))
        self.assertFalse(GPayAdapter.validate_vpa("invalid-vpa-without-at"))

        creds = {"merchant_vpa": "bharatmart@okaxis", "provider_name": "BharatMart", "environment": "SANDBOX"}
        intent_res = GPayAdapter.create_upi_intent(creds, amount_inr=499.0, transaction_id="TXN_123")
        self.assertTrue(intent_res["success"])
        upi_uri = intent_res["data"]["upi_uri"]
        self.assertTrue(upi_uri.startswith("upi://pay?"))
        self.assertIn("pa=bharatmart%40okaxis", upi_uri)
        self.assertIn("am=499.00", upi_uri)

        result = GPayAdapter.test_connection(creds)
        self.assertEqual(result["status"], "CONNECTED")


class TestGatewayManager(unittest.TestCase):
    """Unit tests for GatewayManager."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = str(Path(cls.temp_dir.name) / "test_gw_mgr.db")
        cls.db = DatabaseManager(db_path=cls.test_db_path)
        cls.db.initialize_schema()
        cls.db.seed_initial_entities()
        cls.manager = GatewayManager(db_manager=cls.db)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_list_and_get_credentials(self):
        creds_list = self.manager.list_all_credentials(mask_secrets=True)
        self.assertIsInstance(creds_list, list)
        self.assertGreaterEqual(len(creds_list), 3)

        rzp = self.manager.get_credentials("RAZORPAY", mask_secrets=True)
        self.assertIsNotNone(rzp)
        self.assertEqual(rzp["provider_id"], "RAZORPAY")
        self.assertTrue(rzp["api_key_secret"].startswith("••••"))

    def test_save_and_test_connection(self):
        save_res = self.manager.save_credentials(
            provider_id="GPAY",
            data={
                "merchant_vpa": "teststore@okaxis",
                "environment": "SANDBOX",
            },
        )
        self.assertTrue(save_res["success"])

        test_res = self.manager.test_connection("GPAY")
        self.assertTrue(test_res["success"])
        self.assertEqual(test_res["status"], "CONNECTED")


class TestGatewayAPIRoutes(unittest.TestCase):
    """Integration tests for FastAPI gateway endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = str(Path(cls.temp_dir.name) / "test_gw_api.db")
        init_app_services(db_path=cls.test_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_get_all_gateway_credentials_endpoint(self):
        response = self.client.get("/api/v1/gateways/credentials")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 3)

    def test_get_single_gateway_credentials_endpoint(self):
        response = self.client.get("/api/v1/gateways/RAZORPAY/credentials")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["provider_id"], "RAZORPAY")

    def test_save_gateway_credentials_endpoint(self):
        payload = {
            "api_key_id": "rzp_test_updated123",
            "environment": "SANDBOX",
            "is_enabled": True,
        }
        response = self.client.post("/api/v1/gateways/RAZORPAY/credentials", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["provider_id"], "RAZORPAY")
        self.assertIn("status", data)

    def test_test_gateway_connection_endpoint(self):
        response = self.client.post("/api/v1/gateways/PHONEPE/test-connection")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)

    def test_get_transactions_endpoint(self):
        response = self.client.get("/api/v1/transactions?limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("transactions", data)
        self.assertIn("total", data)
        self.assertIn("limit", data)



if __name__ == "__main__":
    unittest.main()
