"""
Dependency Injection Providers for FastAPI Backend.
Maintains singleton instances of DatabaseManager, PaymentPredictor, and SmartRouter.
"""

from pathlib import Path
from typing import Optional, Union

from database.db_manager import DatabaseManager
from src.ml.predictor import PaymentPredictor
from src.router.router import SmartRouter
from src.utils.logger import get_logger

logger = get_logger("APIDependencies")

_db_manager: Optional[DatabaseManager] = None
_payment_predictor: Optional[PaymentPredictor] = None
_smart_router: Optional[SmartRouter] = None


def init_app_services(
    db_path: Optional[Union[str, Path]] = None,
    models_dir: Optional[Union[str, Path]] = None,
    routes_config_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Initializes application dependencies during FastAPI lifespan startup.
    Loads models and database connection ONCE to eliminate per-request overhead.
    """
    global _db_manager, _payment_predictor, _smart_router

    logger.info("Initializing PayRoute AI Backend Services...")

    # 1. Initialize Database
    _db_manager = DatabaseManager(db_path=str(db_path) if db_path else None)
    _db_manager.initialize_schema()
    _db_manager.seed_initial_entities()

    # 2. Initialize ML Predictor (Loads 6 serialized model artifacts)
    _payment_predictor = PaymentPredictor(models_dir=models_dir)

    # 3. Initialize SmartRouter
    _smart_router = SmartRouter(
        config_path=routes_config_path,
        models_dir=models_dir,
        random_seed=42,
    )

    logger.info("All Backend Services (Database, ML Predictor, SmartRouter) initialized successfully.")


def get_db() -> DatabaseManager:
    """Dependency provider for DatabaseManager."""
    global _db_manager
    if _db_manager is None or not Path(_db_manager.db_path).exists():
        _db_manager = DatabaseManager()
        _db_manager.initialize_schema()
    return _db_manager



def get_predictor() -> PaymentPredictor:
    """Dependency provider for PaymentPredictor."""
    global _payment_predictor
    if _payment_predictor is None:
        _payment_predictor = PaymentPredictor()
    return _payment_predictor


def get_router() -> SmartRouter:
    """Dependency provider for SmartRouter."""
    global _smart_router
    if _smart_router is None:
        _smart_router = SmartRouter()
    return _smart_router
