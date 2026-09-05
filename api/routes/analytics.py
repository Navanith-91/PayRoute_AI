"""
Analytics and Aggregated Metrics Endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_db
from api.schemas import AnalyticsSummaryResponseSchema
from database.db_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger("AnalyticsRouter")
router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics & Reporting"])


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponseSchema,
    summary="Platform Analytics & Success Rate Metrics",
)
def get_analytics_summary(
    db: DatabaseManager = Depends(get_db),
) -> AnalyticsSummaryResponseSchema:
    """
    Returns aggregated platform metrics from SQLite, including:
    - Total, successful, and failed transaction counts.
    - Overall success and failure rates.
    - Mean transaction amounts and route latencies.
    - Total recorded routing decisions.
    """
    try:
        stats = db.get_transaction_statistics()
        return AnalyticsSummaryResponseSchema(**stats)
    except Exception as e:
        logger.error(f"Error querying analytics summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query analytics: {str(e)}",
        )
