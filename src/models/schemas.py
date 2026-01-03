"""Pydantic schemas for Second Guess decision evaluation system."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DecisionInput(BaseModel):
    """Input schema for decision submission."""
    decision: str = Field(..., description="The decision statement to evaluate")
    context: Optional[str] = Field(None, description="Optional context provided by user")


class ContextAnalysis(BaseModel):
    """Output schema for Context Analyzer agent."""
    decision_type: str = Field(..., description="Type of decision: launch, pricing, hiring, technical, market_entry")
    required_context: List[str] = Field(..., description="List of context dimensions required for this decision type")
    provided_context: List[str] = Field(..., description="Context dimensions identified in user input")
    missing_context: List[str] = Field(..., description="Required context not provided by user")
    completeness_score: int = Field(..., ge=0, le=100, description="Context completeness score (0-100)")


class Assumption(BaseModel):
    """Schema for an assumption made by the Proposer."""
    statement: str = Field(..., description="The assumption being made")
    basis: str = Field(..., description="What context or reasoning this assumption is based on")
    risk_level: str = Field(..., description="Risk if assumption is wrong: low, medium, high")


class ProposerOutput(BaseModel):
    """Output schema for Proposer agent."""
    recommendation: str = Field(..., description="Clear directive: proceed, delay, or conditional")
    assumptions: List[Assumption] = Field(..., description="List of assumptions being made")
    confidence: int = Field(..., ge=0, le=100, description="Confidence level in this recommendation (0-100)")
    justification: str = Field(..., description="Reasoning for the recommendation based on provided context")


class DecisionRun(BaseModel):
    """Complete decision evaluation run record."""
    decision_id: str = Field(..., description="Unique decision identifier (dec_YYYYMMDD_<type>)")
    version: int = Field(..., description="Version number of this evaluation")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Evaluation timestamp")
    decision: str = Field(..., description="The decision statement")
    context_provided: Optional[str] = Field(None, description="User-provided context")
    context_analysis: ContextAnalysis = Field(..., description="Context analysis output")
    proposer_output: Optional[ProposerOutput] = Field(None, description="Proposer recommendation output")

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "dec_20250103_launch",
                "version": 1,
                "timestamp": "2025-01-03T14:32:00Z",
                "decision": "Can we launch this week?",
                "context_provided": "Auth service is stable",
                "context_analysis": {
                    "decision_type": "launch",
                    "required_context": [
                        "deployment readiness",
                        "rollback plan",
                        "auth service stability",
                        "customer impact analysis"
                    ],
                    "provided_context": ["auth service stability"],
                    "missing_context": [
                        "deployment readiness",
                        "rollback plan",
                        "customer impact analysis"
                    ],
                    "completeness_score": 32
                }
            }
        }


class DecisionResponse(BaseModel):
    """API response for decision submission."""
    decision_id: str
    version: int
    timestamp: datetime
    decision: str
    context_provided: Optional[str]
    context_analysis: ContextAnalysis
    proposer_output: Optional[ProposerOutput] = Field(None, description="Proposer recommendation output")
