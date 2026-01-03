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


class FailureScenario(BaseModel):
    """Schema for a specific failure scenario."""
    description: str = Field(..., description="Specific failure scenario description")
    trigger: str = Field(..., description="What would trigger this failure")
    impact_severity: str = Field(..., description="Severity of impact: low, medium, high, critical")


class RiskBreakdown(BaseModel):
    """Schema for risk assessment across four dimensions."""
    execution: int = Field(..., ge=0, le=10, description="Execution risk: what could fail technically (0-10)")
    market_customer: int = Field(..., ge=0, le=10, description="Market & customer impact: who gets hurt (0-10)")
    reputational: int = Field(..., ge=0, le=10, description="Reputational downside: public failure narrative (0-10)")
    opportunity_cost: int = Field(..., ge=0, le=10, description="Opportunity cost: what else could be done (0-10)")


class DevilsAdvocateOutput(BaseModel):
    """Output schema for Devil's Advocate agent."""
    counterarguments: List[str] = Field(..., description="Arguments challenging the Proposer's recommendation")
    failure_scenarios: List[FailureScenario] = Field(..., description="Specific failure scenarios with triggers")
    high_risk_assumptions: List[str] = Field(..., description="Unverified assumptions flagged as high-risk")
    risk_breakdown: RiskBreakdown = Field(..., description="Risk assessment across four dimensions")


class WeakClaim(BaseModel):
    """Schema for a weak or poorly supported claim."""
    source: str = Field(..., description="Source of claim: proposer or advocate")
    claim: str = Field(..., description="The weak claim statement")
    weakness_reason: str = Field(..., description="Why this claim is weak (vague, generic, illogical)")


class UnsupportedClaim(BaseModel):
    """Schema for a claim not backed by provided context."""
    source: str = Field(..., description="Source of claim: proposer or advocate")
    claim: str = Field(..., description="The unsupported claim statement")
    missing_evidence: str = Field(..., description="What evidence is missing to support this claim")


class JudgeOutput(BaseModel):
    """Output schema for Judge agent."""
    proposer_strength: int = Field(..., ge=0, le=10, description="Reasoning quality of Proposer (0-10)")
    advocate_strength: int = Field(..., ge=0, le=10, description="Reasoning quality of Devil's Advocate (0-10)")
    weak_claims: List[WeakClaim] = Field(..., description="Weak or vague claims identified")
    unsupported_claims: List[UnsupportedClaim] = Field(..., description="Claims not backed by provided context")
    reasoning_assessment: str = Field(..., description="Overall assessment of reasoning quality from both sides")


class ConfidencePenalty(BaseModel):
    """Schema for a confidence penalty."""
    reason: str = Field(..., description="Human-readable reason for this penalty")
    percentage_impact: int = Field(..., ge=0, le=100, description="Percentage points deducted from confidence")


class ConfidenceImprovement(BaseModel):
    """Schema for a confidence improvement (for v2+ comparisons)."""
    reason: str = Field(..., description="Human-readable reason for this improvement")
    percentage_impact: int = Field(..., ge=0, le=100, description="Percentage points added to confidence")


class ConfidenceOutput(BaseModel):
    """Output schema for Confidence Estimator."""
    initial_confidence: int = Field(..., ge=0, le=100, description="Initial confidence from Proposer (0-100)")
    adjusted_confidence: int = Field(..., ge=0, le=100, description="Adjusted confidence after penalties (0-100)")
    delta: int = Field(..., description="Change in confidence (negative for penalties, positive for improvements)")
    penalties: List[ConfidencePenalty] = Field(..., description="List of confidence penalties applied")
    improvements: List[ConfidenceImprovement] = Field(default_factory=list, description="List of confidence improvements (for v2+ comparisons)")


class DecisionRun(BaseModel):
    """Complete decision evaluation run record."""
    decision_id: str = Field(..., description="Unique decision identifier (dec_YYYYMMDD_<type>)")
    version: int = Field(..., description="Version number of this evaluation")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Evaluation timestamp")
    decision: str = Field(..., description="The decision statement")
    context_provided: Optional[str] = Field(None, description="User-provided context")
    context_analysis: ContextAnalysis = Field(..., description="Context analysis output")
    proposer_output: Optional[ProposerOutput] = Field(None, description="Proposer recommendation output")
    devils_advocate_output: Optional[DevilsAdvocateOutput] = Field(None, description="Devil's Advocate critique output")
    judge_output: Optional[JudgeOutput] = Field(None, description="Judge evaluation output")
    confidence_output: Optional[ConfidenceOutput] = Field(None, description="Confidence estimation output")
    final_recommendation: Optional[str] = Field(None, description="Final recommendation: PROCEED, CONDITIONAL, or DELAY")

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
    devils_advocate_output: Optional[DevilsAdvocateOutput] = Field(None, description="Devil's Advocate critique output")
    judge_output: Optional[JudgeOutput] = Field(None, description="Judge evaluation output")
    confidence_output: Optional[ConfidenceOutput] = Field(None, description="Confidence estimation output")
    final_recommendation: Optional[str] = Field(None, description="Final recommendation: PROCEED, CONDITIONAL, or DELAY")
    risk_breakdown: Optional[RiskBreakdown] = Field(None, description="Risk breakdown across dimensions")


class RiskDelta(BaseModel):
    """Schema for risk reduction across dimensions."""
    execution: int = Field(..., description="Change in execution risk (negative = improvement)")
    market_customer: int = Field(..., description="Change in market & customer risk (negative = improvement)")
    reputational: int = Field(..., description="Change in reputational risk (negative = improvement)")
    opportunity_cost: int = Field(..., description="Change in opportunity cost risk (negative = improvement)")


class VersionComparison(BaseModel):
    """Schema for comparing two decision versions."""
    decision_id: str = Field(..., description="The decision being compared")
    v1: int = Field(..., description="First version number")
    v2: int = Field(..., description="Second version number")
    context_completeness_delta: int = Field(..., description="Change in context completeness (v2 - v1)")
    confidence_delta: int = Field(..., description="Change in adjusted confidence (v2 - v1)")
    risk_reduction: RiskDelta = Field(..., description="Risk reduction per dimension (v2 - v1, negative = improvement)")
    resolved_missing_context: List[str] = Field(..., description="Context items that were missing in v1 but provided in v2")
    remaining_missing_context: List[str] = Field(..., description="Context items still missing in v2")
    new_missing_context: List[str] = Field(..., description="Context items missing in v2 but not in v1 (decision evolved)")


class VersionSummary(BaseModel):
    """Summary information for a decision version."""
    version: int
    timestamp: datetime
    context_completeness: int = Field(..., description="Context completeness score (0-100)")
    adjusted_confidence: int = Field(..., description="Adjusted confidence (0-100)")
    final_recommendation: str = Field(..., description="Final recommendation: PROCEED, CONDITIONAL, or DELAY")
