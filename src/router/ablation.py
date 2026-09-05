"""
Routing Ablation Study Runner for PayRoute AI.
Compares 4 routing policy variants across an identical 3,000 transaction sequence with an injected outage:
- Model A: Success Probability only (w_s = 1.0)
- Model B: Success Probability (0.75) + Latency (0.25)
- Model C: Success Probability (0.65) + Latency (0.20) + Cost (0.15)
- Model D (Full PayRoute AI): Success (0.60) + Latency (0.20) + Cost (0.10) + Health (0.10) + Circuit Breakers
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from src.data_generator.generator import PaymentDataGenerator
from src.router.router import SmartRouter
from src.utils.logger import get_logger

logger = get_logger("RoutingAblation")


def run_ablation_study(
    num_transactions: int = 3000,
    random_seed: int = 42,
    outage_start: int = 800,
    outage_end: int = 1800,
    degraded_bank: str = "SBI",
    degraded_failure_rate: float = 0.75,
    degraded_latency_ms: int = 750,
) -> Dict[str, Any]:
    """
    Executes a 4-variant routing ablation study over an identical stream of transactions.
    """
    logger.info(f"Generating {num_transactions:,} transactions for ablation benchmark...")
    gen = PaymentDataGenerator(random_seed=random_seed)
    df_txns = gen.generate(num_records=num_transactions)

    # Define the 4 ablation configurations
    models_config = {
        "Model A (Success Only)": {
            "weights": {"success": 1.0, "latency": 0.0, "cost": 0.0, "health": 0.0},
            "use_circuit_breakers": False,
        },
        "Model B (Success + Latency)": {
            "weights": {"success": 0.75, "latency": 0.25, "cost": 0.0, "health": 0.0},
            "use_circuit_breakers": False,
        },
        "Model C (Success + Latency + Cost)": {
            "weights": {"success": 0.65, "latency": 0.20, "cost": 0.15, "health": 0.0},
            "use_circuit_breakers": False,
        },
        "Model D (Full PayRoute AI: Multi-Criteria + CB)": {
            "weights": {"success": 0.60, "latency": 0.20, "cost": 0.10, "health": 0.10},
            "use_circuit_breakers": True,
        },
    }

    results = {}

    for model_name, cfg in models_config.items():
        logger.info(f"Evaluating {model_name}...")
        router = SmartRouter(random_seed=random_seed)
        router.scorer.weights = cfg["weights"]

        # If circuit breakers are disabled for this ablation, increase trip threshold to 1.0
        if not cfg["use_circuit_breakers"]:
            for tracker in router.health_trackers.values():
                tracker.failure_rate_threshold = 1.0  # Never trip

        rng = np.random.RandomState(random_seed)
        outcomes: List[int] = []
        latencies: List[int] = []
        routes_chosen: List[str] = []

        for i, row in df_txns.iterrows():
            current_time = float(i * 0.5)
            is_in_outage = (outage_start <= i <= outage_end)

            req = row.to_dict()
            bank = req["bank"]

            decision = router.route_payment(
                payment_request=req,
                current_time=current_time,
                enable_exploration=True,
                include_explanation=False,
            )

            chosen_route = decision["primary_route"]
            routes_chosen.append(chosen_route if chosen_route else "NONE")

            if chosen_route is None:
                failed = True
                lat = 10
            else:
                if is_in_outage and bank == degraded_bank and chosen_route == "ROUTE_SBI_DIRECT":
                    failed = (rng.rand() < degraded_failure_rate)
                    lat = degraded_latency_ms + rng.randint(-50, 150)
                elif is_in_outage and bank == degraded_bank and chosen_route != "ROUTE_SBI_DIRECT":
                    failed = (rng.rand() < 0.12)
                    lat = 180 + rng.randint(-20, 40)
                else:
                    failed = (row["payment_status"] == 1)
                    lat = int(row["bank_latency_ms"] + row["gateway_latency_ms"])

                # Record outcome to update router health
                router.record_outcome(
                    route_id=chosen_route,
                    payment_status=(1 if failed else 0),
                    latency_ms=lat,
                    current_time=current_time,
                )

            outcomes.append(1 if failed else 0)
            latencies.append(max(10, lat))

        total = len(df_txns)
        success_count = total - sum(outcomes)
        sr = (success_count / total) * 100.0
        avg_lat = float(np.mean(latencies))
        p95_lat = float(np.percentile(latencies, 95))

        results[model_name] = {
            "success_rate_pct": round(sr, 2),
            "failure_rate_pct": round(100.0 - sr, 2),
            "avg_latency_ms": round(avg_lat, 1),
            "p95_latency_ms": round(p95_lat, 1),
            "total_failures": sum(outcomes),
        }

    # Print clean summary table
    logger.info("==================================================================================")
    logger.info("                         ROUTING ABLATION STUDY RESULTS                           ")
    logger.info("==================================================================================")
    for k, v in results.items():
        logger.info(
            f"{k:46} | Success: {v['success_rate_pct']}% | "
            f"Avg Lat: {v['avg_latency_ms']}ms | P95 Lat: {v['p95_latency_ms']}ms | Failures: {v['total_failures']:,}"
        )
    logger.info("==================================================================================")

    return results


if __name__ == "__main__":
    run_ablation_study()
