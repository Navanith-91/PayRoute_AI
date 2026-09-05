"""
FastAPI Main Application Entrypoint for PayRoute AI.
Configures Lifespan Lifecycle Management, CORS Middleware, Error Handling, and OpenAPI Documentation.
"""

from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.dependencies import init_app_services
from api.routes import api_router
from src.utils.logger import get_logger

logger = get_logger("FastAPIApp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle context manager for FastAPI.
    Initializes database schema and loads ML model artifacts once at startup.
    """
    logger.info("Starting PayRoute AI FastAPI Application...")
    try:
        init_app_services()
        logger.info("PayRoute AI Application Startup Complete. Ready for traffic.")
    except Exception as e:
        logger.critical(f"Failed to initialize application services: {str(e)}", exc_info=True)
        raise e

    yield

    logger.info("Shutting down PayRoute AI FastAPI Application...")


def create_app() -> FastAPI:
    """Application factory for PayRoute AI."""
    app = FastAPI(
        title="PayRoute AI — Payment Failure Prediction & Smart Routing API",
        description=(
            "AI-Powered Payment Reliability and Dynamic Routing Platform. "
            "Evaluates multi-gateway routes, predicts calibrated failure probabilities, "
            "and optimizes payment success through dynamic 3-state circuit breakers."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Configure CORS for Streamlit Dashboard & Local Development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8501",  # Streamlit default
            "http://127.0.0.1:8501",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "*",  # Local dev fallback
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register API Routes
    app.include_router(api_router)

    # 3. Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Exception on {request.method} {request.url}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred while processing the request.",
                "path": str(request.url.path),
            },
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
