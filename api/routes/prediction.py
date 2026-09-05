"""
Machine Learning Payment Failure Prediction Endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_predictor
from api.schemas import PaymentContextInput, PredictionResponseSchema
from src.ml.predictor import PaymentPredictor
from src.utils.logger import get_logger

logger = get_logger("PredictionRouter")
router = APIRouter(prefix="/api/v1/predict", tags=["ML Prediction"])


@router.post(
    "/failure",
    response_model=PredictionResponseSchema,
    summary="Predict Payment Failure Risk & Diagnosis",
    status_code=status.HTTP_200_OK,
)
def predict_payment_failure(
    payload: PaymentContextInput,
    predictor: PaymentPredictor = Depends(get_predictor),
) -> PredictionResponseSchema:
    """
    Evaluates an incoming payment request using the calibrated Stage-1 Gradient Boosted Decision Tree
    and Stage-2 Failure Reason Diagnoser.

    Returns:
    - **failure_probability**: Calibrated posterior $P(\\text{Fail}) \\in [0, 1]$.
    - **success_probability**: $1.0 - P(\\text{Fail})$.
    - **risk_level**: Categorical risk classification (`LOW`, `MEDIUM`, `HIGH`).
    - **predicted_failure_reason**: Most probable root cause if failure occurs.
    - **top_risk_factors**: Top features increasing failure risk.
    - **top_protective_factors**: Top features decreasing failure risk.
    """
    try:
        data = payload.to_dict()
        res = predictor.evaluate_full_transaction(data)

        risk = res["risk_assessment"]
        diag = res["failure_diagnosis"]
        expl = res.get("explanation", {})

        return PredictionResponseSchema(
            transaction_id=data["transaction_id"],
            failure_probability=risk["failure_probability"],
            success_probability=risk["success_probability"],
            risk_level=risk["risk_level"],
            is_high_risk=risk["is_high_risk"],
            decision_threshold=risk["decision_threshold"],
            predicted_failure_reason=diag["predicted_reason"],
            reason_probabilities=diag["reason_probabilities"],
            top_risk_factors=expl.get("top_risk_contributors", []),
            top_protective_factors=expl.get("top_protective_factors", []),
        )
    except Exception as e:
        logger.error(f"Error during failure prediction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction engine error: {str(e)}",
        )
