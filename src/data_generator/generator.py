"""
Realistic Synthetic Payment Transaction Generator.

Generates reproducible payment data with multi-variable probabilistic relationships,
non-linear interactions, temporal volume curves, bank maintenance windows,
and realistic failure reasons without simplistic deterministic rules.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import yaml

from src.data_generator.distributions import (
    sample_amounts_by_category,
    sample_day_of_week,
    sample_diurnal_hours,
    sample_latencies,
    sigmoid,
    softmax,
)
from src.utils.logger import get_logger

logger = get_logger("PaymentDataGenerator")


class PaymentDataGenerator:
    """
    Generates synthetic payment transactions reflecting realistic fintech failure patterns.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        random_seed: int = 42,
    ) -> None:
        """
        Initialize generator with configuration parameters and random seed.

        Args:
            config_path: Path to data_generation.yaml. If None, default embedded settings are used.
            random_seed: Random seed for reproducibility.
        """
        self.random_seed = random_seed
        self.rng = np.random.RandomState(self.random_seed)
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Loads YAML config or falls back to robust defaults."""
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        # Look in default path
        default_path = Path(__file__).resolve().parent.parent.parent / "config" / "data_generation.yaml"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        logger.warning("Config file not found. Using internal fallback defaults.")
        return {
            "dataset": {"default_records": 100000, "currency": "INR"},
            "banks": {
                "options": ["HDFC", "SBI", "ICICI", "AXIS"],
                "weights": [0.35, 0.28, 0.22, 0.15],
                "baseline_success_rates": {"HDFC": 0.94, "ICICI": 0.93, "AXIS": 0.91, "SBI": 0.88},
                "baseline_latencies_ms": {"HDFC": 180, "ICICI": 195, "AXIS": 220, "SBI": 310},
            },
            "gateways": {
                "options": ["RAZORPAY_SIM", "CASHFREE_SIM", "PAYU_SIM", "DIRECT_BANK"],
                "weights": [0.45, 0.25, 0.20, 0.10],
                "baseline_success_rates": {"RAZORPAY_SIM": 0.96, "CASHFREE_SIM": 0.94, "PAYU_SIM": 0.93, "DIRECT_BANK": 0.89},
                "baseline_latencies_ms": {"RAZORPAY_SIM": 110, "CASHFREE_SIM": 135, "PAYU_SIM": 150, "DIRECT_BANK": 220},
            },
            "payment_methods": {
                "options": ["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"],
                "weights": [0.60, 0.18, 0.14, 0.08],
            },
            "merchant_categories": {
                "options": ["ECOMMERCE", "FOOD", "TRAVEL", "UTILITIES", "ENTERTAINMENT", "HEALTHCARE", "EDUCATION"],
                "weights": [0.30, 0.25, 0.12, 0.12, 0.10, 0.06, 0.05],
                "amount_params": {
                    "ECOMMERCE": {"mu": 7.2, "sigma": 0.95},
                    "FOOD": {"mu": 5.8, "sigma": 0.65},
                    "TRAVEL": {"mu": 8.3, "sigma": 1.10},
                    "UTILITIES": {"mu": 6.6, "sigma": 0.70},
                    "ENTERTAINMENT": {"mu": 6.2, "sigma": 0.75},
                    "HEALTHCARE": {"mu": 7.6, "sigma": 1.05},
                    "EDUCATION": {"mu": 9.2, "sigma": 1.15},
                },
            },
            "device_types": {"options": ["MOBILE", "DESKTOP", "TABLET"], "weights": [0.78, 0.18, 0.04]},
            "network_types": {
                "options": ["5G", "4G", "WIFI", "3G", "2G"],
                "weights": [0.35, 0.45, 0.14, 0.05, 0.01],
                "latency_adders_ms": {"5G": 20, "4G": 45, "WIFI": 35, "3G": 220, "2G": 650},
            },
            "failure_reasons": ["BANK_DOWNTIME", "GATEWAY_TIMEOUT", "USER_AUTHENTICATION_ERROR", "INSUFFICIENT_FUNDS", "NETWORK_DROP"],
        }

    def generate(self, num_records: int = 100000) -> pd.DataFrame:
        """
        Generates a synthetic payment dataset of given size.

        Args:
            num_records: Number of transactions to generate (default 100,000).

        Returns:
            pd.DataFrame containing the generated transaction records.
        """
        logger.info(f"Generating {num_records:,} synthetic payment transactions with seed {self.random_seed}...")

        # 1. Base Identifiers and Temporal Features
        tx_ids = [f"txn_{i+1:08d}" for i in range(num_records)]
        hours = sample_diurnal_hours(num_records, self.rng)
        days = sample_day_of_week(num_records, self.rng)
        currency = self.config.get("dataset", {}).get("currency", "INR")

        # 2. Categorical Dimensions
        banks_cfg = self.config["banks"]
        banks = self.rng.choice(banks_cfg["options"], size=num_records, p=banks_cfg["weights"])

        gateways_cfg = self.config.get("gateways", {
            "options": ["RAZORPAY_SIM", "CASHFREE_SIM", "PAYU_SIM", "DIRECT_BANK"],
            "weights": [0.45, 0.25, 0.20, 0.10],
        })
        gateways = self.rng.choice(gateways_cfg["options"], size=num_records, p=gateways_cfg["weights"])

        methods_cfg = self.config["payment_methods"]
        payment_methods = self.rng.choice(methods_cfg["options"], size=num_records, p=methods_cfg["weights"])

        cats_cfg = self.config["merchant_categories"]
        categories = self.rng.choice(cats_cfg["options"], size=num_records, p=cats_cfg["weights"])

        devices_cfg = self.config["device_types"]
        devices = self.rng.choice(devices_cfg["options"], size=num_records, p=devices_cfg["weights"])

        networks_cfg = self.config["network_types"]
        networks = self.rng.choice(networks_cfg["options"], size=num_records, p=networks_cfg["weights"])

        # 3. Numeric Amounts (Log-normal by Category)
        amounts = sample_amounts_by_category(categories, cats_cfg["amount_params"], self.rng)

        # 4. Customer History and Profile
        customer_age_days = self.rng.gamma(shape=2.0, scale=180.0, size=num_records).astype(int) + 1
        customer_age_days = np.clip(customer_age_days, 1, 1800)

        # New device is more probable for younger customer profiles
        new_device_prob = np.clip(0.40 - (customer_age_days / 365.0) * 0.08, 0.05, 0.60)
        is_new_device = (self.rng.rand(num_records) < new_device_prob).astype(int)

        # Previous transactions scale with customer age
        expected_prev_tx = np.clip((customer_age_days / 15.0), 0, 150)
        previous_transactions = self.rng.poisson(lam=expected_prev_tx, size=num_records)

        # Previous failures as a fraction of previous transactions
        prev_fail_rates = self.rng.beta(a=2.0, b=12.0, size=num_records)
        previous_failed_transactions = np.minimum(
            previous_transactions,
            np.round(previous_transactions * prev_fail_rates).astype(int),
        )

        # Transaction retry attempts (for current purchase session)
        retry_weights = [0.72, 0.16, 0.07, 0.03, 0.02]
        previous_attempts = self.rng.choice([0, 1, 2, 3, 4], size=num_records, p=retry_weights)

        # Velocity (transactions in recent rolling hour)
        velocity_lam = np.where(is_new_device, 1.2, 1.8)
        transaction_velocity = self.rng.poisson(lam=velocity_lam, size=num_records) + 1
        transaction_velocity = np.clip(transaction_velocity, 1, 10)

        # 5. Infrastructure Health & Latency Modeling
        bank_baseline_sr = np.array([banks_cfg["baseline_success_rates"].get(b, 0.92) for b in banks])
        bank_baseline_lat = np.array([banks_cfg["baseline_latencies_ms"].get(b, 200) for b in banks])

        gw_baseline_sr = np.array([gateways_cfg.get("baseline_success_rates", {}).get(g, 0.95) for g in gateways])
        gw_baseline_lat = np.array([gateways_cfg.get("baseline_latencies_ms", {}).get(g, 120) for g in gateways])

        # Simulate scheduled maintenance / degradation windows
        is_maintenance = np.zeros(num_records, dtype=bool)
        maint_cfg = banks_cfg.get("maintenance_windows", {})
        for bank_name, m_info in maint_cfg.items():
            mask = (banks == bank_name) & (hours >= m_info["start_hour"]) & (hours <= m_info["end_hour"])
            degraded_sub = mask & (self.rng.rand(num_records) < m_info.get("degradation_prob", 0.25))
            is_maintenance[degraded_sub] = True

        # Occasional random short-duration gateway or bank degradation (2% sporadic incidents)
        sporadic_bank_outage = self.rng.rand(num_records) < 0.018
        sporadic_gw_outage = self.rng.rand(num_records) < 0.012

        # Adjust rolling health metrics
        bank_success_rate = bank_baseline_sr.copy()
        bank_success_rate[is_maintenance] -= self.rng.uniform(0.15, 0.35, size=np.sum(is_maintenance))
        bank_success_rate[sporadic_bank_outage] -= self.rng.uniform(0.20, 0.40, size=np.sum(sporadic_bank_outage))
        bank_success_rate = np.clip(np.round(bank_success_rate + self.rng.normal(0, 0.01, num_records), 4), 0.40, 0.99)

        gateway_success_rate = gw_baseline_sr.copy()
        gateway_success_rate[sporadic_gw_outage] -= self.rng.uniform(0.15, 0.30, size=np.sum(sporadic_gw_outage))
        gateway_success_rate = np.clip(np.round(gateway_success_rate + self.rng.normal(0, 0.008, num_records), 4), 0.55, 0.99)

        # Network latency addition
        net_lat_adders = np.array([networks_cfg.get("latency_adders_ms", {}).get(n, 30) for n in networks])

        # Bank and Gateway Latencies
        bank_deg_mult = np.where(is_maintenance | sporadic_bank_outage, self.rng.uniform(2.0, 4.5, size=num_records), 1.0)
        bank_latency_ms = sample_latencies(bank_baseline_lat, bank_deg_mult, net_lat_adders * 0.4, self.rng)

        gw_deg_mult = np.where(sporadic_gw_outage, self.rng.uniform(2.5, 5.0, size=num_records), 1.0)
        gateway_latency_ms = sample_latencies(gw_baseline_lat, gw_deg_mult, net_lat_adders * 0.6, self.rng)

        # 6. Probabilistic Payment Failure Modeling (Log-Odds Formulation)
        # Baseline intercept tuned to achieve target ~14-16% global failure rate
        intercept = -3.18

        # Bank & Gateway Health terms
        term_bank_sr = 3.6 * (0.95 - bank_success_rate)
        term_gw_sr = 2.8 * (0.96 - gateway_success_rate)

        # Latency terms (smooth logarithmic scaling above normal baselines)
        term_bank_lat = 1.15 * np.log1p(np.maximum(0, bank_latency_ms - 160) / 250.0)
        term_gw_lat = 0.85 * np.log1p(np.maximum(0, gateway_latency_ms - 110) / 200.0)

        # Friction from previous retries and velocity
        term_attempts = 0.42 * previous_attempts
        term_velocity = 0.10 * np.maximum(0, transaction_velocity - 3)

        # Network friction
        net_risk = np.array([networks_cfg.get("timeout_risk_factors", {}).get(n, 0.0) for n in networks])
        term_network = 1.0 * net_risk

        # Payment method differences
        method_risk = np.array([methods_cfg.get("risk_factors", {}).get(m, 0.0) for m in payment_methods])
        term_method = 0.8 * method_risk

        # Interaction: Poor Network x High Latency
        is_poor_net = np.isin(networks, ["2G", "3G"])
        is_high_lat = (bank_latency_ms + gateway_latency_ms) > 500
        term_net_lat_interaction = np.where(is_poor_net & is_high_lat, 0.65, 0.0)

        # Interaction: High Ticket Size x New Device (auth / limit scrutiny)
        is_high_amount = amounts > 10000.0
        term_device_amount_interaction = np.where(is_new_device & is_high_amount, 0.40, 0.0)

        # Unobserved Stochastic Friction (Zero-mean Gaussian noise)
        noise = self.rng.normal(loc=0.0, scale=0.35, size=num_records)

        # Composite Logit Score
        logit_p = (
            intercept
            + term_bank_sr
            + term_gw_sr
            + term_bank_lat
            + term_gw_lat
            + term_attempts
            + term_velocity
            + term_network
            + term_method
            + term_net_lat_interaction
            + term_device_amount_interaction
            + noise
        )

        failure_prob = sigmoid(logit_p)

        # Draw binary payment status: 0 = SUCCESS, 1 = FAILED
        payment_status = (self.rng.rand(num_records) < failure_prob).astype(int)

        # 7. Multi-Class Failure Reason Assignment (Conditional on Failure)
        failure_reasons = self._assign_failure_reasons(
            num_records=num_records,
            payment_status=payment_status,
            bank_success_rate=bank_success_rate,
            gateway_success_rate=gateway_success_rate,
            bank_latency_ms=bank_latency_ms,
            gateway_latency_ms=gateway_latency_ms,
            payment_methods=payment_methods,
            is_new_device=is_new_device,
            amounts=amounts,
            previous_attempts=previous_attempts,
            previous_failed_transactions=previous_failed_transactions,
            networks=networks,
            devices=devices,
            is_maintenance=is_maintenance,
        )

        # 8. Assemble Clean DataFrame
        df = pd.DataFrame({
            "transaction_id": tx_ids,
            "amount": amounts,
            "currency": currency,
            "payment_method": payment_methods,
            "bank": banks,
            "merchant_category": categories,
            "hour": hours,
            "day_of_week": days,
            "device_type": devices,
            "network_type": networks,
            "customer_age_days": customer_age_days,
            "previous_transactions": previous_transactions,
            "previous_failed_transactions": previous_failed_transactions,
            "previous_attempts": previous_attempts,
            "transaction_velocity": transaction_velocity,
            "is_new_device": is_new_device,
            "bank_latency_ms": bank_latency_ms,
            "gateway_latency_ms": gateway_latency_ms,
            "bank_success_rate": bank_success_rate,
            "gateway_success_rate": gateway_success_rate,
            "payment_status": payment_status,
            "failure_reason": failure_reasons,
        })

        self._log_summary(df)
        return df

    def _assign_failure_reasons(
        self,
        num_records: int,
        payment_status: np.ndarray,
        bank_success_rate: np.ndarray,
        gateway_success_rate: np.ndarray,
        bank_latency_ms: np.ndarray,
        gateway_latency_ms: np.ndarray,
        payment_methods: np.ndarray,
        is_new_device: np.ndarray,
        amounts: np.ndarray,
        previous_attempts: np.ndarray,
        previous_failed_transactions: np.ndarray,
        networks: np.ndarray,
        devices: np.ndarray,
        is_maintenance: np.ndarray,
    ) -> np.ndarray:
        """
        Assigns probabilistic failure reasons using Softmax sampling across dynamic hazard logits.
        """
        reasons_list = [
            "BANK_DOWNTIME",
            "GATEWAY_TIMEOUT",
            "USER_AUTHENTICATION_ERROR",
            "INSUFFICIENT_FUNDS",
            "NETWORK_DROP",
        ]
        
        failure_indices = np.where(payment_status == 1)[0]
        num_failures = len(failure_indices)

        if num_failures == 0:
            return np.array([None] * num_records, dtype=object)

        # Slice attributes for failed records
        b_sr = bank_success_rate[failure_indices]
        g_sr = gateway_success_rate[failure_indices]
        b_lat = bank_latency_ms[failure_indices]
        g_lat = gateway_latency_ms[failure_indices]
        p_meth = payment_methods[failure_indices]
        is_new_dev = is_new_device[failure_indices]
        amt = amounts[failure_indices]
        p_att = previous_attempts[failure_indices]
        p_failed = previous_failed_transactions[failure_indices]
        net = networks[failure_indices]
        dev = devices[failure_indices]
        maint = is_maintenance[failure_indices]

        # Calculate hazard score for each potential reason
        # 0: BANK_DOWNTIME
        logit_bank = (
            2.8 * (0.95 - b_sr)
            + 1.6 * maint
            + 1.0 * (b_lat > 650)
            + self.rng.normal(0, 0.25, size=num_failures)
        )

        # 1: GATEWAY_TIMEOUT
        logit_gw = (
            2.2 * (0.96 - g_sr)
            + 1.4 * np.log1p(g_lat / 200.0)
            + 0.6 * np.isin(net, ["2G", "3G"])
            + self.rng.normal(0, 0.25, size=num_failures)
        )

        # 2: USER_AUTHENTICATION_ERROR
        is_card_or_nb = np.isin(p_meth, ["CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"])
        logit_auth = (
            0.9 * is_card_or_nb
            + 0.7 * is_new_dev
            + 0.5 * (amt > 8000)
            + 0.35 * p_att
            + self.rng.normal(0, 0.25, size=num_failures)
        )

        # 3: INSUFFICIENT_FUNDS
        logit_funds = (
            1.2 * np.log1p(amt / 2500.0)
            + 0.45 * (p_failed > 1)
            + 0.3 * (p_meth == "UPI")
            + self.rng.normal(0, 0.25, size=num_failures)
        )

        # 4: NETWORK_DROP
        logit_net = (
            2.4 * (net == "2G")
            + 1.3 * (net == "3G")
            + 0.4 * (dev == "MOBILE")
            + 0.5 * (g_lat > 400)
            + self.rng.normal(0, 0.25, size=num_failures)
        )

        # Stack into matrix [num_failures, 5]
        reason_logits = np.column_stack([
            logit_bank,
            logit_gw,
            logit_auth,
            logit_funds,
            logit_net,
        ])

        # Compute categorical probabilities via Softmax
        reason_probs = softmax(reason_logits, temperature=0.85)

        # Sample categorical choices
        sampled_reasons = []
        for i in range(num_failures):
            chosen = self.rng.choice(reasons_list, p=reason_probs[i])
            sampled_reasons.append(chosen)

        # Build full array: None for success, sampled string for failure
        full_reasons = np.array([None] * num_records, dtype=object)
        full_reasons[failure_indices] = sampled_reasons

        return full_reasons

    def _log_summary(self, df: pd.DataFrame) -> None:
        """Logs high-level dataset health metrics and failure statistics."""
        total = len(df)
        failures = int(df["payment_status"].sum())
        failure_rate = (failures / total) * 100.0

        logger.info(f"Dataset generated successfully: {total:,} rows, {len(df.columns)} columns.")
        logger.info(f"Payment Status: Success = {total - failures:,} ({(100.0 - failure_rate):.2f}%), Failed = {failures:,} ({failure_rate:.2f}%)")

        reason_counts = df[df["payment_status"] == 1]["failure_reason"].value_counts().to_dict()
        logger.info(f"Failure Reasons Breakdown: {reason_counts}")
        logger.info(f"Mean Bank Latency: {df['bank_latency_ms'].mean():.1f}ms | Mean Gateway Latency: {df['gateway_latency_ms'].mean():.1f}ms")

    def save_csv(self, df: pd.DataFrame, output_path: str) -> str:
        """
        Saves DataFrame to CSV ensuring parent directories exist.

        Args:
            df: Generated DataFrame.
            output_path: Target filepath.

        Returns:
            Resolved absolute path.
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_file, index=False)
        logger.info(f"Saved dataset to {out_file} ({out_file.stat().st_size / (1024 * 1024):.2f} MB)")
        return str(out_file)


def main() -> None:
    """CLI entry point for synthetic dataset generation."""
    parser = argparse.ArgumentParser(description="PayRoute AI - Synthetic Payment Data Generator")
    parser.add_argument("--records", type=int, default=100000, help="Number of records to generate (default: 100000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--config", type=str, default=None, help="Path to custom config YAML")
    parser.add_argument("--output", type=str, default="data/raw/payments_synthetic.csv", help="Output CSV path")

    args = parser.parse_args()

    generator = PaymentDataGenerator(config_path=args.config, random_seed=args.seed)
    df = generator.generate(num_records=args.records)
    generator.save_csv(df, args.output)


if __name__ == "__main__":
    main()
