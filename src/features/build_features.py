"""
Core feature engineering pipeline builder and chronological dataset splitting.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.features.encoders import (
    AmountRiskTransformer,
    CustomerBehaviorTransformer,
    CyclicTemporalTransformer,
    InfrastructureHealthTransformer,
)
from src.utils.logger import get_logger

logger = get_logger("FeaturePipeline")

# Feature Column Categorization
CATEGORICAL_FEATURES = [
    "payment_method",
    "bank",
    "merchant_category",
    "device_type",
    "network_type",
]

TEMPORAL_INPUT_COLS = ["hour", "day_of_week"]
CUSTOMER_INPUT_COLS = [
    "previous_transactions",
    "previous_failed_transactions",
    "previous_attempts",
    "transaction_velocity",
    "customer_age_days",
]
INFRA_INPUT_COLS = [
    "bank_latency_ms",
    "gateway_latency_ms",
    "bank_success_rate",
    "gateway_success_rate",
]
AMOUNT_INPUT_COLS = ["amount", "is_new_device"]

TARGET_COLUMN = "payment_status"
POST_OUTCOME_COLUMNS = ["failure_reason"]
METADATA_COLUMNS = ["transaction_id", "currency", "created_at"]


def split_data_chronologically(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits the dataset strictly chronologically to prevent temporal lookahead leakage.

    Args:
        df: Input DataFrame sorted chronologically.
        train_ratio: Earliest portion for model training (default 70%).
        val_ratio: Intermediate portion for calibration and tuning (default 15%).
        test_ratio: Latest portion for final out-of-time evaluation (default 15%).

    Returns:
        (train_df, val_df, test_df) tuple.
    """
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Split ratios must sum to 1.0"
    
    n_total = len(df)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_df = df.iloc[:n_train].copy().reset_index(drop=True)
    val_df = df.iloc[n_train : n_train + n_val].copy().reset_index(drop=True)
    test_df = df.iloc[n_train + n_val :].copy().reset_index(drop=True)

    logger.info(
        f"Chronological split complete: Train={len(train_df):,} ({train_ratio*100:.0f}%), "
        f"Val={len(val_df):,} ({val_ratio*100:.0f}%), Test={len(test_df):,} ({test_ratio*100:.0f}%)"
    )

    return train_df, val_df, test_df


def create_feature_pipeline() -> ColumnTransformer:
    """
    Constructs a complete Scikit-Learn ColumnTransformer pipeline.
    Combines custom transformers for temporal, behavioral, health, and amount features
    with OneHotEncoder for categoricals and StandardScaler for continuous features.
    """
    # 1. Custom Engineered Numerical Feature Pipelines
    temporal_pipe = Pipeline([
        ("cyclic_transform", CyclicTemporalTransformer(hour_col="hour", day_col="day_of_week")),
        ("scaler", StandardScaler()),
    ])

    customer_pipe = Pipeline([
        ("customer_transform", CustomerBehaviorTransformer()),
        ("scaler", StandardScaler()),
    ])

    infra_pipe = Pipeline([
        ("infra_transform", InfrastructureHealthTransformer()),
        ("scaler", StandardScaler()),
    ])

    amount_pipe = Pipeline([
        ("amount_transform", AmountRiskTransformer(amount_col="amount", new_device_col="is_new_device")),
        ("scaler", StandardScaler()),
    ])

    # 2. Categorical Encoding Pipeline (Handles unseen categories at inference)
    categorical_pipe = Pipeline([
        (
            "onehot",
            OneHotEncoder(
                categories="auto",
                drop=None,
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ])

    # 3. Composite ColumnTransformer
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", categorical_pipe, CATEGORICAL_FEATURES),
            ("temporal", temporal_pipe, TEMPORAL_INPUT_COLS),
            ("customer", customer_pipe, CUSTOMER_INPUT_COLS),
            ("infra", infra_pipe, INFRA_INPUT_COLS),
            ("amount", amount_pipe, AMOUNT_INPUT_COLS),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )

    return preprocessor


def get_feature_names(fitted_pipeline: ColumnTransformer) -> List[str]:
    """
    Extracts all output feature names from a fitted ColumnTransformer.
    """
    try:
        return list(fitted_pipeline.get_feature_names_out())
    except Exception as e:
        logger.warning(f"Could not retrieve feature names via get_feature_names_out: {e}")
        return [f"feat_{i}" for i in range(fitted_pipeline.n_features_in_)]


def transform_single_transaction(
    txn_dict: Dict[str, Any],
    fitted_pipeline: ColumnTransformer,
) -> np.ndarray:
    """
    Preprocesses a single real-time payment transaction request dictionary.

    Args:
        txn_dict: Dictionary containing raw transaction attributes.
        fitted_pipeline: Fitted ColumnTransformer artifact.

    Returns:
        2D numpy array of shape (1, n_features) ready for model inference.
    """
    df_single = pd.DataFrame([txn_dict])
    return fitted_pipeline.transform(df_single)
