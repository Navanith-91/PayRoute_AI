"""
Statistical distributions, hazard curves, and probabilistic utilities for synthetic payment generation.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np


def sample_diurnal_hours(
    num_samples: int,
    random_state: Optional[np.random.RandomState] = None,
) -> np.ndarray:
    """
    Generates realistic 24-hour transaction distribution with morning and evening peaks.
    Peak volumes: 10:00-13:00 (workday morning) and 19:00-22:00 (evening leisure/shopping).
    Lull volume: 01:00-06:00 (night time).
    """
    rng = random_state if random_state is not None else np.random.RandomState()
    
    # 24-hour hourly probability density (unnormalized)
    hourly_weights = np.array([
        0.010, 0.006, 0.004, 0.003, 0.004, 0.008,  # 00:00 - 05:00 (Night lull)
        0.018, 0.035, 0.055, 0.075, 0.082, 0.080,  # 06:00 - 11:00 (Morning surge)
        0.076, 0.065, 0.058, 0.055, 0.060, 0.070,  # 12:00 - 17:00 (Afternoon)
        0.085, 0.092, 0.088, 0.070, 0.040, 0.020,  # 18:00 - 23:00 (Evening peak)
    ])
    hourly_probs = hourly_weights / hourly_weights.sum()
    
    return rng.choice(np.arange(24), size=num_samples, p=hourly_probs)


def sample_day_of_week(
    num_samples: int,
    random_state: Optional[np.random.RandomState] = None,
) -> np.ndarray:
    """
    Generates day of week (0=Monday, 6=Sunday) with slightly higher Friday-Sunday weekend volumes.
    """
    rng = random_state if random_state is not None else np.random.RandomState()
    day_weights = np.array([0.13, 0.13, 0.13, 0.14, 0.16, 0.16, 0.15])
    day_probs = day_weights / day_weights.sum()
    return rng.choice(np.arange(7), size=num_samples, p=day_probs)


def sample_amounts_by_category(
    categories: np.ndarray,
    amount_params: Dict[str, Dict[str, float]],
    random_state: Optional[np.random.RandomState] = None,
) -> np.ndarray:
    """
    Generates strictly positive log-normally distributed transaction amounts parameterized by merchant category.
    """
    rng = random_state if random_state is not None else np.random.RandomState()
    amounts = np.zeros(len(categories), dtype=np.float64)

    for cat_name, params in amount_params.items():
        mask = (categories == cat_name)
        count = np.sum(mask)
        if count > 0:
            mu = params["mu"]
            sigma = params["sigma"]
            sampled = rng.lognormal(mean=mu, sigma=sigma, size=count)
            # Clip between minimum sensible amount (₹1.00) and maximum (₹200,000)
            sampled = np.clip(sampled, 1.0, 200000.0)
            amounts[mask] = np.round(sampled, 2)

    return amounts


def sample_latencies(
    baselines: np.ndarray,
    degradation_factors: np.ndarray,
    network_adders: np.ndarray,
    random_state: Optional[np.random.RandomState] = None,
) -> np.ndarray:
    """
    Generates strictly positive latency values with heavy right tails (Gamma distributed)
    incorporating baseline provider latency, outage degradation, and client network latency.
    """
    rng = random_state if random_state is not None else np.random.RandomState()
    shape = 3.0  # Gamma shape parameter
    scale = baselines / shape
    
    noise = rng.gamma(shape=shape, scale=scale, size=len(baselines))
    latencies = noise * degradation_factors + network_adders
    
    # Ensure minimum latency of 10ms and round to integer
    return np.maximum(10.0, np.round(latencies)).astype(int)


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """
    Numerically stable Softmax calculation across rows of a 2D array.
    """
    scaled = logits / max(temperature, 1e-4)
    exp_shifted = np.exp(scaled - np.max(scaled, axis=1, keepdims=True))
    return exp_shifted / np.sum(exp_shifted, axis=1, keepdims=True)


def sigmoid(z: np.ndarray) -> np.ndarray:
    """
    Numerically stable sigmoid function.
    """
    return 1.0 / (1.0 + np.exp(-np.clip(z, -25.0, 25.0)))
