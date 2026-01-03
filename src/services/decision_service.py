"""Service layer for decision evaluation operations."""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List
import json

from src.models.schemas import (
    DecisionInput, DecisionRun, DecisionResponse,
    VersionComparison, VersionSummary, RiskDelta
)
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
        # Run workflow (Context Analyzer -> Proposer -> Devil's Advocate -> Judge -> Confidence Estimator)
        final_state = self.workflow.run(
            decision=decision_input.decision,
            context=decision_input.context
        )

        context_analysis = final_state["context_analysis"]
        proposer_output = final_state["proposer_output"]
        devils_advocate_output = final_state["devils_advocate_output"]
        judge_output = final_state["judge_output"]
        confidence_output = final_state["confidence_output"]
        final_recommendation = final_state["final_recommendation"]

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
            judge_output=judge_output,
            confidence_output=confidence_output,
            final_recommendation=final_recommendation
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
            confidence_output=decision_run.confidence_output,
            final_recommendation=decision_run.final_recommendation,
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
            confidence_output=decision_run.confidence_output,
            final_recommendation=decision_run.final_recommendation,
            risk_breakdown=decision_run.devils_advocate_output.risk_breakdown if decision_run.devils_advocate_output else None
        )

    def reevaluate_decision(
        self,
        decision_id: str,
        decision_input: DecisionInput,
        db: Session
    ) -> DecisionResponse:
        """
        Re-evaluate an existing decision with new context.

        Args:
            decision_id: The decision ID to re-evaluate
            decision_input: Updated decision input (must match original decision statement)
            db: Database session

        Returns:
            DecisionResponse with new version

        Raises:
            ValueError: If decision_id not found or decision statement doesn't match
        """
        # Get the latest version to verify decision exists and get decision statement
        latest_record = db.query(DecisionRunDB).filter(
            DecisionRunDB.decision_id == decision_id
        ).order_by(DecisionRunDB.version.desc()).first()

        if not latest_record:
            raise ValueError(f"Decision {decision_id} not found")

        # Parse the latest version to get the original decision statement
        latest_run = DecisionRun.model_validate_json(latest_record.output_json)

        # Verify decision statement matches (prevent changing the decision itself)
        if decision_input.decision != latest_run.decision:
            raise ValueError(
                f"Decision statement must match original. "
                f"Expected: '{latest_run.decision}', Got: '{decision_input.decision}'"
            )

        # Run workflow with updated context (fresh evaluation, no memory from previous)
        final_state = self.workflow.run(
            decision=decision_input.decision,
            context=decision_input.context
        )

        context_analysis = final_state["context_analysis"]
        proposer_output = final_state["proposer_output"]
        devils_advocate_output = final_state["devils_advocate_output"]
        judge_output = final_state["judge_output"]
        confidence_output = final_state["confidence_output"]
        final_recommendation = final_state["final_recommendation"]

        # Auto-increment version number
        next_version = self._get_next_version(db, decision_id)
        timestamp = datetime.utcnow()

        # Create decision run record for new version
        decision_run = DecisionRun(
            decision_id=decision_id,
            version=next_version,
            timestamp=timestamp,
            decision=decision_input.decision,
            context_provided=decision_input.context,
            context_analysis=context_analysis,
            proposer_output=proposer_output,
            devils_advocate_output=devils_advocate_output,
            judge_output=judge_output,
            confidence_output=confidence_output,
            final_recommendation=final_recommendation
        )

        # Store in database
        db_record = DecisionRunDB(
            decision_id=decision_id,
            version=next_version,
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
            confidence_output=decision_run.confidence_output,
            final_recommendation=decision_run.final_recommendation,
            risk_breakdown=decision_run.devils_advocate_output.risk_breakdown if decision_run.devils_advocate_output else None
        )

    def get_latest_decision(self, decision_id: str, db: Session) -> DecisionResponse:
        """Retrieve the latest version of a decision evaluation."""
        latest_record = db.query(DecisionRunDB).filter(
            DecisionRunDB.decision_id == decision_id
        ).order_by(DecisionRunDB.version.desc()).first()

        if not latest_record:
            raise ValueError(f"Decision {decision_id} not found")

        decision_run = DecisionRun.model_validate_json(latest_record.output_json)

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
            confidence_output=decision_run.confidence_output,
            final_recommendation=decision_run.final_recommendation,
            risk_breakdown=decision_run.devils_advocate_output.risk_breakdown if decision_run.devils_advocate_output else None
        )

    def get_all_versions(self, decision_id: str, db: Session) -> List[VersionSummary]:
        """Retrieve all versions of a decision as summaries."""
        records = db.query(DecisionRunDB).filter(
            DecisionRunDB.decision_id == decision_id
        ).order_by(DecisionRunDB.version.asc()).all()

        if not records:
            raise ValueError(f"Decision {decision_id} not found")

        summaries = []
        for record in records:
            decision_run = DecisionRun.model_validate_json(record.output_json)
            summaries.append(VersionSummary(
                version=decision_run.version,
                timestamp=decision_run.timestamp,
                context_completeness=decision_run.context_analysis.completeness_score,
                adjusted_confidence=decision_run.confidence_output.adjusted_confidence if decision_run.confidence_output else 0,
                final_recommendation=decision_run.final_recommendation or "N/A"
            ))

        return summaries

    def compare_versions(
        self,
        decision_id: str,
        v1: int,
        v2: int,
        db: Session
    ) -> VersionComparison:
        """
        Compare two versions of a decision.

        Args:
            decision_id: The decision ID
            v1: First version number
            v2: Second version number
            db: Database session

        Returns:
            VersionComparison with quantified deltas

        Raises:
            ValueError: If either version not found
        """
        # Retrieve both versions
        v1_record = db.query(DecisionRunDB).filter(
            DecisionRunDB.decision_id == decision_id,
            DecisionRunDB.version == v1
        ).first()

        v2_record = db.query(DecisionRunDB).filter(
            DecisionRunDB.decision_id == decision_id,
            DecisionRunDB.version == v2
        ).first()

        if not v1_record:
            raise ValueError(f"Decision {decision_id} version {v1} not found")
        if not v2_record:
            raise ValueError(f"Decision {decision_id} version {v2} not found")

        # Parse both versions
        v1_run = DecisionRun.model_validate_json(v1_record.output_json)
        v2_run = DecisionRun.model_validate_json(v2_record.output_json)

        # Calculate deltas
        context_completeness_delta = (
            v2_run.context_analysis.completeness_score -
            v1_run.context_analysis.completeness_score
        )

        confidence_delta = (
            (v2_run.confidence_output.adjusted_confidence if v2_run.confidence_output else 0) -
            (v1_run.confidence_output.adjusted_confidence if v1_run.confidence_output else 0)
        )

        # Calculate risk reduction (v2 - v1, negative means improvement)
        v1_risk = v1_run.devils_advocate_output.risk_breakdown if v1_run.devils_advocate_output else None
        v2_risk = v2_run.devils_advocate_output.risk_breakdown if v2_run.devils_advocate_output else None

        risk_reduction = RiskDelta(
            execution=(v2_risk.execution if v2_risk else 0) - (v1_risk.execution if v1_risk else 0),
            market_customer=(v2_risk.market_customer if v2_risk else 0) - (v1_risk.market_customer if v1_risk else 0),
            reputational=(v2_risk.reputational if v2_risk else 0) - (v1_risk.reputational if v1_risk else 0),
            opportunity_cost=(v2_risk.opportunity_cost if v2_risk else 0) - (v1_risk.opportunity_cost if v1_risk else 0)
        )

        # Determine which context items were resolved
        v1_missing = set(v1_run.context_analysis.missing_context)
        v2_missing = set(v2_run.context_analysis.missing_context)

        resolved_missing_context = list(v1_missing - v2_missing)
        remaining_missing_context = list(v2_missing & v1_missing)
        new_missing_context = list(v2_missing - v1_missing)

        return VersionComparison(
            decision_id=decision_id,
            v1=v1,
            v2=v2,
            context_completeness_delta=context_completeness_delta,
            confidence_delta=confidence_delta,
            risk_reduction=risk_reduction,
            resolved_missing_context=resolved_missing_context,
            remaining_missing_context=remaining_missing_context,
            new_missing_context=new_missing_context
        )
