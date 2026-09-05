"""
Unit and Integration Tests for User Registration & Authentication System.
Verifies password hashing, SQLite user persistence, FastAPI auth endpoints, and client methods.
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
from dashboard.api_client import PayRouteAPIClient
from src.utils.auth import hash_password, verify_password


class TestAuthSecurity(unittest.TestCase):
    """Verifies cryptographic password hashing and verification."""

    def test_password_hashing_and_verification(self):
        pwd = "SecurePassword@123"
        hashed = hash_password(pwd)
        self.assertIn("$", hashed)
        salt, h = hashed.split("$", 1)
        self.assertEqual(len(salt), 32)
        self.assertTrue(len(h) > 0)

        # Verification succeeds with matching password
        self.assertTrue(verify_password(pwd, hashed))

        # Verification fails with wrong password
        self.assertFalse(verify_password("WrongPassword", hashed))

        # Verification fails with malformed hash
        self.assertFalse(verify_password(pwd, "invalid_hash_string"))
        self.assertFalse(verify_password(pwd, ""))


class TestDatabaseUserManagement(unittest.TestCase):
    """Verifies user CRUD and authentication in SQLite DatabaseManager."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_auth.db")
        self.db = DatabaseManager(db_path=self.db_path)
        self.db.initialize_schema()
        self.db.seed_initial_entities()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_seeded_demo_users_exist(self):
        admin = self.db.get_user_by_email("admin@payroute.ai")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "SUPER_ADMIN")

        # Verify seeded password authentication
        auth_admin = self.db.authenticate_user("admin@payroute.ai", "Admin@12345")
        self.assertIsNotNone(auth_admin)
        self.assertEqual(auth_admin["email"], "admin@payroute.ai")

        merch = self.db.get_user_by_email("merchant@bharatmart.com")
        self.assertIsNotNone(merch)
        self.assertEqual(merch["role"], "MERCHANT_ADMIN")

    def test_create_and_authenticate_new_user(self):
        user = self.db.create_user(
            email="rohan@techcorp.in",
            password="RohanPassword@999",
            full_name="Rohan Sharma",
            organization="TechCorp Retail",
            role="MERCHANT_ADMIN",
        )
        self.assertEqual(user["email"], "rohan@techcorp.in")
        self.assertEqual(user["full_name"], "Rohan Sharma")
        self.assertTrue(user["user_id"].startswith("usr_"))

        # Authenticate with valid password
        auth_res = self.db.authenticate_user("rohan@techcorp.in", "RohanPassword@999")
        self.assertIsNotNone(auth_res)
        self.assertEqual(auth_res["user_id"], user["user_id"])

        # Authenticate with wrong password
        bad_auth = self.db.authenticate_user("rohan@techcorp.in", "WrongPwd123")
        self.assertIsNone(bad_auth)

    def test_duplicate_email_rejection(self):
        self.db.create_user(
            email="duplicate@example.com",
            password="Password123",
            full_name="User One",
        )
        with self.assertRaises(ValueError):
            self.db.create_user(
                email="duplicate@example.com",
                password="Password456",
                full_name="User Two",
            )

    def test_invalid_registration_fields(self):
        # Invalid email
        with self.assertRaises(ValueError):
            self.db.create_user("notanemail", "Password123", "Name")

        # Short password
        with self.assertRaises(ValueError):
            self.db.create_user("valid@email.com", "123", "Name")

        # Empty name
        with self.assertRaises(ValueError):
            self.db.create_user("valid2@email.com", "Password123", "   ")


class TestAuthAPIEndpoints(unittest.TestCase):
    """Verifies FastAPI auth endpoints via TestClient."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_api_auth.db")
        self.db = DatabaseManager(db_path=self.db_path)
        self.db.initialize_schema()
        self.db.seed_initial_entities()

        # Patch dependency provider get_db
        from api.dependencies import get_db
        self.app = create_app()
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_endpoint_success(self):
        payload = {
            "email": "priya.nair@swiggy.in",
            "password": "SecurePassword@123",
            "full_name": "Priya Nair",
            "organization": "Swiggy Payments",
            "role": "PAYMENT_OPS_LEAD",
        }
        res = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["email"], "priya.nair@swiggy.in")
        self.assertEqual(data["full_name"], "Priya Nair")
        self.assertTrue(data["user_id"].startswith("usr_"))

    def test_register_duplicate_email_error(self):
        payload = {
            "email": "admin@payroute.ai",  # Already seeded
            "password": "NewPassword@123",
            "full_name": "Admin Clone",
        }
        res = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("already exists", res.json()["detail"])

    def test_login_endpoint_success_and_failure(self):
        # Valid login
        valid_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@payroute.ai", "password": "Admin@12345"},
        )
        self.assertEqual(valid_res.status_code, 200)
        data = valid_res.json()
        self.assertTrue(data["access_token"].startswith("tok_"))
        self.assertEqual(data["user"]["email"], "admin@payroute.ai")

        # Invalid login
        bad_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@payroute.ai", "password": "WrongPassword"},
        )
        self.assertEqual(bad_res.status_code, 401)


class TestDashboardClientAuth(unittest.TestCase):
    """Verifies dashboard API client authentication methods."""

    @patch("requests.post")
    def test_dashboard_client_register_and_login(self, mock_post):
        client = PayRouteAPIClient(base_url="http://localhost:8000")

        # Mock register
        mock_resp_reg = MagicMock()
        mock_resp_reg.status_code = 201
        mock_resp_reg.json.return_value = {
            "user_id": "usr_123",
            "email": "test@merchant.com",
            "full_name": "Test User",
            "role": "MERCHANT_ADMIN",
        }
        mock_post.return_value = mock_resp_reg

        reg_res = client.register_user(
            email="test@merchant.com",
            password="Password@123",
            full_name="Test User",
        )
        self.assertTrue(reg_res["success"])
        self.assertEqual(reg_res["data"]["email"], "test@merchant.com")

        # Mock login
        mock_resp_login = MagicMock()
        mock_resp_login.status_code = 200
        mock_resp_login.json.return_value = {
            "access_token": "tok_xyz",
            "user": {"email": "test@merchant.com", "full_name": "Test User"},
        }
        mock_post.return_value = mock_resp_login

        login_res = client.login_user("test@merchant.com", "Password@123")
        self.assertTrue(login_res["success"])
        self.assertEqual(login_res["data"]["access_token"], "tok_xyz")


if __name__ == "__main__":
    unittest.main()
