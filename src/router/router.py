"""
Smart Routing Orchestrator Engine for PayRoute AI.
Integrates Candidate Filtering, Phase-3 ML Risk Inference, Multi-Criteria Scoring,
3-State Circuit Breakers, Dynamic Traffic Simulation, and Intelligent Decision Policies.
"""

import json
import os
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import yaml

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.decision_engine.event_logger import EventLogger
from src.decision_engine.policy_engine import DecisionAction, DecisionPolicyEngine, DecisionResult
from src.decision_engine.traffic_simulator import (
    DemoScenario,
    LoadLevel,
    RouteStatus,
    TrafficSimulator,
)
from src.ml.predictor import PaymentPredictor
from src.router.candidate_filter import filter_candidate_routes
from src.router.circuit_breaker import CircuitState, RouteHealthTracker
from src.router.scorer import RouteScorer
from src.utils.logger import get_logger

logger = get_logger("SmartRouter")

DEFAULT_ROUTES_CONFIG = PROJECT_ROOT / "config" / "routes_config.yaml"


class SmartRouter:
    """
    Intelligent Payment Gateway Router using Machine Learning, Dynamic Health Telemetry,
    3-State Circuit Breakers, Real-time Traffic Simulation, and Decision Policies.
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        models_dir: Optional[Union[str, Path]] = None,
        random_seed: int = 42,
    ) -> None:
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)
        self.np_rng = np.random.RandomState(random_seed)

        # 1. Load Configurations
        self.config = self._load_routes_config(config_path)
        self.routes: List[Dict[str, Any]] = self.config.get("routes", [])

        # 2. Routing Parameters
        routing_cfg = self.config.get("routing", {})
        self.weights = routing_cfg.get(
            "weights",
            {"success": 0.60, "latency": 0.20, "cost": 0.10, "health": 0.10},
        )
        self.exploration_prob = routing_cfg.get("exploration_probability", 0.05)

        # 3. Circuit Breaker Parameters
        cb_cfg = self.config.get("circuit_breaker", {})
        self.cb_threshold = cb_cfg.get("failure_rate_threshold", 0.40)
        self.cb_min_txns = cb_cfg.get("minimum_transactions", 20)
        self.cb_timeout = cb_cfg.get("recovery_timeout_seconds", 30.0)
        self.half_open_prob = cb_cfg.get("half_open_test_probability", 0.05)

        # 4. Route Health Trackers
        window_size = self.config.get("health", {}).get("rolling_window_size", 100)
        self.health_trackers: Dict[str, RouteHealthTracker] = {}
        for r in self.routes:
            r_id = r["route_id"]
            self.health_trackers[r_id] = RouteHealthTracker(
                route_id=r_id,
                failure_rate_threshold=self.cb_threshold,
                minimum_transactions=self.cb_min_txns,
                recovery_timeout_seconds=self.cb_timeout,
                rolling_window_size=window_size,
                baseline_success_rate=r.get("baseline_success_rate", 0.95),
                baseline_latency_ms=r.get("expected_latency_ms", 150),
            )

        # 5. Core ML Predictor and Scorer
        self.predictor = PaymentPredictor(models_dir=models_dir)
        self.scorer = RouteScorer(weights=self.weights)

        # 6. Traffic Simulator, Event Logger, and Decision Policy Engine
        self.traffic_simulator = TrafficSimulator(
            routes=self.routes,
            config=self.config,
            random_seed=random_seed,
        )
        self.event_logger = EventLogger(maxlen=60)
        self.policy_engine = DecisionPolicyEngine(config=self.config)

        # 7. Session In-Memory Telemetry Stats
        self.session_stats = {
            "total_payments": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "interventions": 0,
            "circuit_breaker_trips": 0,
            "wait_recommendations": 0,
            "method_recommendations": 0,
            "latencies": [],
        }

        logger.info(
            f"SmartRouter initialized with {len(self.routes)} routes. "
            f"Weights: {self.scorer.weights} | CB Threshold: {self.cb_threshold*100:.0f}% | Traffic Engine: Active"
        )

    def _load_routes_config(self, config_path: Optional[Union[str, Path]]) -> Dict[str, Any]:
        """Loads YAML route configuration."""
        target_path = Path(config_path) if config_path else DEFAULT_ROUTES_CONFIG
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        logger.warning(f"Routes config not found at {target_path}. Using fallback catalogue.")
        return {
            "routes": [
                {
                    "route_id": "ROUTE_HDFC_RAZORPAY",
                    "bank": "HDFC",
                    "gateway": "RAZORPAY_SIM",
                    "supported_payment_methods": ["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"],
                    "base_fee_pct": 1.50,
                    "expected_latency_ms": 130,
                    "baseline_success_rate": 0.95,
                    "active": True,
                },
                {
                    "route_id": "ROUTE_HDFC_CASHFREE",
                    "bank": "HDFC",
                    "gateway": "CASHFREE_SIM",
                    "supported_payment_methods": ["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"],
                    "base_fee_pct": 1.35,
                    "expected_latency_ms": 155,
                    "baseline_success_rate": 0.94,
                    "active": True,
                },
            ],
            "routing": {"weights": {"success": 0.60, "latency": 0.20, "cost": 0.10, "health": 0.10}},
        }

    def set_simulation_scenario(
        self,
        scenario: str,
        target_bank: Optional[str] = None,
        target_gateway: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sets active demo simulation scenario."""
        res = self.traffic_simulator.set_scenario(
            scenario=scenario,
            target_bank=target_bank,
            target_gateway=target_gateway,
        )
        self.event_logger.log_event(
            event_type="SCENARIO_CHANGED",
            title=f"Scenario: {res['scenario']}",
            description=res["description"],
            severity="INFO" if res["scenario"] == "NORMAL" else "WARNING",
        )
        return res

    def _evaluate_candidate_routes_batch(
        self,
        payment_request: Dict[str, Any],
        eligible_routes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Runs batch ML inference and traffic adjustments for candidate routes.
        """
        if not eligible_routes:
            return []

        base_ctx = {
            "amount": float(payment_request.get("amount", 1000.0)),
            "currency": str(payment_request.get("currency", "INR")),
            "payment_method": str(payment_request.get("payment_method", "UPI")),
            "bank": str(payment_request.get("bank", "HDFC")),
            "merchant_category": str(payment_request.get("merchant_category", "ECOMMERCE")),
            "hour": int(payment_request.get("hour", 14)),
            "day_of_week": int(payment_request.get("day_of_week", 2)),
            "device_type": str(payment_request.get("device_type", "MOBILE")),
            "network_type": str(payment_request.get("network_type", "4G")),
            "customer_age_days": int(payment_request.get("customer_age_days", 180)),
            "previous_transactions": int(payment_request.get("previous_transactions", 10)),
            "previous_failed_transactions": int(payment_request.get("previous_failed_transactions", 0)),
            "previous_attempts": int(payment_request.get("previous_attempts", 0)),
            "transaction_velocity": int(payment_request.get("transaction_velocity", 1)),
            "is_new_device": int(payment_request.get("is_new_device", 0)),
        }
        base_ctx.update(payment_request)

        candidate_contexts = []
        candidate_metadata = []

        for route in eligible_routes:
            r_id = route["route_id"]
            tracker = self.health_trackers[r_id]

            # Dynamic traffic & load telemetry
            load = self.traffic_simulator.get_route_load(r_id)
            load_level = self.traffic_simulator.get_load_level(load)
            eff_latency = self.traffic_simulator.compute_effective_latency(
                route_id=r_id,
                base_latency_ms=route.get("expected_latency_ms", 150),
            )
            route_status = self.traffic_simulator.evaluate_route_status(
                route_id=r_id,
                circuit_state=route.get("circuit_state", "CLOSED"),
                rolling_success_rate=tracker.rolling_success_rate,
                median_latency_ms=eff_latency,
            )

            # Ingest route-specific telemetry into context copy
            route_ctx = base_ctx.copy()
            route_ctx["bank"] = route["bank"]
            route_ctx["bank_latency_ms"] = int(eff_latency * 0.6)
            route_ctx["gateway_latency_ms"] = int(eff_latency * 0.4)
            route_ctx["bank_success_rate"] = tracker.rolling_success_rate
            route_ctx["gateway_success_rate"] = route.get("baseline_success_rate", 0.95)

            candidate_contexts.append(route_ctx)
            candidate_metadata.append({
                "route_id": r_id,
                "route_name": route.get("route_name", r_id),
                "gateway": route["gateway"],
                "bank": route["bank"],
                "expected_latency_ms": eff_latency,
                "base_fee_pct": route["base_fee_pct"],
                "rolling_health": tracker.rolling_success_rate,
                "circuit_state": route["circuit_state"],
                "current_load": round(load, 3),
                "load_level": load_level.value,
                "route_status": route_status.value,
                "_context": route_ctx,
            })

        # Single batch transform for all K candidate routes
        df_batch = pd.DataFrame(candidate_contexts)
        X_batch = self.predictor.preprocessor.transform(df_batch)
        p_fails_raw = self.predictor.calibrated_model.predict_proba(X_batch)[:, 1]

        evaluated_candidates = []
        for idx, meta in enumerate(candidate_metadata):
            r_id = meta["route_id"]
            p_fail_ml = float(p_fails_raw[idx])

            # Ingest load risk penalty
            load_penalty = self.traffic_simulator.compute_load_risk_penalty(r_id)
            p_fail = min(0.98, max(0.01, p_fail_ml + load_penalty))
            p_success = 1.0 - p_fail

            if p_fail < 0.20:
                risk_level = "LOW"
            elif p_fail < self.predictor.optimal_threshold:
                risk_level = "MEDIUM"
            else:
                risk_level = "HIGH"

            meta["failure_probability"] = round(p_fail, 4)
            meta["success_probability"] = round(p_success, 4)
            meta["risk_level"] = risk_level
            evaluated_candidates.append(meta)

        return evaluated_candidates

    def _evaluate_alternative_methods(self, payment_request: Dict[str, Any]) -> Dict[str, float]:
        """Evaluates expected success rates across other payment methods for comparison."""
        current_method = payment_request.get("payment_method", "UPI")
        all_methods = ["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]
        results: Dict[str, float] = {}

        for method in all_methods:
            req_copy = payment_request.copy()
            req_copy["payment_method"] = method
            eligible, _ = filter_candidate_routes(
                payment_request=req_copy,
                all_routes=self.routes,
                health_trackers=self.health_trackers,
                current_time=0.0,
                is_probe_eligible=False,
            )
            if eligible:
                cands = self._evaluate_candidate_routes_batch(req_copy, eligible)
                if cands:
                    best_cand = max(cands, key=lambda c: c["success_probability"])
                    results[method] = round(best_cand["success_probability"], 4)

        return results

    def analyze_payment(
        self,
        payment_request: Dict[str, Any],
        current_time: float = 0.0,
        enable_exploration: bool = False,
    ) -> Dict[str, Any]:
        """
        Unified Pre-Payment Real-Time Analysis Endpoint:
        1. Filters candidates based on bank and method.
        2. Ingests dynamic route loads and computes effective latencies.
        3. Evaluates ML failure risk and multi-objective scores.
        4. Evaluates Cross-Rail Alternative payment methods.
        5. Computes structured Decision Policy (PROCESS_NOW, SWITCH_ROUTE, WAIT_AND_RETRY, etc.).
        6. Generates SHAP feature attributions.

        Returns:
            Comprehensive analysis payload with risk, infrastructure, decision policy, and routes.
        """
        is_probe_eligible = enable_exploration and (self.rng.random() < self.half_open_prob)

        # 1. Filter candidates
        eligible_routes, excluded_routes = filter_candidate_routes(
            payment_request=payment_request,
            all_routes=self.routes,
            health_trackers=self.health_trackers,
            current_time=current_time,
            is_probe_eligible=is_probe_eligible,
        )

        # 2. Evaluate candidates batch
        evaluated_candidates = self._evaluate_candidate_routes_batch(payment_request, eligible_routes)

        # 3. Score & rank
        ranked_candidates = self.scorer.score_candidates(evaluated_candidates) if evaluated_candidates else []

        # 4. Evaluate Alternative Methods
        method_alternatives = self._evaluate_alternative_methods(payment_request)

        # 5. Run Decision Policy Engine
        decision_result: DecisionResult = self.policy_engine.evaluate_decision(
            payment_request=payment_request,
            ranked_candidates=ranked_candidates,
            excluded_candidates=excluded_routes,
            method_alternatives=method_alternatives,
        )

        # Top candidate ML diagnostic and explanation
        explanation = None
        failure_diagnosis = None
        if ranked_candidates:
            top_cand = ranked_candidates[0]
            explanation = self.predictor.explain(top_cand["_context"], top_k=4)
            failure_diagnosis = self.predictor.predict_failure_reason(top_cand["_context"])

        # Clean private context fields from candidate output
        cleaned_candidates = []
        for c in ranked_candidates:
            c_out = {k: v for k, v in c.items() if not k.startswith("_")}
            cleaned_candidates.append(c_out)

        # Determine aggregate infrastructure status
        traffic_level = "LOW"
        if ranked_candidates:
            max_load = max(c.get("current_load", 0.0) for c in ranked_candidates)
            traffic_level = self.traffic_simulator.get_load_level(max_load).value

        # Event logging for meaningful interventions
        if decision_result.action == DecisionAction.SWITCH_ROUTE:
            self.event_logger.log_event(
                event_type="ROUTE_SWITCHED",
                route_id=decision_result.recommended_route,
                title=f"Switched: {decision_result.original_route} ➔ {decision_result.recommended_route}",
                description=decision_result.message,
                severity="WARNING",
            )
        elif decision_result.action == DecisionAction.WAIT_AND_RETRY:
            self.event_logger.log_event(
                event_type="TRAFFIC_SURGE",
                route_id=decision_result.recommended_route,
                title="Congestion Detected",
                description="All candidate routes at peak capacity; retry countdown suggested.",
                severity="CRITICAL",
            )

        return {
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "risk": {
                "failure_probability": ranked_candidates[0]["failure_probability"] if ranked_candidates else 1.0,
                "success_probability": ranked_candidates[0]["success_probability"] if ranked_candidates else 0.0,
                "risk_level": ranked_candidates[0]["risk_level"] if ranked_candidates else "HIGH",
                "predicted_reason": failure_diagnosis.get("predicted_reason") if failure_diagnosis else "SYSTEM_OUTAGE",
                "decision_threshold": self.predictor.optimal_threshold,
            },
            "infrastructure": {
                "traffic_level": traffic_level,
                "active_scenario": self.traffic_simulator.active_scenario.value,
                "scenario_description": self.traffic_simulator.get_scenario_description(),
                "bank": payment_request.get("bank", "HDFC"),
                "payment_method": payment_request.get("payment_method", "UPI"),
            },
            "decision": decision_result.to_dict(),
            "method_alternatives": method_alternatives,
            "routes": cleaned_candidates,
            "excluded_routes": [
                {"route_id": ex["route_id"], "reason": ex["reason"]}
                for ex in excluded_routes
            ],
            "explanation": explanation,
        }

    def process_payment(
        self,
        payment_request: Dict[str, Any],
        preferred_route: Optional[str] = None,
        simulate_forced_failure: bool = False,
        current_time: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Executes payment settlement through selected route, updates circuit breakers & event log.
        """
        # Run pre-analysis to get candidate scores and decision
        analysis = self.analyze_payment(payment_request, current_time=current_time)
        decision = analysis["decision"]

        # Determine target route to execute
        target_route_id = preferred_route or decision.get("recommended_route")
        if not target_route_id or decision.get("action") == DecisionAction.NO_ROUTE_AVAILABLE.value:
            return {
                "transaction_id": analysis["transaction_id"],
                "status": "FAILED",
                "payment_status": 1,
                "failure_reason": "NO_ROUTE_AVAILABLE",
                "route_id": None,
                "latency_ms": 0,
                "message": "Payment failed: No available or operational routes.",
                "analysis": analysis,
            }

        # Find target candidate details
        target_cand = next((c for c in analysis["routes"] if c["route_id"] == target_route_id), None)
        if target_cand is None and analysis["routes"]:
            target_cand = analysis["routes"][0]
            target_route_id = target_cand["route_id"]

        # Compute execution outcome probabilistically
        p_fail = target_cand["failure_probability"] if target_cand else 0.50
        eff_lat = target_cand["expected_latency_ms"] if target_cand else 200

        # Inject forced failure if requested or in severe gateway outage scenario
        if simulate_forced_failure or (
            self.traffic_simulator.active_scenario == DemoScenario.GATEWAY_OUTAGE
            and self.traffic_simulator.scenario_target_gateway in target_route_id
        ):
            is_failure = True
            failure_reason = "GATEWAY_TIMEOUT"
        else:
            is_failure = bool(self.rng.random() < p_fail)
            failure_reason = analysis["risk"]["predicted_reason"] if is_failure else None

        payment_status_int = 1 if is_failure else 0

        # Record outcome in Route Health Tracker & Circuit Breaker
        self.record_outcome(
            route_id=target_route_id,
            payment_status=payment_status_int,
            latency_ms=eff_lat,
            current_time=current_time,
        )

        # Update Session In-Memory Telemetry
        self.session_stats["total_payments"] += 1
        if is_failure:
            self.session_stats["failed_payments"] += 1
        else:
            self.session_stats["successful_payments"] += 1

        self.session_stats["latencies"].append(eff_lat)
        if decision.get("action") == DecisionAction.SWITCH_ROUTE.value:
            self.session_stats["interventions"] += 1
        elif decision.get("action") == DecisionAction.WAIT_AND_RETRY.value:
            self.session_stats["wait_recommendations"] += 1
        elif decision.get("action") == DecisionAction.USE_ALTERNATIVE_PAYMENT_METHOD.value:
            self.session_stats["method_recommendations"] += 1

        # Check for circuit breaker trip
        tracker = self.health_trackers.get(target_route_id)
        if tracker and tracker.state == CircuitState.OPEN:
            self.session_stats["circuit_breaker_trips"] += 1
            self.event_logger.log_event(
                event_type="CIRCUIT_TRIPPED",
                route_id=target_route_id,
                title=f"Circuit Breaker Tripped: {target_route_id}",
                description=f"Route exceeded failure threshold ({tracker.rolling_failure_rate*100:.1f}%). Traffic diverted to fallbacks.",
                severity="CRITICAL",
            )

        return {
            "transaction_id": analysis["transaction_id"],
            "status": "FAILED" if is_failure else "SUCCESS",
            "payment_status": payment_status_int,
            "failure_reason": failure_reason,
            "route_id": target_route_id,
            "route_name": target_cand.get("route_name", target_route_id) if target_cand else target_route_id,
            "latency_ms": eff_lat,
            "amount": payment_request.get("amount", 1000.0),
            "bank": payment_request.get("bank", "HDFC"),
            "payment_method": payment_request.get("payment_method", "UPI"),
            "decision_action": decision.get("action"),
            "circuit_state": tracker.state.value if tracker else "CLOSED",
            "analysis": analysis,
        }

    def route_payment(
        self,
        payment_request: Dict[str, Any],
        current_time: float = 0.0,
        enable_exploration: bool = True,
        include_explanation: bool = True,
    ) -> Dict[str, Any]:
        """
        Backwards-compatible wrapper matching original SmartRouter signature.
        """
        analysis = self.analyze_payment(
            payment_request=payment_request,
            current_time=current_time,
            enable_exploration=enable_exploration,
        )

        if not analysis["routes"]:
            return {
                "status": "NO_ROUTE_AVAILABLE",
                "primary_route": None,
                "fallback_route": None,
                "routing_strategy": "NO_ROUTE_AVAILABLE",
                "recommendation_summary": "All candidate routes are either down (OPEN circuit) or incompatible.",
                "candidates": [],
                "excluded_candidates": analysis["excluded_routes"],
            }

        top_cand = analysis["routes"][0]
        fallback_cand = analysis["routes"][1] if len(analysis["routes"]) > 1 else None

        has_open_candidates = any("CIRCUIT_BREAKER_OPEN" in ex.get("reason", "") for ex in analysis["excluded_routes"])
        if len(analysis["routes"]) == 1:
            strategy = "SINGLE_ROUTE"
        elif has_open_candidates:
            strategy = "CIRCUIT_BREAKER_OVERRIDE"
        elif enable_exploration and (self.rng.random() < self.exploration_prob):
            strategy = "EXPLORATION"
        else:
            strategy = "AI_OPTIMAL"

        return {
            "status": "ROUTE_SELECTED",
            "primary_route": top_cand["route_id"],
            "fallback_route": fallback_cand["route_id"] if fallback_cand else None,
            "routing_strategy": strategy,
            "decision_action": analysis["decision"]["action"],
            "primary_predicted_success_prob": top_cand["success_probability"],
            "primary_predicted_failure_prob": top_cand["failure_probability"],
            "primary_utility_score": top_cand.get("utility_score", 0.85),
            "primary_circuit_state": top_cand.get("circuit_state", "CLOSED"),
            "explanation": analysis["explanation"],
            "candidates": analysis["routes"],
            "excluded_candidates": analysis["excluded_routes"],
        }


    def record_outcome(
        self,
        route_id: str,
        payment_status: int,
        latency_ms: int,
        current_time: float = 0.0,
        is_probe: bool = False,
    ) -> None:
        """Updates health tracker and circuit breaker state upon transaction result."""
        tracker = self.health_trackers.get(route_id)
        if tracker is not None:
            tracker.record_outcome(
                payment_status=payment_status,
                latency_ms=latency_ms,
                current_time=current_time,
                is_probe=is_probe,
            )

    def get_system_health_snapshot(self) -> List[Dict[str, Any]]:
        """Returns real-time health, load, and circuit breaker status for all configured routes."""
        snapshot = []
        for r_id, tracker in self.health_trackers.items():
            t_dict = tracker.to_dict()
            load = self.traffic_simulator.get_route_load(r_id)
            load_level = self.traffic_simulator.get_load_level(load)
            status = self.traffic_simulator.evaluate_route_status(
                route_id=r_id,
                circuit_state=tracker.state.value,
                rolling_success_rate=tracker.rolling_success_rate,
                median_latency_ms=tracker.median_latency_ms,
            )
            t_dict["current_load"] = round(load, 3)
            t_dict["load_level"] = load_level.value
            t_dict["route_status"] = status.value
            snapshot.append(t_dict)
        return snapshot

    def get_recent_events(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns stream of recent routing and infrastructure events."""
        return self.event_logger.get_recent_events(limit=limit)

    def get_session_kpis(self) -> Dict[str, Any]:
        """Returns aggregate session KPIs and business impact metrics."""
        total = self.session_stats["total_payments"]
        succ = self.session_stats["successful_payments"]
        sr = (succ / total * 100.0) if total > 0 else 100.0
        avg_lat = (sum(self.session_stats["latencies"]) / len(self.session_stats["latencies"])) if self.session_stats["latencies"] else 150.0
        return {
            "total_payments": total,
            "successful_payments": succ,
            "failed_payments": self.session_stats["failed_payments"],
            "success_rate_pct": round(sr, 2),
            "interventions": self.session_stats["interventions"],
            "circuit_breaker_trips": self.session_stats["circuit_breaker_trips"],
            "wait_recommendations": self.session_stats["wait_recommendations"],
            "method_recommendations": self.session_stats["method_recommendations"],
            "average_latency_ms": round(avg_lat, 1),
        }
