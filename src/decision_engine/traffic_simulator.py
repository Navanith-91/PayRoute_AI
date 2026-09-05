"""
Traffic Simulator & Route State Evaluation Engine for PayRoute AI.
Simulates real-time infrastructure load, latency surges, and route health classifications.
"""

from enum import Enum
import random
from typing import Any, Dict, List, Optional
import numpy as np

from src.utils.logger import get_logger

logger = get_logger("TrafficSimulator")


class RouteStatus(str, Enum):
    """Human-readable route operational condition."""
    HEALTHY = "HEALTHY"          # Good success rate + low/moderate load
    BUSY = "BUSY"                # Elevated traffic load, performance still acceptable
    DEGRADED = "DEGRADED"        # Increasing failure rate or latency surge
    CRITICAL = "CRITICAL"        # Severe failure rate or extreme traffic congestion
    UNAVAILABLE = "UNAVAILABLE"  # Circuit breaker tripped OPEN or gateway disabled


class LoadLevel(str, Enum):
    """Categorized traffic load classification."""
    LOW = "LOW"            # 0.00 - 0.35
    MODERATE = "MODERATE"  # 0.35 - 0.70
    HIGH = "HIGH"          # 0.70 - 0.85
    CRITICAL = "CRITICAL"  # 0.85 - 1.00


class DemoScenario(str, Enum):
    """Preset demonstration scenarios for live testing."""
    NORMAL = "NORMAL"                      # All infrastructure healthy and operational
    HIGH_TRAFFIC = "HIGH_TRAFFIC"          # Primary routes congested, triggering smart alternative switches
    BANK_DEGRADATION = "BANK_DEGRADATION"  # Target bank experiencing core server delays/failures
    GATEWAY_OUTAGE = "GATEWAY_OUTAGE"      # Target gateway fails, tripping circuit breakers
    UPI_CONGESTION = "UPI_CONGESTION"      # UPI rails congested, recommending Card/NetBanking alternatives
    FLASH_SALE = "FLASH_SALE"              # Massive traffic burst across all routes requiring dynamic balancing


class TrafficSimulator:
    """
    Manages dynamic route loads and computes traffic-induced performance degradation.
    """

    def __init__(
        self,
        routes: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
        random_seed: int = 42,
    ) -> None:
        self.routes = routes
        self.config = config or {}
        self.rng = random.Random(random_seed)
        self.np_rng = np.random.RandomState(random_seed)

        traffic_cfg = self.config.get("traffic", {})
        self.load_thresholds = traffic_cfg.get(
            "load_thresholds",
            {"low": 0.35, "moderate": 0.70, "high": 0.85, "critical": 1.00},
        )
        self.latency_multiplier = traffic_cfg.get("latency_multiplier", 1.50)
        self.failure_penalty = traffic_cfg.get("failure_rate_load_penalty", 0.15)

        # Active Scenario State
        self.active_scenario: DemoScenario = DemoScenario.NORMAL
        self.scenario_target_bank: str = "SBI"
        self.scenario_target_gateway: str = "RAZORPAY_SIM"

        # Route load mapping: route_id -> float [0.0, 1.0]
        self.route_loads: Dict[str, float] = {}
        self._initialize_loads()

    def _initialize_loads(self) -> None:
        """Sets initial baseline loads for all routes."""
        for r in self.routes:
            r_id = r["route_id"]
            # Base load between 0.15 and 0.35 (Low-to-moderate)
            self.route_loads[r_id] = round(self.rng.uniform(0.18, 0.34), 3)

    def set_scenario(
        self,
        scenario: str,
        target_bank: Optional[str] = None,
        target_gateway: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Applies a simulated demo scenario and adjusts route loads and states accordingly.

        Args:
            scenario: Name of scenario (NORMAL, HIGH_TRAFFIC, BANK_DEGRADATION, GATEWAY_OUTAGE, UPI_CONGESTION, FLASH_SALE).
            target_bank: Optional bank identifier targeted by scenario (e.g. SBI, HDFC).
            target_gateway: Optional gateway identifier targeted by scenario (e.g. RAZORPAY_SIM).

        Returns:
            Dictionary describing the applied scenario metadata.
        """
        try:
            self.active_scenario = DemoScenario(scenario.upper())
        except ValueError:
            logger.warning(f"Unknown scenario '{scenario}'. Falling back to NORMAL.")
            self.active_scenario = DemoScenario.NORMAL

        if target_bank:
            self.scenario_target_bank = target_bank.upper()
        if target_gateway:
            self.scenario_target_gateway = target_gateway.upper()

        # Update loads based on scenario
        for r in self.routes:
            r_id = r["route_id"]
            bank = r.get("bank", "")
            gateway = r.get("gateway", "")
            methods = r.get("supported_payment_methods", [])

            if self.active_scenario == DemoScenario.NORMAL:
                self.route_loads[r_id] = round(self.rng.uniform(0.18, 0.35), 3)

            elif self.active_scenario == DemoScenario.HIGH_TRAFFIC:
                # Primary Razorpay routes overloaded; Cashfree/PayU remain moderate
                if "RAZORPAY" in r_id:
                    self.route_loads[r_id] = round(self.rng.uniform(0.88, 0.95), 3)
                else:
                    self.route_loads[r_id] = round(self.rng.uniform(0.35, 0.50), 3)

            elif self.active_scenario == DemoScenario.BANK_DEGRADATION:
                if bank == self.scenario_target_bank:
                    self.route_loads[r_id] = round(self.rng.uniform(0.86, 0.96), 3)
                else:
                    self.route_loads[r_id] = round(self.rng.uniform(0.20, 0.40), 3)

            elif self.active_scenario == DemoScenario.GATEWAY_OUTAGE:
                if gateway == self.scenario_target_gateway:
                    self.route_loads[r_id] = 1.00  # Gateway down
                else:
                    self.route_loads[r_id] = round(self.rng.uniform(0.30, 0.55), 3)

            elif self.active_scenario == DemoScenario.UPI_CONGESTION:
                if "UPI" in methods and ("DIRECT" in r_id or "RAZORPAY" in r_id):
                    self.route_loads[r_id] = round(self.rng.uniform(0.89, 0.97), 3)
                else:
                    self.route_loads[r_id] = round(self.rng.uniform(0.22, 0.42), 3)

            elif self.active_scenario == DemoScenario.FLASH_SALE:
                # High volume everywhere, but varying across providers
                self.route_loads[r_id] = round(self.rng.uniform(0.72, 0.93), 3)

        logger.info(f"Applied simulation scenario: {self.active_scenario.value}")
        return {
            "scenario": self.active_scenario.value,
            "target_bank": self.scenario_target_bank,
            "target_gateway": self.scenario_target_gateway,
            "description": self.get_scenario_description(),
        }

    def get_scenario_description(self) -> str:
        """Returns human-readable explanation of the current active demo scenario."""
        if self.active_scenario == DemoScenario.NORMAL:
            return "All payment infrastructure and gateways operating under healthy baseline traffic."
        elif self.active_scenario == DemoScenario.HIGH_TRAFFIC:
            return "Primary payment routes are experiencing peak volume; alternative routes remain healthy."
        elif self.active_scenario == DemoScenario.BANK_DEGRADATION:
            return f"Core banking servers at {self.scenario_target_bank} are experiencing elevated latency and timeouts."
        elif self.active_scenario == DemoScenario.GATEWAY_OUTAGE:
            return f"{self.scenario_target_gateway} is experiencing an infrastructure outage tripping circuit breakers."
        elif self.active_scenario == DemoScenario.UPI_CONGESTION:
            return "UPI infrastructure is congested nationwide; Card and Net Banking rails remain fast and reliable."
        elif self.active_scenario == DemoScenario.FLASH_SALE:
            return "Flash-sale traffic surge: PayRoute AI dynamically load-balances across all candidate providers."
        return "Standard operational mode."

    def get_route_load(self, route_id: str) -> float:
        """Returns current load factor [0.0, 1.0] for a specific route."""
        return self.route_loads.get(route_id, 0.25)

    def get_load_level(self, load: float) -> LoadLevel:
        """Maps numeric load to categorized LoadLevel enum."""
        if load <= self.load_thresholds.get("low", 0.35):
            return LoadLevel.LOW
        elif load <= self.load_thresholds.get("moderate", 0.70):
            return LoadLevel.MODERATE
        elif load <= self.load_thresholds.get("high", 0.85):
            return LoadLevel.HIGH
        return LoadLevel.CRITICAL

    def compute_effective_latency(self, route_id: str, base_latency_ms: int) -> int:
        """
        Computes load-adjusted effective latency in milliseconds:
        EffectiveLatency = BaseLatency * (1.0 + 1.5 * Load) + Jitter
        """
        load = self.get_route_load(route_id)
        surge_factor = 1.0 + (self.latency_multiplier * load)
        jitter = self.rng.uniform(-10.0, 15.0)

        # Severe bank degradation multiplier
        if (
            self.active_scenario == DemoScenario.BANK_DEGRADATION
            and self.scenario_target_bank in route_id
        ):
            surge_factor *= 2.2

        effective = int(max(50, (base_latency_ms * surge_factor) + jitter))
        return effective

    def compute_load_risk_penalty(self, route_id: str) -> float:
        """
        Computes incremental failure probability risk penalty due to high load:
        LoadRiskPenalty = failure_penalty * (Load^2)
        """
        load = self.get_route_load(route_id)
        if load < 0.50:
            return 0.0
        # Quadratic risk acceleration above 50% load
        penalty = float(self.failure_penalty * (load ** 2))
        return round(penalty, 4)

    def evaluate_route_status(
        self,
        route_id: str,
        circuit_state: str,
        rolling_success_rate: float,
        median_latency_ms: float,
    ) -> RouteStatus:
        """
        Determines human-readable RouteStatus (HEALTHY, BUSY, DEGRADED, CRITICAL, UNAVAILABLE).
        Centralized threshold rules without hardcoding.
        """
        if str(circuit_state).upper() == "OPEN":
            return RouteStatus.UNAVAILABLE

        load = self.get_route_load(route_id)
        failure_rate = 1.0 - rolling_success_rate

        # 1. Critical condition
        if failure_rate >= 0.35 or load >= 0.92 or median_latency_ms >= 600:
            return RouteStatus.CRITICAL

        # 2. Degraded condition
        if failure_rate >= 0.18 or load >= 0.78 or median_latency_ms >= 380:
            return RouteStatus.DEGRADED

        # 3. Busy condition
        if load >= 0.65 or median_latency_ms >= 240:
            return RouteStatus.BUSY

        # 4. Healthy condition
        return RouteStatus.HEALTHY
