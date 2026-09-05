"""
API Routes Aggregator.
"""

from fastapi import APIRouter

from api.routes.analytics import router as analytics_router
from api.routes.auth import router as auth_router
from api.routes.decision import router as decision_router
from api.routes.gateways import router as gateways_router
from api.routes.health import router as health_router
from api.routes.prediction import router as prediction_router
from api.routes.routing import router as routing_router
from api.routes.transaction import router as transaction_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(decision_router)
api_router.include_router(gateways_router)
api_router.include_router(health_router)
api_router.include_router(prediction_router)
api_router.include_router(routing_router)
api_router.include_router(transaction_router)
api_router.include_router(analytics_router)



