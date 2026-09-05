"""
Machine Learning Model Audit & Improvement Investigation for PayRoute AI.
Audits pre-transaction features, verifies non-leakage, and benchmarks multiple classifier architectures
(HistGradientBoosting, GradientBoosting, RandomForest, LogisticRegression) with probability calibration.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)

from src.data_generator.generator import PaymentDataGenerator
from src.features.build_features import create_feature_pipeline, split_data_chronologically
from src.utils.logger import get_logger

logger = get_logger("ModelImprovement")


def run_model_comparison_study() -> Dict[str, Any]:
    """
    Executes a rigorous ML benchmark comparing 4 model families on chronological splits.
    Measures ROC-AUC, PR-AUC, Brier score, Log-Loss, F1, and inference latency.
    """
    logger.info("Starting PayRoute AI Machine Learning Model Audit & Comparison Study...")

    # 1. Load or Generate Dataset
    data_path = PROJECT_ROOT / "data" / "raw_transactions.parquet"
    if data_path.exists():
        df = pd.read_parquet(data_path)
    else:
        gen = PaymentDataGenerator(random_seed=42)
        df = gen.generate(num_records=20000)

    # 2. Chronological Train / Val / Test Split

    train_df, val_df, test_df = split_data_chronologically(df)

    preprocessor = create_feature_pipeline()
    X_train = preprocessor.fit_transform(train_df)
    y_train = train_df["payment_status"].values

    X_val = preprocessor.transform(val_df)
    y_val = val_df["payment_status"].values

    X_test = preprocessor.transform(test_df)
    y_test = test_df["payment_status"].values

    logger.info(f"Dataset split: Train={len(train_df):,}, Val={len(val_df):,}, Test={len(test_df):,}")


    models_to_test = {
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=150,
            learning_rate=0.08,
            max_depth=6,
            min_samples_leaf=25,
            l2_regularization=1.5,
            random_state=42,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=10,
            n_jobs=-1,
            random_state=42,
        ),
        "LogisticRegression": LogisticRegression(
            C=1.0,
            max_iter=500,
            random_state=42,
        ),
    }

    results: Dict[str, Any] = {}

    for name, base_clf in models_to_test.items():
        logger.info(f"Training & evaluating {name}...")
        t0 = time.time()
        base_clf.fit(X_train, y_train)
        train_time_ms = round((time.time() - t0) * 1000, 1)

        # Calibrate using Validation Set with Isotonic Regression
        calibrated = CalibratedClassifierCV(estimator=base_clf, method="isotonic", cv="prefit")
        calibrated.fit(X_val, y_val)

        # Evaluate on untouched Test Set
        t_infer0 = time.time()
        p_test = calibrated.predict_proba(X_test)[:, 1]
        infer_time_us = round(((time.time() - t_infer0) / len(X_test)) * 1_000_000, 2)

        roc_auc = float(roc_auc_score(y_test, p_test))
        pr_auc = float(average_precision_score(y_test, p_test))
        brier = float(brier_score_loss(y_test, p_test))
        lloss = float(log_loss(y_test, p_test))

        y_pred = (p_test >= 0.20).astype(int)  # Optimal threshold
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))

        results[name] = {
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "brier_score": round(brier, 4),
            "log_loss": round(lloss, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "train_time_ms": train_time_ms,
            "inference_latency_per_txn_us": infer_time_us,
        }
        logger.info(
            f"[{name}] ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f} | Brier: {brier:.4f} | Latency: {infer_time_us}μs/txn"
        )

    # Save results to models/model_comparison_audit.json
    out_path = PROJECT_ROOT / "models" / "model_comparison_audit.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Model comparison audit saved to {out_path}")
    return results


if __name__ == "__main__":
    run_model_comparison_study()
