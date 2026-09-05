"""
Unit tests for the PayRoute AI feature engineering pipeline and chronological splitting.
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
from src.features.build_features import (
    create_feature_pipeline,
    get_feature_names,
    split_data_chronologically,
    transform_single_transaction,
)


class TestFeaturePipeline(unittest.TestCase):
    """Test suite for validating feature engineering, encodings, and temporal splitting."""

    @classmethod
    def setUpClass(cls):
        """Generates sample dataset and fits the feature pipeline on training partition."""
        gen = PaymentDataGenerator(random_seed=42)
        cls.raw_df = gen.generate(num_records=10000)

        cls.train_df, cls.val_df, cls.test_df = split_data_chronologically(
            cls.raw_df, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15
        )

        cls.pipeline = create_feature_pipeline()
        cls.X_train = cls.pipeline.fit_transform(cls.train_df)
        cls.X_val = cls.pipeline.transform(cls.val_df)
        cls.X_test = cls.pipeline.transform(cls.test_df)
        cls.feature_names = get_feature_names(cls.pipeline)

    def test_chronological_split_shapes_and_order(self):
        """Verifies strict temporal partitioning without row loss or index shuffling."""
        self.assertEqual(len(self.train_df), 7000)
        self.assertEqual(len(self.val_df), 1500)
        self.assertEqual(len(self.test_df), 1500)
        self.assertEqual(len(self.train_df) + len(self.val_df) + len(self.test_df), len(self.raw_df))

        # Check transaction_id continuity
        self.assertEqual(self.train_df.iloc[0]["transaction_id"], "txn_00000001")
        self.assertEqual(self.train_df.iloc[-1]["transaction_id"], "txn_00007000")
        self.assertEqual(self.val_df.iloc[0]["transaction_id"], "txn_00007001")
        self.assertEqual(self.val_df.iloc[-1]["transaction_id"], "txn_00008500")
        self.assertEqual(self.test_df.iloc[0]["transaction_id"], "txn_00008501")
        self.assertEqual(self.test_df.iloc[-1]["transaction_id"], "txn_00010000")

    def test_feature_matrix_shapes_and_no_nans(self):
        """Verifies feature matrix dimensions and total absence of NaN/inf values."""
        n_features = len(self.feature_names)
        self.assertGreaterEqual(n_features, 30)

        self.assertEqual(self.X_train.shape, (7000, n_features))
        self.assertEqual(self.X_val.shape, (1500, n_features))
        self.assertEqual(self.X_test.shape, (1500, n_features))

        self.assertFalse(np.isnan(self.X_train).any(), "NaN values found in X_train")
        self.assertFalse(np.isnan(self.X_val).any(), "NaN values found in X_val")
        self.assertFalse(np.isnan(self.X_test).any(), "NaN values found in X_test")

        self.assertFalse(np.isinf(self.X_train).any(), "Inf values found in X_train")
        self.assertFalse(np.isinf(self.X_val).any(), "Inf values found in X_val")
        self.assertFalse(np.isinf(self.X_test).any(), "Inf values found in X_test")

    def test_unseen_categories_graceful_handling(self):
        """Verifies that previously unseen category strings do not crash the pipeline."""
        novel_row = {
            "amount": 2500.0,
            "currency": "INR",
            "payment_method": "NEW_CRYPTO_METHOD",  # Unseen method
            "bank": "UNKNOWN_FOREIGN_BANK",         # Unseen bank
            "merchant_category": "SPACE_TRAVEL",    # Unseen category
            "hour": 14,
            "day_of_week": 2,
            "device_type": "SMART_WATCH",           # Unseen device
            "network_type": "SATELLITE",            # Unseen network
            "customer_age_days": 180,
            "previous_transactions": 5,
            "previous_failed_transactions": 1,
            "previous_attempts": 0,
            "transaction_velocity": 2,
            "is_new_device": 0,
            "bank_latency_ms": 210,
            "gateway_latency_ms": 130,
            "bank_success_rate": 0.93,
            "gateway_success_rate": 0.95,
        }

        # Should transform without exception
        transformed = transform_single_transaction(novel_row, self.pipeline)
        self.assertEqual(transformed.shape, (1, len(self.feature_names)))
        self.assertFalse(np.isnan(transformed).any())

    def test_single_transaction_inference(self):
        """Verifies real-time transformation on a single payment request dictionary."""
        sample_dict = self.raw_df.iloc[0].to_dict()
        single_X = transform_single_transaction(sample_dict, self.pipeline)

        self.assertEqual(single_X.shape, (1, len(self.feature_names)))
        # Verify it matches the first row of X_train within floating point tolerance
        np.testing.assert_allclose(single_X[0], self.X_train[0], rtol=1e-5, atol=1e-5)

    def test_target_and_leakage_exclusion(self):
        """Verifies target and post-outcome diagnostic fields are not in the feature matrix."""
        for feat in self.feature_names:
            self.assertNotIn("payment_status", feat)
            self.assertNotIn("failure_reason", feat)
            self.assertNotIn("transaction_id", feat)


if __name__ == "__main__":
    unittest.main()
