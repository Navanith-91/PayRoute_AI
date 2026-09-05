"""
Centralized logging configuration for PayRoute AI.
"""

import logging
import sys
from typing import Optional


def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Creates or retrieves a standardized logger with consistent formatting.

    Args:
        name: Name of the logger, typically __name__.
        level: Logging level (e.g. logging.INFO, logging.DEBUG).

    Returns:
        Configured logging.Logger instance.
    """
    logger_name = name if name else "payroute_ai"
    logger = logging.getLogger(logger_name)

    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger
