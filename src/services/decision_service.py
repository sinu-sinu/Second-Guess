"""Service layer for decision evaluation operations."""
from datetime import datetime
from sqlalchemy.orm import Session
import json

from src.models.schemas import DecisionInput, DecisionRun, DecisionResponse
from src.models.database import DecisionRunDB
from src.services.workflow import DecisionWorkflow


class DecisionService:
    """Service for managing decision evaluations."""

    def __init__(self):
        """Initialize decision service with workflow."""
        self.workflow = DecisionWorkflow()

    def _generate_decision_id(self, decision_type: str) -> str:
        """Generate unique decision ID in format: dec_YYYYMMDD_<type>"""
        timestamp = datetime.utcnow()
        date_str = timestamp.strftime("%Y%m%d")
        # Add time component for uniqueness within same day
        time_str = timestamp.strftime("%H%M%S")
        return f"dec_{date_str}_{decision_type}_{time_str}"

    def _get_next_version(self, db: Session, decision_id: str) -> int:
        """Get the next version number for a decision ID."""
        latest = db.query(DecisionRunDB).filter(
            DecisionRunDB.decision_id == decision_id
        ).order_by(DecisionRunDB.version.desc()).first()

        if latest:
            return latest.version + 1
        return 1

    def evaluate_decision(self, decision_input: DecisionInput, db: Session) -> DecisionResponse:
        """
        Evaluate a decision and store the result.

        Args:
            decision_input: The decision to evaluate
            db: Database session

        Returns:
            DecisionResponse with evaluation results
        """
        # Run workflow (Context Analyzer -> Proposer -> Devil's Advocate -> Judge)
        final_state = self.workflow.run(
            decision=decision_input.decision,
            context=decision_input.context
        )

        context_analysis = final_state["context_analysis"]
        proposer_output = final_state["proposer_output"]
        devils_advocate_output = final_state["devils_advocate_output"]
        judge_output = final_state["judge_output"]

        # Generate decision ID (new decision gets version 1)
        decision_id = self._generate_decision_id(context_analysis.decision_type)
        version = 1
        timestamp = datetime.utcnow()

        # Create decision run record
        decision_run = DecisionRun(
            decision_id=decision_id,
            version=version,
            timestamp=timestamp,
            decision=decision_input.decision,
            context_provided=decision_input.context,
            context_analysis=context_analysis,
            proposer_output=proposer_output,
            devils_advocate_output=devils_advocate_output,
            judge_output=judge_output
        )

        # Store in database
        db_record = DecisionRunDB(
            decision_id=decision_id,
            version=version,
            timestamp=timestamp,
            input_json=decision_input.model_dump_json(),
            output_json=decision_run.model_dump_json()
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        # Return response
        return DecisionResponse(
            decision_id=decision_run.decision_id,
            version=decision_run.version,
            timestamp=decision_run.timestamp,
            decision=decision_run.decision,
            context_provided=decision_run.context_provided,
            context_analysis=decision_run.context_analysis,
            proposer_output=decision_run.proposer_output,
            devils_advocate_output=decision_run.devils_advocate_output,
            judge_output=decision_run.judge_output,
            risk_breakdown=decision_run.devils_advocate_output.risk_breakdown if decision_run.devils_advocate_output else None
        )

    def get_decision(self, decision_id: str, version: int, db: Session) -> DecisionResponse:
        """Retrieve a specific decision evaluation."""
        record = db.query(DecisionRunDB).filter(
            DecisionRunDB.decision_id == decision_id,
            DecisionRunDB.version == version
        ).first()

        if not record:
            raise ValueError(f"Decision {decision_id} version {version} not found")

        decision_run = DecisionRun.model_validate_json(record.output_json)

        return DecisionResponse(
            decision_id=decision_run.decision_id,
            version=decision_run.version,
            timestamp=decision_run.timestamp,
            decision=decision_run.decision,
            context_provided=decision_run.context_provided,
            context_analysis=decision_run.context_analysis,
            proposer_output=decision_run.proposer_output,
            devils_advocate_output=decision_run.devils_advocate_output,
            judge_output=decision_run.judge_output,
            risk_breakdown=decision_run.devils_advocate_output.risk_breakdown if decision_run.devils_advocate_output else None
        )
