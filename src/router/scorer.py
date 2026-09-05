"""
Multi-Objective Route Scorer and Utility Optimization Engine.
"""

from typing import Any, Dict, List, Optional
import numpy as np

from src.utils.logger import get_logger

logger = get_logger("RouteScorer")

DEFAULT_WEIGHTS = {
    "success": 0.60,
    "latency": 0.20,
    "cost": 0.10,
    "health": 0.10,
}


class RouteScorer:
    """
    Calculates weighted utility scores for candidate payment routes and ranks them deterministically.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self.weights = weights if weights is not None else DEFAULT_WEIGHTS.copy()
        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def score_candidates(
        self,
        evaluated_candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Scores and ranks evaluated candidate routes based on ML failure risk, latency, fee, and health.

        Args:
            evaluated_candidates: List of candidate dictionaries with ML predictions attached.

        Returns:
            Ranked list of scored candidate dictionaries sorted by utility descending.
        """
        if not evaluated_candidates:
            return []

        if len(evaluated_candidates) == 1:
            cand = evaluated_candidates[0].copy()
            p_success = float(cand.get("success_probability", 1.0 - cand.get("failure_probability", 0.15)))
            health = float(cand.get("rolling_health", 0.95))
            score = (
                self.weights["success"] * p_success
                + self.weights["health"] * health
                - self.weights["latency"] * 0.0
                - self.weights["cost"] * 0.0
            )
            cand["normalized_latency"] = 0.0
            cand["normalized_cost"] = 0.0
            cand["utility_score"] = round(float(score), 4)
            return [cand]

        # Extract vectors for normalization
        latencies = np.array([float(c.get("expected_latency_ms", 150)) for c in evaluated_candidates])
        costs = np.array([float(c.get("base_fee_pct", 1.5)) for c in evaluated_candidates])
        success_probs = np.array([float(c.get("success_probability", 1.0 - c.get("failure_probability", 0.15))) for c in evaluated_candidates])
        health_scores = np.array([float(c.get("rolling_health", 0.95)) for c in evaluated_candidates])

        # Min-Max Normalization for Latency and Cost penalties
        lat_min, lat_max = np.min(latencies), np.max(latencies)
        lat_norm = np.zeros_like(latencies) if lat_max == lat_min else (latencies - lat_min) / (lat_max - lat_min)

        cost_min, cost_max = np.min(costs), np.max(costs)
        cost_norm = np.zeros_like(costs) if cost_max == cost_min else (costs - cost_min) / (cost_max - cost_min)

        w_s = self.weights["success"]
        w_l = self.weights["latency"]
        w_c = self.weights["cost"]
        w_h = self.weights["health"]

        # Calculate Utility Scores
        utility_scores = (
            w_s * success_probs
            - w_l * lat_norm
            - w_c * cost_norm
            + w_h * health_scores
        )

        scored_candidates = []
        for idx, cand in enumerate(evaluated_candidates):
            c_copy = cand.copy()
            c_copy["normalized_latency"] = round(float(lat_norm[idx]), 4)
            c_copy["normalized_cost"] = round(float(cost_norm[idx]), 4)
            c_copy["utility_score"] = round(float(utility_scores[idx]), 4)
            scored_candidates.append(c_copy)

        # Deterministic Tie-Breaking Sort:
        # 1. Utility Score (Desc)
        # 2. Success Probability (Desc)
        # 3. Latency ms (Asc)
        # 4. Fee pct (Asc)
        # 5. Route ID (Alphabetical Asc)
        ranked = sorted(
            scored_candidates,
            key=lambda x: (
                -x["utility_score"],
                -x["success_probability"],
                x["expected_latency_ms"],
                x["base_fee_pct"],
                x["route_id"],
            ),
        )

        return ranked
