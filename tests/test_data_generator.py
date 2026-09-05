"""
Unit tests for the synthetic payment data generator.
"""

import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from src.data_generator.generator import PaymentDataGenerator


class TestPaymentDataGenerator(unittest.TestCase):
    """Test suite for validating synthetic payment dataset integrity, bounds, and distributions."""

    @classmethod
    def setUpClass(cls):
        """Generates a sample dataset once for all test assertions."""
        cls.generator = PaymentDataGenerator(random_seed=42)
        cls.sample_df = cls.generator.generate(num_records=10000)

    def test_generator_reproducibility(self):
        """Verifies that identical random seeds produce bitwise identical DataFrames."""
        gen1 = PaymentDataGenerator(random_seed=123)
        df1 = gen1.generate(num_records=1000)

        gen2 = PaymentDataGenerator(random_seed=123)
        df2 = gen2.generate(num_records=1000)

        pd.testing.assert_frame_equal(df1, df2)

    def test_record_count_and_columns(self):
        """Verifies that the generated dataset matches the expected record count and column schema."""
        expected_columns = [
            "transaction_id",
            "amount",
            "currency",
            "payment_method",
            "bank",
            "merchant_category",
            "hour",
            "day_of_week",
            "device_type",
            "network_type",
            "customer_age_days",
            "previous_transactions",
            "previous_failed_transactions",
            "previous_attempts",
            "transaction_velocity",
            "is_new_device",
            "bank_latency_ms",
            "gateway_latency_ms",
            "bank_success_rate",
            "gateway_success_rate",
            "payment_status",
            "failure_reason",
        ]

        self.assertEqual(len(self.sample_df), 10000)
        self.assertListEqual(list(self.sample_df.columns), expected_columns)

    def test_failure_rate_within_expected_band(self):
        """Verifies that the overall failure rate is realistic and bounded between 12% and 18%."""
        gen = PaymentDataGenerator(random_seed=42)
        df = gen.generate(num_records=50000)
        
        failure_rate = df["payment_status"].mean()
        self.assertTrue(
            0.12 <= failure_rate <= 0.18,
            f"Failure rate {failure_rate:.4f} outside target [0.12, 0.18]"
        )

    def test_data_integrity_and_bounds(self):
        """Verifies numerical ranges, absence of negative latencies, and unique primary keys."""
        # Unique IDs
        self.assertEqual(self.sample_df["transaction_id"].nunique(), len(self.sample_df))

        # Positive Amounts & Latencies
        self.assertTrue((self.sample_df["amount"] > 0).all())
        self.assertTrue((self.sample_df["bank_latency_ms"] >= 10).all())
        self.assertTrue((self.sample_df["gateway_latency_ms"] >= 10).all())

        # Temporal bounds
        self.assertTrue(self.sample_df["hour"].between(0, 23).all())
        self.assertTrue(self.sample_df["day_of_week"].between(0, 6).all())

        # Customer History Logic
        self.assertTrue(
            (self.sample_df["previous_transactions"] >= self.sample_df["previous_failed_transactions"]).all()
        )
        self.assertGreaterEqual(self.sample_df["customer_age_days"].min(), 1)

        # Probability bounds
        self.assertTrue(self.sample_df["bank_success_rate"].between(0.0, 1.0).all())
        self.assertTrue(self.sample_df["gateway_success_rate"].between(0.0, 1.0).all())

    def test_failure_reason_consistency(self):
        """Verifies that successful transactions have null reasons and failed transactions have valid reasons."""
        valid_reasons = {
            "BANK_DOWNTIME",
            "GATEWAY_TIMEOUT",
            "USER_AUTHENTICATION_ERROR",
            "INSUFFICIENT_FUNDS",
            "NETWORK_DROP",
        }

        # Success transactions must have None/NaN failure reason
        successes = self.sample_df[self.sample_df["payment_status"] == 0]
        self.assertTrue(successes["failure_reason"].isna().all())

        # Failed transactions must have a valid failure reason string
        failures = self.sample_df[self.sample_df["payment_status"] == 1]
        self.assertFalse(failures["failure_reason"].isna().any())
        self.assertTrue(set(failures["failure_reason"].unique()).issubset(valid_reasons))

    def test_all_categorical_dimensions_represented(self):
        """Verifies that all specified banks, methods, and categories are properly populated."""
        expected_banks = {"HDFC", "SBI", "ICICI", "AXIS"}
        expected_methods = {"UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"}
        expected_categories = {"ECOMMERCE", "FOOD", "TRAVEL", "UTILITIES", "ENTERTAINMENT", "HEALTHCARE", "EDUCATION"}

        self.assertEqual(set(self.sample_df["bank"].unique()), expected_banks)
        self.assertEqual(set(self.sample_df["payment_method"].unique()), expected_methods)
        self.assertEqual(set(self.sample_df["merchant_category"].unique()), expected_categories)


if __name__ == "__main__":
    unittest.main()
