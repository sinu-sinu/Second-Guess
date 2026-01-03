"""API endpoints for decision evaluation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.models.schemas import DecisionInput, DecisionResponse
from src.models.database import get_db
from src.services.decision_service import DecisionService

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])
decision_service = DecisionService()


@router.post("", response_model=DecisionResponse, status_code=201)
async def create_decision_evaluation(
    decision_input: DecisionInput,
    db: Session = Depends(get_db)
) -> DecisionResponse:
    """
    Evaluate a new decision.

    Runs the Context Analyzer agent and returns:
    - Decision ID and version
    - Context completeness analysis
    - Required vs provided context breakdown
    """
    try:
        return decision_service.evaluate_decision(decision_input, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{decision_id}/versions/{version}", response_model=DecisionResponse)
async def get_decision_evaluation(
    decision_id: str,
    version: int,
    db: Session = Depends(get_db)
) -> DecisionResponse:
    """
    Retrieve a specific decision evaluation by ID and version.
    """
    try:
        return decision_service.get_decision(decision_id, version, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
