"""
Comparative Routing Simulation and Outage Benchmark Runner for PayRoute AI.
Benchmarks Strategy A (Naive Static Routing) vs Strategy B (PayRoute AI Smart Routing)
under realistic provider degradation and recovery scenarios.
"""

import argparse
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from src.data_generator.generator import PaymentDataGenerator
from src.router.circuit_breaker import CircuitState
from src.router.router import SmartRouter
from src.utils.logger import get_logger

logger = get_logger("RoutingSimulator")


class RoutingSimulator:
    """
    Simulates high-volume payment transactions to benchmark Smart Routing against Naive Routing.
    """

    def __init__(
        self,
        num_transactions: int = 3000,
        random_seed: int = 42,
    ) -> None:
        self.num_transactions = num_transactions
        self.random_seed = random_seed
        self.rng = np.random.RandomState(random_seed)
        self.py_rng = random.Random(random_seed)

        # Default naive mapping (static routing table)
        self.naive_routing_map = {
            "HDFC": "ROUTE_HDFC_RAZORPAY",
            "SBI": "ROUTE_SBI_DIRECT",
            "ICICI": "ROUTE_ICICI_RAZORPAY",
            "AXIS": "ROUTE_AXIS_RAZORPAY",
        }

        # Initialize SmartRouter
        self.router = SmartRouter(random_seed=random_seed)

    def run_benchmark(
        self,
        outage_start: int = 800,
        outage_end: int = 1800,
        degraded_bank: str = "SBI",
        degraded_failure_rate: float = 0.75,
        degraded_latency_ms: int = 750,
    ) -> Dict[str, Any]:
        """
        Executes comparative simulation stream over identical transaction requests.

        Args:
            outage_start: Index when the degraded bank outage begins.
            outage_end: Index when the degraded bank recovers.
            degraded_bank: The bank experiencing severe provider degradation.
            degraded_failure_rate: Injected failure rate during outage window.
            degraded_latency_ms: Injected latency during outage window.

        Returns:
            Dictionary containing comprehensive comparative metrics.
        """
        logger.info(f"Generating {self.num_transactions:,} simulation transactions (Seed: {self.random_seed})...")
        gen = PaymentDataGenerator(random_seed=self.random_seed)
        df_txns = gen.generate(num_records=self.num_transactions)

        naive_outcomes: List[int] = []  # 0=success, 1=failed
        naive_latencies: List[int] = []
        naive_routes_chosen: List[str] = []

        smart_outcomes: List[int] = []
        smart_latencies: List[int] = []
        smart_routes_chosen: List[str] = []
        smart_strategies_used: List[str] = []
        prevented_failures: int = 0

        logger.info(
            f"Starting simulation. Outage on {degraded_bank} active from txn {outage_start} to {outage_end}..."
        )

        for i, row in df_txns.iterrows():
            current_time = float(i * 0.5)  # 1 transaction every 0.5s
            is_in_outage = (outage_start <= i <= outage_end)

            req = row.to_dict()
            bank = req["bank"]

            # -------------------------------------------------------------
            # 1. Strategy A: Naive Static Routing
            # -------------------------------------------------------------
            naive_route = self.naive_routing_map.get(bank, "ROUTE_HDFC_RAZORPAY")
            naive_routes_chosen.append(naive_route)

            # Determine actual simulated outcome on Naive Route
            if is_in_outage and bank == degraded_bank and naive_route == "ROUTE_SBI_DIRECT":
                # Severe outage on default SBI route
                naive_failed = (self.rng.rand() < degraded_failure_rate)
                naive_lat = degraded_latency_ms + self.rng.randint(-50, 150)
            else:
                naive_failed = (row["payment_status"] == 1)
                naive_lat = int(row["bank_latency_ms"] + row["gateway_latency_ms"])

            naive_outcomes.append(1 if naive_failed else 0)
            naive_latencies.append(max(10, naive_lat))

            # -------------------------------------------------------------
            # 2. Strategy B: PayRoute AI Smart Routing
            # -------------------------------------------------------------
            decision = self.router.route_payment(
                payment_request=req,
                current_time=current_time,
                enable_exploration=True,
                include_explanation=False,
            )

            chosen_route = decision["primary_route"]
            strategy = decision["routing_strategy"]
            smart_routes_chosen.append(chosen_route if chosen_route else "NONE")
            smart_strategies_used.append(strategy)

            if chosen_route is None:
                # No healthy route available
                smart_failed = True
                smart_lat = 10
            else:
                if is_in_outage and bank == degraded_bank and chosen_route == "ROUTE_SBI_DIRECT":
                    smart_failed = (self.rng.rand() < degraded_failure_rate)
                    smart_lat = degraded_latency_ms + self.rng.randint(-50, 150)
                elif is_in_outage and bank == degraded_bank and chosen_route != "ROUTE_SBI_DIRECT":
                    # Alternative healthy gateway selected by AI during outage!
                    smart_failed = (self.rng.rand() < 0.12)  # Low healthy failure rate
                    smart_lat = 180 + self.rng.randint(-20, 40)
                else:
                    smart_failed = (row["payment_status"] == 1)
                    smart_lat = int(row["bank_latency_ms"] + row["gateway_latency_ms"])

                # Update SmartRouter health trackers
                self.router.record_outcome(
                    route_id=chosen_route,
                    payment_status=(1 if smart_failed else 0),
                    latency_ms=smart_lat,
                    current_time=current_time,
                )

            smart_outcomes.append(1 if smart_failed else 0)
            smart_latencies.append(max(10, smart_lat))

            # Count prevented failures (where Naive failed, but Smart succeeded)
            if naive_failed and not smart_failed:
                prevented_failures += 1

        # -------------------------------------------------------------
        # Aggregate Benchmark Metrics
        # -------------------------------------------------------------
        total = len(df_txns)
        naive_success_count = total - sum(naive_outcomes)
        naive_success_rate = (naive_success_count / total) * 100.0
        naive_avg_lat = float(np.mean(naive_latencies))
        naive_med_lat = float(np.median(naive_latencies))

        smart_success_count = total - sum(smart_outcomes)
        smart_success_rate = (smart_success_count / total) * 100.0
        smart_avg_lat = float(np.mean(smart_latencies))
        smart_med_lat = float(np.median(smart_latencies))

        sr_uplift = smart_success_rate - naive_success_rate
        lat_reduction = naive_avg_lat - smart_avg_lat

        strategy_counts = pd.Series(smart_strategies_used).value_counts().to_dict()
        route_dist = pd.Series(smart_routes_chosen).value_counts().to_dict()

        benchmark_results = {
            "total_transactions": total,
            "outage_window": {"start_txn": outage_start, "end_txn": outage_end, "degraded_bank": degraded_bank},
            "naive_routing": {
                "success_count": naive_success_count,
                "failure_count": sum(naive_outcomes),
                "success_rate_pct": round(naive_success_rate, 2),
                "failure_rate_pct": round(100.0 - naive_success_rate, 2),
                "avg_latency_ms": round(naive_avg_lat, 1),
                "median_latency_ms": round(naive_med_lat, 1),
            },
            "smart_routing": {
                "success_count": smart_success_count,
                "failure_count": sum(smart_outcomes),
                "success_rate_pct": round(smart_success_rate, 2),
                "failure_rate_pct": round(100.0 - smart_success_rate, 2),
                "avg_latency_ms": round(smart_avg_lat, 1),
                "median_latency_ms": round(smart_med_lat, 1),
            },
            "business_impact": {
                "success_rate_uplift_pct_points": round(sr_uplift, 2),
                "prevented_failures_count": prevented_failures,
                "average_latency_reduction_ms": round(lat_reduction, 1),
            },
            "routing_strategy_distribution": strategy_counts,
            "route_traffic_distribution": route_dist,
            "final_circuit_breaker_states": self.router.get_system_health_snapshot(),
        }

        self._log_benchmark_summary(benchmark_results)
        return benchmark_results

    def _log_benchmark_summary(self, res: Dict[str, Any]) -> None:
        """Logs readable benchmark comparison table."""
        logger.info("=================================================================")
        logger.info("       PAYROUTE AI SMART ROUTING BENCHMARK RESULTS               ")
        logger.info("=================================================================")
        logger.info(f"Total Transactions Simulated: {res['total_transactions']:,}")
        logger.info(
            f"Naive Routing Success Rate:  {res['naive_routing']['success_rate_pct']}% "
            f"(Avg Latency: {res['naive_routing']['avg_latency_ms']}ms)"
        )
        logger.info(
            f"Smart Routing Success Rate:  {res['smart_routing']['success_rate_pct']}% "
            f"(Avg Latency: {res['smart_routing']['avg_latency_ms']}ms)"
        )
        logger.info(
            f"SUCCESS RATE UPLIFT:         +{res['business_impact']['success_rate_uplift_pct_points']}% points"
        )
        logger.info(
            f"PREVENTED PAYMENT FAILURES:  {res['business_impact']['prevented_failures_count']:,} transactions"
        )
        logger.info(
            f"AVERAGE LATENCY REDUCTION:   -{res['business_impact']['average_latency_reduction_ms']}ms"
        )
        logger.info(f"Routing Strategy Breakdown:  {res['routing_strategy_distribution']}")
        logger.info("=================================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="PayRoute AI Smart Routing Simulator")
    parser.add_argument("--transactions", type=int, default=3000, help="Number of transactions to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for simulation")
    args = parser.parse_args()

    sim = RoutingSimulator(num_transactions=args.transactions, random_seed=args.seed)
    sim.run_benchmark()


if __name__ == "__main__":
    main()
