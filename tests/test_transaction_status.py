"""
Unit and Integration Tests for Transaction Status & Lifecycle Tracking.
Verifies demo transaction seeding, timeline generation, debited-but-pending logic, and REST API endpoints.
"""

import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from api.dependencies import get_db, get_router
from api.main import create_app
from database.db_manager import DatabaseManager
from src.router.router import SmartRouter


class TestTransactionStatus(unittest.TestCase):
    """Test suite for Transaction Status & Timeline Verification."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_status.db")
        self.db = DatabaseManager(db_path=self.test_db_path)
        self.db.initialize_schema()

        self.router = SmartRouter()

        self.app = create_app()
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[get_router] = lambda: self.router
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.temp_dir.cleanup()

    def test_demo_transactions_seeded_correctly(self):
        """Verify the 4 pre-seeded demo transactions exist with correct states."""
        # 1. SUCCESS demo
        res_succ = self.db.get_transaction_status("TXN_SUCCESS_001")
        self.assertIsNotNone(res_succ)
        self.assertEqual(res_succ["status"], "SUCCESS")
        self.assertEqual(res_succ["customer_debit_status"], "CONFIRMED")
        self.assertEqual(res_succ["merchant_confirmation_status"], "CONFIRMED")

        # 2. PENDING demo (Debited but unconfirmed)
        res_pend = self.db.get_transaction_status("TXN_PENDING_001")
        self.assertIsNotNone(res_pend)
        self.assertEqual(res_pend["status"], "PENDING")
        self.assertEqual(res_pend["customer_debit_status"], "CONFIRMED")
        self.assertEqual(res_pend["merchant_confirmation_status"], "PENDING")

        # 3. FAILED demo
        res_fail = self.db.get_transaction_status("TXN_FAILED_001")
        self.assertIsNotNone(res_fail)
        self.assertEqual(res_fail["status"], "FAILED")
        self.assertEqual(res_fail["merchant_confirmation_status"], "FAILED")

        # 4. REFUND demo
        res_ref = self.db.get_transaction_status("TXN_REFUND_001")
        self.assertIsNotNone(res_ref)
        self.assertEqual(res_ref["status"], "REFUND_INITIATED")
        self.assertEqual(res_ref["customer_debit_status"], "CONFIRMED")
        self.assertEqual(res_ref["merchant_confirmation_status"], "FAILED")

    def test_timeline_stages_structure(self):
        """Verify that stage timeline contains expected stages and icons."""
        res = self.db.get_transaction_status("TXN_PENDING_001")
        timeline = res["timeline"]
        self.assertEqual(len(timeline), 5)
        
        stages = [t["stage"] for t in timeline]
        self.assertIn("Payment Initiated", stages)
        self.assertIn("Bank Processing", stages)
        self.assertIn("Customer Account Debit", stages)
        self.assertIn("Merchant Confirmation", stages)
        self.assertIn("Final Status", stages)

        # For PENDING: customer debit is COMPLETED, merchant confirmation is PROCESSING/PENDING
        debit_stage = next(t for t in timeline if t["stage"] == "Customer Account Debit")
        self.assertEqual(debit_stage["status"], "COMPLETED")
        merch_stage = next(t for t in timeline if t["stage"] == "Merchant Confirmation")
        self.assertEqual(merch_stage["status"], "PENDING")

    def test_api_get_transaction_status_success(self):
        """Test GET /api/v1/transactions/{transaction_id}/status endpoint."""
        resp = self.client.get("/api/v1/transactions/TXN_PENDING_001/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["transaction_id"], "TXN_PENDING_001")
        self.assertEqual(data["status"], "PENDING")
        self.assertEqual(data["customer_debit_status"], "CONFIRMED")
        self.assertEqual(data["merchant_confirmation_status"], "PENDING")
        self.assertIn("timeline", data)

    def test_api_get_transaction_status_not_found(self):
        """Test GET /api/v1/transactions/{transaction_id}/status with invalid ID."""
        resp = self.client.get("/api/v1/transactions/NON_EXISTENT_TXN_999/status")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("We couldn't find a transaction", resp.json()["detail"])

    def test_process_and_track_new_transaction(self):
        """Execute a new transaction, retrieve it by ID, and verify status lifecycle."""
        payload = {
            "amount": 14500.0,
            "currency": "INR",
            "payment_method": "UPI",
            "bank": "HDFC",
            "merchant_category": "ECOMMERCE",
            "device_type": "MOBILE",
            "network_type": "4G",
            "simulate_forced_failure": False,
        }
        proc_resp = self.client.post("/api/v1/payment/process", json=payload)
        self.assertEqual(proc_resp.status_code, 200)
        proc_data = proc_resp.json()
        txn_id = proc_data["transaction_id"]

        # Look up status
        status_resp = self.client.get(f"/api/v1/transactions/{txn_id}/status")
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertEqual(status_data["transaction_id"], txn_id)
        self.assertEqual(status_data["amount"], 14500.0)
        self.assertEqual(status_data["status"], proc_data["status"])


if __name__ == "__main__":
    unittest.main()
