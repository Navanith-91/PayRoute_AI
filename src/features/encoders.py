"""
Custom Scikit-Learn compatible transformers for feature engineering in PayRoute AI.
"""

from typing import Any, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class CyclicTemporalTransformer(BaseEstimator, TransformerMixin):
    """
    Transforms cyclic temporal features (hour and day_of_week) into smooth sin and cos coordinates.
    """

    def __init__(self, hour_col: str = "hour", day_col: str = "day_of_week") -> None:
        self.hour_col = hour_col
        self.day_col = day_col
        self.feature_names_: List[str] = []

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Optional[Any] = None) -> "CyclicTemporalTransformer":
        self.feature_names_ = ["hour_sin", "hour_cos", "day_sin", "day_cos"]
        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            hours = X[self.hour_col].values.astype(float)
            days = X[self.day_col].values.astype(float)
        else:
            # Assume column 0 is hour, column 1 is day_of_week
            hours = X[:, 0].astype(float)
            days = X[:, 1].astype(float)

        hour_sin = np.sin(2.0 * np.pi * hours / 24.0)
        hour_cos = np.cos(2.0 * np.pi * hours / 24.0)
        day_sin = np.sin(2.0 * np.pi * days / 7.0)
        day_cos = np.cos(2.0 * np.pi * days / 7.0)

        return np.column_stack([hour_sin, hour_cos, day_sin, day_cos])

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        return np.array(self.feature_names_)


class CustomerBehaviorTransformer(BaseEstimator, TransformerMixin):
    """
    Computes causal historical customer metrics without using current transaction outcome.
    """

    def __init__(
        self,
        prev_tx_col: str = "previous_transactions",
        prev_fail_col: str = "previous_failed_transactions",
        attempts_col: str = "previous_attempts",
        velocity_col: str = "transaction_velocity",
        age_col: str = "customer_age_days",
    ) -> None:
        self.prev_tx_col = prev_tx_col
        self.prev_fail_col = prev_fail_col
        self.attempts_col = attempts_col
        self.velocity_col = velocity_col
        self.age_col = age_col
        self.feature_names_: List[str] = []

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Optional[Any] = None) -> "CustomerBehaviorTransformer":
        self.feature_names_ = [
            "historical_failure_rate",
            "retry_risk",
            "velocity_log",
            "account_maturity_years",
        ]
        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            prev_tx = X[self.prev_tx_col].values.astype(float)
            prev_fail = X[self.prev_fail_col].values.astype(float)
            attempts = X[self.attempts_col].values.astype(float)
            velocity = X[self.velocity_col].values.astype(float)
            age = X[self.age_col].values.astype(float)
        else:
            prev_tx = X[:, 0].astype(float)
            prev_fail = X[:, 1].astype(float)
            attempts = X[:, 2].astype(float)
            velocity = X[:, 3].astype(float)
            age = X[:, 4].astype(float)

        # Causal historical failure rate with Laplace smoothing to avoid 0/0 division
        historical_failure_rate = prev_fail / (prev_tx + 1.0)
        retry_risk = np.log1p(np.maximum(0.0, attempts))
        velocity_log = np.log1p(np.maximum(0.0, velocity))
        account_maturity_years = age / 365.0

        return np.column_stack([
            historical_failure_rate,
            retry_risk,
            velocity_log,
            account_maturity_years,
        ])

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        return np.array(self.feature_names_)


class InfrastructureHealthTransformer(BaseEstimator, TransformerMixin):
    """
    Transforms pre-transaction route latency and reliability metrics into composite signals.
    """

    def __init__(
        self,
        bank_lat_col: str = "bank_latency_ms",
        gw_lat_col: str = "gateway_latency_ms",
        bank_sr_col: str = "bank_success_rate",
        gw_sr_col: str = "gateway_success_rate",
    ) -> None:
        self.bank_lat_col = bank_lat_col
        self.gw_lat_col = gw_lat_col
        self.bank_sr_col = bank_sr_col
        self.gw_sr_col = gw_sr_col
        self.feature_names_: List[str] = []

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Optional[Any] = None) -> "InfrastructureHealthTransformer":
        self.feature_names_ = [
            "total_latency_ms",
            "latency_ratio",
            "combined_route_health",
            "health_deficit",
        ]
        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            b_lat = X[self.bank_lat_col].values.astype(float)
            g_lat = X[self.gw_lat_col].values.astype(float)
            b_sr = X[self.bank_sr_col].values.astype(float)
            g_sr = X[self.gw_sr_col].values.astype(float)
        else:
            b_lat = X[:, 0].astype(float)
            g_lat = X[:, 1].astype(float)
            b_sr = X[:, 2].astype(float)
            g_sr = X[:, 3].astype(float)

        total_latency = b_lat + g_lat
        latency_ratio = g_lat / np.maximum(10.0, b_lat)
        combined_health = np.clip(b_sr * g_sr, 0.0, 1.0)
        health_deficit = np.maximum(0.0, (1.0 - b_sr)) + np.maximum(0.0, (1.0 - g_sr))

        return np.column_stack([
            total_latency,
            latency_ratio,
            combined_health,
            health_deficit,
        ])

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        return np.array(self.feature_names_)


class AmountRiskTransformer(BaseEstimator, TransformerMixin):
    """
    Transforms transaction amount into log-scale and generates risk interaction flags.
    """

    def __init__(
        self,
        amount_col: str = "amount",
        new_device_col: str = "is_new_device",
        high_ticket_threshold: float = 10000.0,
    ) -> None:
        self.amount_col = amount_col
        self.new_device_col = new_device_col
        self.high_ticket_threshold = high_ticket_threshold
        self.feature_names_: List[str] = []

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Optional[Any] = None) -> "AmountRiskTransformer":
        self.feature_names_ = [
            "amount_log",
            "high_ticket_new_device",
        ]
        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            amount = X[self.amount_col].values.astype(float)
            new_dev = X[self.new_device_col].values.astype(float)
        else:
            amount = X[:, 0].astype(float)
            new_dev = X[:, 1].astype(float)

        amount_log = np.log1p(np.maximum(0.0, amount))
        high_ticket_new_device = ((amount >= self.high_ticket_threshold) & (new_dev == 1.0)).astype(float)

        return np.column_stack([amount_log, high_ticket_new_device])

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        return np.array(self.feature_names_)
