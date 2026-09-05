"""
Production Inference Wrapper for PayRoute AI.
Provides single-transaction prediction, risk tiering, failure reason diagnosis, and explanations.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd

from src.features.build_features import transform_single_transaction
from src.ml.explainer import PaymentExplainer
from src.utils.logger import get_logger

logger = get_logger("PaymentPredictor")

DEFAULT_MODELS_DIR = PROJECT_ROOT / "models"


class PaymentPredictor:
    """
    Unified real-time inference engine combining preprocessing, calibrated failure prediction,
    multi-class failure diagnosis, and local feature attribution.
    """

    def __init__(self, models_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Loads all required model artifacts and initializes the explainer.
        """
        if models_dir is None:
            self.models_dir = DEFAULT_MODELS_DIR
        else:
            self.models_dir = Path(models_dir)

        self._load_artifacts()
        self.explainer = PaymentExplainer(
            model=self.base_model,
            feature_names=self.metadata.get("feature_names", []),
        )

    def _load_artifacts(self) -> None:
        """Loads serialized model binaries and metadata from models/ directory."""
        preproc_path = self.models_dir / "preprocessor.joblib"
        calib_path = self.models_dir / "calibrated_failure_model.joblib"
        base_path = self.models_dir / "failure_model.joblib"
        reason_path = self.models_dir / "reason_model.joblib"
        meta_path = self.models_dir / "feature_metadata.json"

        if not all(p.exists() for p in [preproc_path, calib_path, reason_path, meta_path]):
            raise FileNotFoundError(
                f"Required model artifacts missing in {self.models_dir}. "
                "Please run python src/ml/train.py first."
            )

        self.preprocessor = joblib.load(preproc_path)
        self.calibrated_model = joblib.load(calib_path)
        self.base_model = joblib.load(base_path)
        self.reason_model = joblib.load(reason_path)

        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.optimal_threshold = float(self.metadata.get("optimal_threshold", 0.35))
        self.reason_classes = list(self.reason_model.classes_)
        logger.info(f"PaymentPredictor initialized successfully (Decision Threshold: {self.optimal_threshold:.2f}).")

    def predict_failure(
        self,
        transaction: Union[Dict[str, Any], np.ndarray],
    ) -> Dict[str, Any]:
        """
        Predicts calibrated probability of payment failure for a single transaction.

        Args:
            transaction: Dictionary of pre-transaction features or preprocessed 2D array.

        Returns:
            Dictionary containing failure_probability, success_probability, risk_level, and is_high_risk.
        """
        if isinstance(transaction, dict):
            X_vec = transform_single_transaction(transaction, self.preprocessor)
        else:
            X_vec = transaction

        p_fail = float(self.calibrated_model.predict_proba(X_vec)[0, 1])
        p_success = 1.0 - p_fail

        if p_fail < 0.20:
            risk_level = "LOW"
        elif p_fail < self.optimal_threshold:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        is_high_risk = bool(p_fail >= self.optimal_threshold)

        return {
            "failure_probability": round(p_fail, 4),
            "success_probability": round(p_success, 4),
            "is_high_risk": is_high_risk,
            "risk_level": risk_level,
            "decision_threshold": self.optimal_threshold,
        }

    def predict_failure_reason(
        self,
        transaction: Union[Dict[str, Any], np.ndarray],
    ) -> Dict[str, Any]:
        """
        Predicts most probable failure cause and category distribution if failure occurs.

        Args:
            transaction: Dictionary of pre-transaction features or preprocessed 2D array.

        Returns:
            Dictionary with predicted_reason and probability distribution across all 5 classes.
        """
        if isinstance(transaction, dict):
            X_vec = transform_single_transaction(transaction, self.preprocessor)
        else:
            X_vec = transaction

        reason_probs = self.reason_model.predict_proba(X_vec)[0]
        predicted_idx = int(np.argmax(reason_probs))
        predicted_reason = str(self.reason_classes[predicted_idx])

        reason_dist = {
            cls_name: round(float(prob), 4)
            for cls_name, prob in zip(self.reason_classes, reason_probs)
        }

        return {
            "predicted_reason": predicted_reason,
            "reason_probabilities": reason_dist,
        }

    def explain(
        self,
        transaction: Union[Dict[str, Any], np.ndarray],
        top_k: int = 4,
    ) -> Dict[str, Any]:
        """
        Returns top risk-increasing and protective feature contributions for a transaction.
        """
        if isinstance(transaction, dict):
            X_vec = transform_single_transaction(transaction, self.preprocessor)
        else:
            X_vec = transaction

        p_fail = float(self.calibrated_model.predict_proba(X_vec)[0, 1])
        return self.explainer.explain_instance(X_vec, predicted_probability=p_fail, top_k=top_k)

    def evaluate_full_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combined high-speed inference pipeline returning failure risk, reason diagnostic, and explanation.
        Single vectorized transform executes in <5ms.
        """
        X_vec = transform_single_transaction(transaction, self.preprocessor)
        risk_res = self.predict_failure(X_vec)
        reason_res = self.predict_failure_reason(X_vec)
        explanation = self.explain(X_vec, top_k=4)

        return {
            "risk_assessment": risk_res,
            "failure_diagnosis": reason_res,
            "explanation": explanation,
        }
