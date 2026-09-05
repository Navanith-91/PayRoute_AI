"""
Central Gateway Integration Manager.
Coordinates platform adapters (Razorpay, PhonePe, Google Pay), credential storage, and live connection health.
"""

from typing import Any, Dict, List, Optional

from database.db_manager import DatabaseManager
from src.gateways.gpay_adapter import GPayAdapter
from src.gateways.phonepe_adapter import PhonePeAdapter
from src.gateways.razorpay_adapter import RazorpayAdapter
from src.utils.logger import get_logger

logger = get_logger("GatewayManager")


class GatewayManager:
    """
    Central Manager managing live gateway platform adapters and credential verification.
    """

    ADAPTERS = {
        "RAZORPAY": RazorpayAdapter,
        "PHONEPE": PhonePeAdapter,
        "GPAY": GPayAdapter,
    }

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager()

    def get_credentials(self, provider_id: str, mask_secrets: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieves credentials for a provider with optional secret masking.
        """
        creds = self.db.get_gateway_credentials(provider_id.upper())
        if not creds:
            return None

        result = dict(creds)
        if mask_secrets:
            if result.get("api_key_secret"):
                sec = result["api_key_secret"]
                result["api_key_secret"] = f"••••••••{sec[-4:]}" if len(sec) > 4 else "••••••••"
            if result.get("salt_key"):
                sk = result["salt_key"]
                result["salt_key"] = f"••••••••{sk[-4:]}" if len(sk) > 4 else "••••••••"
            if result.get("webhook_secret"):
                ws = result["webhook_secret"]
                result["webhook_secret"] = f"••••••••{ws[-4:]}" if len(ws) > 4 else "••••••••"

        return result

    def list_all_credentials(self, mask_secrets: bool = True) -> List[Dict[str, Any]]:
        """
        Lists credentials for all providers.
        """
        providers = ["RAZORPAY", "PHONEPE", "GPAY"]
        results = []
        for p in providers:
            c = self.get_credentials(p, mask_secrets=mask_secrets)
            if c:
                results.append(c)
            else:
                results.append({
                    "provider_id": p,
                    "provider_name": f"{p} Gateway",
                    "environment": "SANDBOX",
                    "is_enabled": 0,
                    "test_status": "UNCONFIGURED",
                    "latency_ms": 0,
                })
        return results

    def save_credentials(self, provider_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves updated API credentials and runs pre-flight connectivity test.
        """
        p_id = provider_id.upper()
        # Preserve existing secrets if masked string was submitted
        existing = self.db.get_gateway_credentials(p_id)
        if existing:
            for k, v in existing.items():
                if k not in data or data[k] is None:
                    data[k] = v
            if (data.get("api_key_secret") or "").startswith("•••"):
                data["api_key_secret"] = existing.get("api_key_secret")
            if (data.get("salt_key") or "").startswith("•••"):
                data["salt_key"] = existing.get("salt_key")
            if (data.get("webhook_secret") or "").startswith("•••"):
                data["webhook_secret"] = existing.get("webhook_secret")

        # Execute connectivity test
        test_res = self.test_connection(p_id, data)
        data["test_status"] = test_res.get("status", "UNCONFIGURED")
        data["latency_ms"] = test_res.get("latency_ms", 0)
        data["last_tested_at"] = test_res.get("tested_at")

        self.db.save_gateway_credentials(p_id, data)
        logger.info(f"Saved gateway credentials for {p_id} (Status: {data['test_status']}, Latency: {data['latency_ms']}ms)")
        return test_res

    def test_connection(self, provider_id: str, credentials_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Tests API connection to the specified gateway provider.
        """
        p_id = provider_id.upper()
        adapter = self.ADAPTERS.get(p_id)
        if not adapter:
            return {
                "success": False,
                "status": "UNSUPPORTED_PROVIDER",
                "message": f"Provider '{provider_id}' is not supported.",
                "latency_ms": 0,
            }

        creds = credentials_override or self.db.get_gateway_credentials(p_id)
        if not creds:
            return {
                "success": False,
                "status": "UNCONFIGURED",
                "message": f"No credentials configured for {p_id}.",
                "latency_ms": 0,
            }

        result = adapter.test_connection(creds)
        # Update test status in DB if testing persisted creds
        if not credentials_override:
            creds_copy = dict(creds)
            creds_copy["test_status"] = result.get("status", "UNCONFIGURED")
            creds_copy["latency_ms"] = result.get("latency_ms", 0)
            self.db.save_gateway_credentials(p_id, creds_copy)

        return result
