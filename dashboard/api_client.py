"""
Centralized HTTP API Client for PayRoute AI Streamlit Dashboard.
Connects to FastAPI backend (default: http://localhost:8000) with robust error handling.
"""

import os
from typing import Any, Dict, List, Optional
import requests

from src.utils.logger import get_logger

logger = get_logger("DashboardAPIClient")

DEFAULT_API_URL = os.environ.get("PAYROUTE_API_URL", "http://localhost:8000")


class PayRouteAPIClient:
    """
    Client for interacting with the PayRoute AI FastAPI backend.
    Handles network timeouts, error codes, and formats user-friendly error messages.
    """

    def __init__(self, base_url: str = DEFAULT_API_URL, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """Checks if the FastAPI backend is online and operational."""
        try:
            res = requests.get(f"{self.base_url}/api/v1/health", timeout=self.timeout)
            if res.status_code == 200:
                return {"online": True, "details": res.json()}
            return {"online": False, "error": f"HTTP {res.status_code}"}
        except requests.exceptions.RequestException as e:
            logger.warning(f"Backend offline at {self.base_url}: {str(e)}")
            return {"online": False, "error": str(e)}

    def predict_failure(self, payment_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls POST /api/v1/predict/failure.

        Args:
            payment_context: Payment transaction dictionary.

        Returns:
            Dictionary with prediction results or error payload.
        """
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/predict/failure",
                json=payment_context,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def recommend_route(self, payment_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls POST /api/v1/route/recommend.

        Args:
            payment_context: Payment transaction dictionary.

        Returns:
            Dictionary with routing recommendation or error payload.
        """
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/route/recommend",
                json=payment_context,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def execute_transaction(
        self,
        payment_request: Dict[str, Any],
        preferred_route: Optional[str] = None,
        simulate_outage: bool = False,
    ) -> Dict[str, Any]:
        """
        Calls POST /api/v1/transactions/execute.
        """
        payload = {
            "payment_request": payment_request,
            "preferred_route": preferred_route,
            "simulate_outage": simulate_outage,
        }
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/transactions/execute",
                json=payload,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_gateway_health(self) -> Dict[str, Any]:
        """Calls GET /api/v1/gateways/health."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/gateways/health",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Calls GET /api/v1/analytics/summary."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/analytics/summary",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Calls GET /api/v1/transactions/{transaction_id}."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/transactions/{transaction_id}",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_explanation(self, transaction_id: str) -> Dict[str, Any]:
        """Calls GET /api/v1/explain/{transaction_id}."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/explain/{transaction_id}",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        organization: Optional[str] = "Independent Merchant",
        role: str = "MERCHANT_ADMIN",
    ) -> Dict[str, Any]:
        """
        Calls POST /api/v1/auth/register.
        """
        payload = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "organization": organization,
            "role": role,
        }
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/auth/register",
                json=payload,
                timeout=self.timeout,
            )
            if res.status_code == 201:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Calls POST /api/v1/auth/login.
        """
        payload = {"email": email, "password": password}
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json=payload,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def analyze_payment(self, payment_request: Dict[str, Any]) -> Dict[str, Any]:
        """Calls POST /api/v1/payment/analyze."""
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/payment/analyze",
                json=payment_request,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def process_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Calls POST /api/v1/payment/process."""
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/payment/process",
                json=payload,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def set_simulation_scenario(
        self,
        scenario: str,
        target_bank: Optional[str] = "SBI",
        target_gateway: Optional[str] = "RAZORPAY_SIM",
    ) -> Dict[str, Any]:
        """Calls POST /api/v1/simulation/scenario."""
        payload = {
            "scenario": scenario,
            "target_bank": target_bank,
            "target_gateway": target_gateway,
        }
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/simulation/scenario",
                json=payload,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_system_status(self) -> Dict[str, Any]:
        """Calls GET /api/v1/system/status."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/system/status",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_recent_events(self, limit: int = 15) -> Dict[str, Any]:
        """Calls GET /api/v1/events/recent."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/events/recent",
                params={"limit": limit},
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Calls GET /api/v1/transactions/{transaction_id}/status."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/transactions/{transaction_id.strip()}/status",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            detail = res.json().get("detail") if res.headers.get("content-type") == "application/json" else res.text
            return {"success": False, "error": detail or "Transaction not found."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def get_all_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calls GET /api/v1/transactions with filters."""
        params = {"limit": limit, "offset": offset}
        if status_filter and status_filter != "ALL":
            params["status_filter"] = status_filter
        if search_query:
            params["search_query"] = search_query
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/transactions",
                params=params,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def list_gateway_credentials(self) -> Dict[str, Any]:
        """Calls GET /api/v1/gateways/credentials."""
        try:
            res = requests.get(
                f"{self.base_url}/api/v1/gateways/credentials",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def save_gateway_credentials(self, provider_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calls POST /api/v1/gateways/{provider_id}/credentials."""
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/gateways/{provider_id.upper()}/credentials",
                json=data,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}

    def test_gateway_connection(self, provider_id: str) -> Dict[str, Any]:
        """Calls POST /api/v1/gateways/{provider_id}/test-connection."""
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/gateways/{provider_id.upper()}/test-connection",
                timeout=self.timeout,
            )
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.json().get("detail", res.text)}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to backend: {str(e)}"}




