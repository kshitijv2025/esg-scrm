"""
ML prediction API routes — supplier risk scoring.

Endpoints:
  GET  /predict/{supplier_id}  — single supplier risk prediction
  GET  /predict                — batch prediction for all suppliers
  POST /train                  — submit feedback to adjust scoring weights
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, ADMIN_ROLES
from src.ml.risk_predictor import predict_supplier_risk, batch_predict, train_weights

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/predict/{supplier_id}")
def get_prediction(
    supplier_id: str,
    user: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Risk prediction for a single supplier.

    Returns risk_score (0-100), risk_level, factor breakdown, and recommendation.
    """
    org_id = user["org_id"]
    result = predict_supplier_risk(supplier_id, org_id=org_id)

    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])

    logger.info(
        "ml.predict supplier_id=%s risk_score=%s risk_level=%s",
        supplier_id, result["risk_score"], result["risk_level"],
    )
    return result


@router.get("/predict")
def get_batch_prediction(
    user: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Batch risk prediction for all suppliers, sorted by risk_score descending."""
    org_id = user["org_id"]
    results = batch_predict(org_id=org_id)

    summary = {
        "total": len(results),
        "by_level": {
            "critical": sum(1 for r in results if r.get("risk_level") == "critical"),
            "high": sum(1 for r in results if r.get("risk_level") == "high"),
            "medium": sum(1 for r in results if r.get("risk_level") == "medium"),
            "low": sum(1 for r in results if r.get("risk_level") == "low"),
        },
    }

    logger.info(
        "ml.batch_predict total=%d critical=%d high=%d medium=%d low=%d",
        summary["total"],
        summary["by_level"]["critical"],
        summary["by_level"]["high"],
        summary["by_level"]["medium"],
        summary["by_level"]["low"],
    )

    return {
        "summary": summary,
        "suppliers": results,
    }


@router.post("/train")
def post_train_feedback(
    feedback: list[dict[str, Any]],
    user: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Accept corrective feedback to adjust risk scoring weights. Requires admin role.

    Each entry should have:
      - supplier_id: str
      - expected_level: "low" | "medium" | "high" | "critical"
    """
    require_role(user, ADMIN_ROLES)

    if not feedback or not isinstance(feedback, list):
        raise HTTPException(
            status_code=400,
            detail="Request body must be a non-empty list of feedback entries",
        )

    for i, entry in enumerate(feedback):
        if not isinstance(entry, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Entry at index {i} must be a JSON object with supplier_id and expected_level",
            )
        if "supplier_id" not in entry or "expected_level" not in entry:
            raise HTTPException(
                status_code=400,
                detail=f"Entry at index {i} missing required fields: supplier_id, expected_level",
            )
        if entry["expected_level"] not in ("low", "medium", "high", "critical"):
            raise HTTPException(
                status_code=400,
                detail=f"Entry at index {i}: expected_level must be one of low, medium, high, critical",
            )

    result = train_weights(feedback)

    logger.info(
        "ml.train corrections=%d total_feedback=%d",
        result["corrections_applied"], result["total_feedback"],
    )

    return result
