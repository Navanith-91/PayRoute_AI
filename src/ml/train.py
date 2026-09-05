"""
End-to-End Machine Learning Training, Calibration, and Artifact Serialization Pipeline.
Trains Stage-1 Binary Failure Predictor and Stage-2 Multi-Class Reason Classifier.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.features.build_features import (
    create_feature_pipeline,
    get_feature_names,
    split_data_chronologically,
)
from src.features.run_eda import find_raw_dataset, load_dataset
from src.utils.logger import get_logger

logger = get_logger("ML_Trainer")

MODELS_DIR = PROJECT_ROOT / "models"


def calculate_binary_metrics(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Calculates comprehensive binary classification and calibration metrics."""
    y_pred = (y_proba >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    pr_auc = float(average_precision_score(y_true, y_proba))
    roc_auc = float(roc_auc_score(y_true, y_proba))
    brier = float(brier_score_loss(y_true, y_proba))
    logloss = float(log_loss(y_true, np.clip(y_proba, 1e-7, 1 - 1e-7)))
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Business Simulation Cost: False Negatives cost 5x False Positives
    expected_cost = int(5 * fn + 1 * fp)

    return {
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "brier_score": round(brier, 4),
        "log_loss": round(logloss, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "expected_business_cost": expected_cost,
        "threshold": threshold,
    }


def perform_threshold_analysis(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    thresholds: Optional[List[float]] = None,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Evaluates model trade-offs across multiple probability thresholds.
    Selects the optimal threshold minimizing asymmetric business cost (Cost_FN=5, Cost_FP=1).
    """
    if thresholds is None:
        thresholds = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]

    results = []
    min_cost = float("inf")
    optimal_thresh = 0.50

    for th in thresholds:
        metrics = calculate_binary_metrics(y_true, y_proba, threshold=th)
        results.append(metrics)
        if metrics["expected_business_cost"] < min_cost:
            min_cost = metrics["expected_business_cost"]
            optimal_thresh = th

    logger.info(f"Optimal Decision Threshold: {optimal_thresh:.2f} (Minimum Expected Cost: {min_cost:,})")
    return optimal_thresh, results


def train_and_evaluate_all() -> Dict[str, Any]:
    """
    Executes complete Phase 3 ML workflow:
    1. Chronological splitting (70/15/15)
    2. Feature pipeline fitting on train data only
    3. Baseline Logistic Regression training
    4. Gradient Boosted Tree training with sample weighting
    5. Probability calibration on validation data
    6. Asymmetric cost threshold analysis
    7. Multi-class reason diagnosis classifier
    8. Final out-of-time test evaluation
    9. Serialization of artifacts to models/
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = find_raw_dataset()
    df = load_dataset(raw_path)

    # 1. Chronological Split
    train_df, val_df, test_df = split_data_chronologically(df, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)

    # 2. Fit Preprocessing Pipeline strictly on Train Set
    logger.info("Fitting Scikit-Learn Feature Pipeline on Training partition...")
    preprocessor = create_feature_pipeline()
    X_train = preprocessor.fit_transform(train_df)
    X_val = preprocessor.transform(val_df)
    X_test = preprocessor.transform(test_df)
    feature_names = get_feature_names(preprocessor)

    y_train = train_df["payment_status"].values
    y_val = val_df["payment_status"].values
    y_test = test_df["payment_status"].values

    logger.info(f"Feature Matrix: {X_train.shape[1]} features engineered.")

    # 3. Train Baseline Model (Logistic Regression)
    logger.info("Training Baseline Model (Logistic Regression)...")
    baseline_model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    baseline_model.fit(X_train, y_train)
    val_proba_base = baseline_model.predict_proba(X_val)[:, 1]
    val_metrics_base = calculate_binary_metrics(y_val, val_proba_base, threshold=0.50)
    logger.info(f"Baseline Validation Results: PR-AUC={val_metrics_base['pr_auc']}, ROC-AUC={val_metrics_base['roc_auc']}, Brier={val_metrics_base['brier_score']}")

    # 4. Train Main Model (Gradient Boosted Decision Trees)
    logger.info("Training Main Model (HistGradientBoostingClassifier)...")
    base_tree_model = HistGradientBoostingClassifier(
        max_iter=180,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=25,
        l2_regularization=1.5,
        random_state=42,
        class_weight="balanced",
    )
    base_tree_model.fit(X_train, y_train)

    val_proba_uncal = base_tree_model.predict_proba(X_val)[:, 1]
    val_metrics_uncal = calculate_binary_metrics(y_val, val_proba_uncal, threshold=0.50)
    logger.info(f"Main Model (Uncalibrated) Validation: PR-AUC={val_metrics_uncal['pr_auc']}, ROC-AUC={val_metrics_uncal['roc_auc']}, Brier={val_metrics_uncal['brier_score']}")

    # 5. Probability Calibration on Validation Set
    logger.info("Calibrating Probabilities (Comparing Sigmoid vs Isotonic on Validation Split)...")
    # Platt Scaling (Sigmoid)
    calibrator_sigmoid = CalibratedClassifierCV(estimator=base_tree_model, method="sigmoid", cv="prefit")
    calibrator_sigmoid.fit(X_val, y_val)
    val_proba_sig = calibrator_sigmoid.predict_proba(X_val)[:, 1]
    brier_sig = brier_score_loss(y_val, val_proba_sig)

    # Isotonic Regression
    calibrator_iso = CalibratedClassifierCV(estimator=base_tree_model, method="isotonic", cv="prefit")
    calibrator_iso.fit(X_val, y_val)
    val_proba_iso = calibrator_iso.predict_proba(X_val)[:, 1]
    brier_iso = brier_score_loss(y_val, val_proba_iso)

    logger.info(f"Calibration Brier Scores: Uncalibrated={val_metrics_uncal['brier_score']:.4f}, Sigmoid={brier_sig:.4f}, Isotonic={brier_iso:.4f}")

    if brier_iso <= brier_sig:
        best_calibrator = calibrator_iso
        best_calib_method = "isotonic"
        val_proba_cal = val_proba_iso
    else:
        best_calibrator = calibrator_sigmoid
        best_calib_method = "sigmoid"
        val_proba_cal = val_proba_sig

    val_metrics_cal = calculate_binary_metrics(y_val, val_proba_cal, threshold=0.50)

    # 6. Threshold Optimization Analysis
    optimal_threshold, threshold_table = perform_threshold_analysis(y_val, val_proba_cal)
    val_metrics_optimal_th = calculate_binary_metrics(y_val, val_proba_cal, threshold=optimal_threshold)

    # 7. Stage 2 Multi-Class Reason Diagnosis Model
    logger.info("Training Stage-2 Multi-Class Failure Reason Classifier (on Failed Transactions Only)...")
    train_failed_mask = (train_df["payment_status"] == 1)
    val_failed_mask = (val_df["payment_status"] == 1)
    test_failed_mask = (test_df["payment_status"] == 1)

    X_train_failed = X_train[train_failed_mask]
    y_train_reason = train_df.loc[train_failed_mask, "failure_reason"].values

    X_val_failed = X_val[val_failed_mask]
    y_val_reason = val_df.loc[val_failed_mask, "failure_reason"].values

    X_test_failed = X_test[test_failed_mask]
    y_test_reason = test_df.loc[test_failed_mask, "failure_reason"].values

    reason_classes = sorted(list(set(y_train_reason)))
    logger.info(f"Training Reason Model on {len(X_train_failed):,} failed transactions across {len(reason_classes)} classes: {reason_classes}")

    reason_model = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=20,
        random_state=42,
    )
    reason_model.fit(X_train_failed, y_train_reason)

    val_reason_pred = reason_model.predict(X_val_failed)
    val_reason_acc = accuracy_score(y_val_reason, val_reason_pred)
    val_reason_f1 = f1_score(y_val_reason, val_reason_pred, average="macro")
    logger.info(f"Reason Model Validation: Accuracy={val_reason_acc:.4f}, Macro-F1={val_reason_f1:.4f}")

    # 8. Final Untouched Test Set Evaluation
    logger.info("Performing Final Evaluation on Untouched Out-of-Time Test Set...")
    test_proba_cal = best_calibrator.predict_proba(X_test)[:, 1]
    test_metrics_default = calculate_binary_metrics(y_test, test_proba_cal, threshold=0.50)
    test_metrics_optimal = calculate_binary_metrics(y_test, test_proba_cal, threshold=optimal_threshold)

    test_reason_pred = reason_model.predict(X_test_failed)
    test_reason_acc = accuracy_score(y_test_reason, test_reason_pred)
    test_reason_f1 = f1_score(y_test_reason, test_reason_pred, average="macro")

    logger.info("=== FINAL TEST METRICS ===")
    logger.info(f"Test PR-AUC: {test_metrics_optimal['pr_auc']:.4f} | Test ROC-AUC: {test_metrics_optimal['roc_auc']:.4f}")
    logger.info(f"Test Brier Score: {test_metrics_optimal['brier_score']:.4f} | Log-Loss: {test_metrics_optimal['log_loss']:.4f}")
    logger.info(f"Test F1 at optimal threshold ({optimal_threshold}): {test_metrics_optimal['f1_score']:.4f} (Precision: {test_metrics_optimal['precision']:.4f}, Recall: {test_metrics_optimal['recall']:.4f})")
    logger.info(f"Test Reason Diagnosis Accuracy: {test_reason_acc:.4f} (Macro-F1: {test_reason_f1:.4f})")

    # 9. Save Artifacts in models/
    joblib.dump(preprocessor, MODELS_DIR / "preprocessor.joblib")
    joblib.dump(base_tree_model, MODELS_DIR / "failure_model.joblib")
    joblib.dump(best_calibrator, MODELS_DIR / "calibrated_failure_model.joblib")
    joblib.dump(reason_model, MODELS_DIR / "reason_model.joblib")

    feature_metadata = {
        "feature_names": feature_names,
        "n_features": len(feature_names),
        "target_name": "payment_status",
        "optimal_threshold": optimal_threshold,
        "risk_tiers": {
            "LOW": {"min": 0.0, "max": 0.20},
            "MEDIUM": {"min": 0.20, "max": optimal_threshold},
            "HIGH": {"min": optimal_threshold, "max": 1.0},
        },
        "calibration_method": best_calib_method,
        "reason_classes": list(reason_model.classes_),
    }
    with open(MODELS_DIR / "feature_metadata.json", "w", encoding="utf-8") as f:
        json.dump(feature_metadata, f, indent=2)

    full_metrics = {
        "baseline_validation": val_metrics_base,
        "uncalibrated_validation": val_metrics_uncal,
        "calibrated_validation_default_thresh": val_metrics_cal,
        "calibrated_validation_optimal_thresh": val_metrics_optimal_th,
        "threshold_analysis": threshold_table,
        "reason_model_validation": {
            "accuracy": round(float(val_reason_acc), 4),
            "macro_f1": round(float(val_reason_f1), 4),
        },
        "final_test_evaluation": {
            "default_threshold_0.50": test_metrics_default,
            "optimal_threshold": test_metrics_optimal,
            "reason_diagnosis": {
                "accuracy": round(float(test_reason_acc), 4),
                "macro_f1": round(float(test_reason_f1), 4),
            },
        },
    }
    with open(MODELS_DIR / "model_metrics.json", "w", encoding="utf-8") as f:
        json.dump(full_metrics, f, indent=2)

    logger.info(f"All 6 production artifacts serialized successfully to {MODELS_DIR}.")
    return full_metrics


if __name__ == "__main__":
    train_and_evaluate_all()
