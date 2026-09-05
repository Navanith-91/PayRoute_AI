"""
Unit tests for the machine learning models, probability calibration, explainer, and inference wrapper.
"""

import json
import sys
import time
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from src.ml.predictor import PaymentPredictor


class TestMLPipeline(unittest.TestCase):
    """Test suite for validating trained ML artifacts, calibration, and inference wrapper."""

    @classmethod
    def setUpClass(cls):
        """Initializes PaymentPredictor loading serialized models."""
        cls.predictor = PaymentPredictor()

        cls.sample_healthy_txn = {
            "amount": 450.0,
            "currency": "INR",
            "payment_method": "UPI",
            "bank": "HDFC",
            "merchant_category": "FOOD",
            "hour": 12,
            "day_of_week": 2,
            "device_type": "MOBILE",
            "network_type": "5G",
            "customer_age_days": 400,
            "previous_transactions": 25,
            "previous_failed_transactions": 1,
            "previous_attempts": 0,
            "transaction_velocity": 1,
            "is_new_device": 0,
            "bank_latency_ms": 140,
            "gateway_latency_ms": 90,
            "bank_success_rate": 0.96,
            "gateway_success_rate": 0.98,
        }

        cls.sample_risky_txn = {
            "amount": 25000.0,
            "currency": "INR",
            "payment_method": "NET_BANKING",
            "bank": "SBI",
            "merchant_category": "EDUCATION",
            "hour": 3,  # Maintenance hour
            "day_of_week": 4,
            "device_type": "MOBILE",
            "network_type": "2G",  # Poor network
            "customer_age_days": 15,
            "previous_transactions": 2,
            "previous_failed_transactions": 2,
            "previous_attempts": 3,  # Heavy retry fatigue
            "transaction_velocity": 5,
            "is_new_device": 1,
            "bank_latency_ms": 780,
            "gateway_latency_ms": 450,
            "bank_success_rate": 0.65,
            "gateway_success_rate": 0.70,
        }

    def test_saved_model_artifacts_exist(self):
        """Verifies that all 6 required model artifacts exist in models/ directory."""
        models_dir = PROJECT_ROOT / "models"
        required_files = [
            "preprocessor.joblib",
            "failure_model.joblib",
            "calibrated_failure_model.joblib",
            "reason_model.joblib",
            "feature_metadata.json",
            "model_metrics.json",
        ]
        for f in required_files:
            self.assertTrue((models_dir / f).exists(), f"Missing model artifact: {f}")

    def test_calibrated_probabilities_in_valid_range(self):
        """Verifies that predicted failure probabilities are valid bounded probabilities."""
        res_healthy = self.predictor.predict_failure(self.sample_healthy_txn)
        res_risky = self.predictor.predict_failure(self.sample_risky_txn)

        self.assertGreaterEqual(res_healthy["failure_probability"], 0.0)
        self.assertLessEqual(res_healthy["failure_probability"], 1.0)
        self.assertAlmostEqual(res_healthy["failure_probability"] + res_healthy["success_probability"], 1.0, places=3)

        # Risky transaction should have substantially higher failure probability than healthy transaction
        self.assertGreater(res_risky["failure_probability"], res_healthy["failure_probability"])
        self.assertEqual(res_risky["risk_level"], "HIGH")

    def test_reason_probabilities_sum_to_one(self):
        """Verifies that multi-class failure diagnosis returns probabilities summing to 1.0."""
        res = self.predictor.predict_failure_reason(self.sample_risky_txn)
        expected_classes = {
            "BANK_DOWNTIME",
            "GATEWAY_TIMEOUT",
            "USER_AUTHENTICATION_ERROR",
            "INSUFFICIENT_FUNDS",
            "NETWORK_DROP",
        }

        self.assertIn(res["predicted_reason"], expected_classes)
        self.assertEqual(set(res["reason_probabilities"].keys()), expected_classes)
        prob_sum = sum(res["reason_probabilities"].values())
        self.assertAlmostEqual(prob_sum, 1.0, places=3)

    def test_explainer_local_attribution(self):
        """Verifies local feature attribution decomposes into risk contributors and protective factors."""
        explanation = self.predictor.explain(self.sample_risky_txn, top_k=4)
        self.assertIn("top_risk_contributors", explanation)
        self.assertIn("top_protective_factors", explanation)
        self.assertGreater(len(explanation["top_risk_contributors"]), 0)

        # Check positive impact for risk contributors
        for factor in explanation["top_risk_contributors"]:
            self.assertGreater(factor["impact"], 0.0)
            self.assertEqual(factor["direction"], "RISK_INCREASING")

    def test_single_transaction_inference_latency(self):
        """Verifies that real-time evaluation executes within latency SLA (< 50ms)."""
        # Warm-up
        _ = self.predictor.evaluate_full_transaction(self.sample_healthy_txn)
        
        start_time = time.perf_counter()
        n_iters = 50
        for _ in range(n_iters):
            _ = self.predictor.evaluate_full_transaction(self.sample_healthy_txn)
        elapsed_ms = (time.perf_counter() - start_time) / n_iters * 1000.0

        self.assertLess(elapsed_ms, 50.0, f"Inference latency {elapsed_ms:.2f}ms exceeds SLA limit")


if __name__ == "__main__":
    unittest.main()
