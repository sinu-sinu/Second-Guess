"""Confidence Estimator agent implementation."""
from typing import List
from src.models.schemas import (
    ConfidenceOutput, ConfidencePenalty, ConfidenceImprovement,
    ContextAnalysis, ProposerOutput, DevilsAdvocateOutput, JudgeOutput
)


class ConfidenceEstimatorAgent:
    """Agent that calculates adjusted confidence with explicit penalties."""

    def __init__(self):
        """Initialize the Confidence Estimator."""
        pass

    def estimate(
        self,
        context_analysis: ContextAnalysis,
        proposer_output: ProposerOutput,
        devils_advocate_output: DevilsAdvocateOutput,
        judge_output: JudgeOutput
    ) -> ConfidenceOutput:
        """
        Calculate adjusted confidence with explicit penalties.

        Args:
            context_analysis: Output from Context Analyzer
            proposer_output: Output from Proposer Agent
            devils_advocate_output: Output from Devil's Advocate Agent
            judge_output: Output from Judge Agent

        Returns:
            ConfidenceOutput with initial/adjusted confidence and penalties
        """
        initial_confidence = proposer_output.confidence
        penalties: List[ConfidencePenalty] = []

        # Penalty 1: Missing context items
        penalties.extend(self._calculate_missing_context_penalties(context_analysis))

        # Penalty 2: Unsupported claims from Judge
        penalties.extend(self._calculate_unsupported_claim_penalties(judge_output))

        # Penalty 3: High-risk assumptions
        penalties.extend(self._calculate_high_risk_assumption_penalties(
            proposer_output, devils_advocate_output
        ))

        # Penalty 4: Weak claims from Judge
        penalties.extend(self._calculate_weak_claim_penalties(judge_output))

        # Penalty 5: Severe execution risks
        penalties.extend(self._calculate_execution_risk_penalties(devils_advocate_output))

        # Calculate adjusted confidence
        total_penalty = sum(p.percentage_impact for p in penalties)
        adjusted_confidence = max(0, min(100, initial_confidence - total_penalty))
        delta = adjusted_confidence - initial_confidence

        return ConfidenceOutput(
            initial_confidence=initial_confidence,
            adjusted_confidence=adjusted_confidence,
            delta=delta,
            penalties=penalties,
            improvements=[]  # For v2+ comparisons
        )

    def _calculate_missing_context_penalties(
        self,
        context_analysis: ContextAnalysis
    ) -> List[ConfidencePenalty]:
        """Calculate penalties for missing context items."""
        penalties = []

        for missing_item in context_analysis.missing_context:
            # Critical missing context: -15% to -20% per item
            # Use completeness score to determine severity
            if context_analysis.completeness_score < 30:
                # Extremely low context - higher penalty
                penalty = 20
            elif context_analysis.completeness_score < 50:
                # Low context - high penalty
                penalty = 15
            else:
                # Moderate context - medium penalty
                penalty = 10

            penalties.append(ConfidencePenalty(
                reason=f"Missing critical context: {missing_item}",
                percentage_impact=penalty
            ))

        return penalties

    def _calculate_unsupported_claim_penalties(
        self,
        judge_output: JudgeOutput
    ) -> List[ConfidencePenalty]:
        """Calculate penalties for unsupported claims from Proposer."""
        penalties = []

        # Only penalize unsupported claims from the Proposer
        proposer_unsupported = [
            claim for claim in judge_output.unsupported_claims
            if claim.source == "proposer"
        ]

        for claim in proposer_unsupported:
            # Unsupported claim: -8% per claim
            penalties.append(ConfidencePenalty(
                reason=f"Unsupported claim: {claim.claim[:60]}... (missing: {claim.missing_evidence[:40]}...)",
                percentage_impact=8
            ))

        return penalties

    def _calculate_high_risk_assumption_penalties(
        self,
        proposer_output: ProposerOutput,
        devils_advocate_output: DevilsAdvocateOutput
    ) -> List[ConfidencePenalty]:
        """Calculate penalties for high-risk assumptions."""
        penalties = []

        # Check which of Proposer's assumptions were flagged as high-risk by Devil's Advocate
        for assumption in proposer_output.assumptions:
            if assumption.risk_level == "high":
                # Check if flagged by Devil's Advocate
                flagged = any(
                    assumption.statement.lower() in hra.lower()
                    for hra in devils_advocate_output.high_risk_assumptions
                )

                if flagged:
                    # High-risk assumption flagged by both: -12%
                    penalties.append(ConfidencePenalty(
                        reason=f"High-risk unverified assumption: {assumption.statement[:60]}...",
                        percentage_impact=12
                    ))
                else:
                    # High-risk but not flagged: -6%
                    penalties.append(ConfidencePenalty(
                        reason=f"High-risk assumption: {assumption.statement[:60]}...",
                        percentage_impact=6
                    ))

        return penalties

    def _calculate_weak_claim_penalties(
        self,
        judge_output: JudgeOutput
    ) -> List[ConfidencePenalty]:
        """Calculate penalties for weak claims from Proposer."""
        penalties = []

        # Only penalize weak claims from the Proposer
        proposer_weak = [
            claim for claim in judge_output.weak_claims
            if claim.source == "proposer"
        ]

        for claim in proposer_weak:
            # Weak claim (vague, generic): -5% per claim
            penalties.append(ConfidencePenalty(
                reason=f"Weak/vague claim: {claim.claim[:60]}... ({claim.weakness_reason[:40]}...)",
                percentage_impact=5
            ))

        return penalties

    def _calculate_execution_risk_penalties(
        self,
        devils_advocate_output: DevilsAdvocateOutput
    ) -> List[ConfidencePenalty]:
        """Calculate penalties for severe execution risks."""
        penalties = []

        execution_risk = devils_advocate_output.risk_breakdown.execution

        # Execution risk threshold penalties
        if execution_risk >= 8:
            # Critical execution risk (8-10): -15%
            penalties.append(ConfidencePenalty(
                reason=f"Critical execution risk level ({execution_risk}/10)",
                percentage_impact=15
            ))
        elif execution_risk >= 6:
            # High execution risk (6-7): -8%
            penalties.append(ConfidencePenalty(
                reason=f"High execution risk level ({execution_risk}/10)",
                percentage_impact=8
            ))

        return penalties

    def generate_final_recommendation(
        self,
        confidence_output: ConfidenceOutput,
        proposer_output: ProposerOutput,
        devils_advocate_output: DevilsAdvocateOutput,
        context_analysis: ContextAnalysis
    ) -> str:
        """
        Generate final recommendation based on adjusted confidence.

        Recommendation thresholds:
        - <40%: DELAY with specific blockers listed
        - 40-70%: CONDITIONAL with requirements listed
        - >70%: PROCEED with monitoring recommendations

        Args:
            confidence_output: Confidence estimation output
            proposer_output: Proposer recommendation output
            devils_advocate_output: Devil's Advocate critique output
            context_analysis: Context analysis output

        Returns:
            Final recommendation string with actionable next steps
        """
        adjusted_confidence = confidence_output.adjusted_confidence

        if adjusted_confidence < 40:
            # DELAY - identify blockers
            blockers = []

            # Add missing critical context as blockers
            if context_analysis.missing_context:
                for missing in context_analysis.missing_context[:3]:  # Top 3
                    blockers.append(f"Gather missing context: {missing}")

            # Add high-risk assumptions as blockers
            high_risk_assumptions = [
                a.statement for a in proposer_output.assumptions
                if a.risk_level == "high"
            ]
            for assumption in high_risk_assumptions[:2]:  # Top 2
                blockers.append(f"Verify assumption: {assumption}")

            # Add critical failure scenarios as blockers
            critical_scenarios = [
                fs for fs in devils_advocate_output.failure_scenarios
                if fs.impact_severity == "critical"
            ]
            for scenario in critical_scenarios[:2]:  # Top 2
                blockers.append(f"Mitigate risk: {scenario.description}")

            blockers_text = "\n".join(f"  - {b}" for b in blockers[:5])  # Max 5 blockers

            return f"""DELAY

Adjusted confidence ({adjusted_confidence}%) is too low to proceed. Address these blockers first:

{blockers_text}

Once these blockers are resolved, re-evaluate the decision with updated context."""

        elif adjusted_confidence < 70:
            # CONDITIONAL - identify requirements
            requirements = []

            # Add missing context as requirements
            if context_analysis.missing_context:
                requirements.append(f"Obtain {', '.join(context_analysis.missing_context[:2])}")

            # Add high-risk assumptions as requirements
            high_risk_assumptions = [
                a.statement for a in proposer_output.assumptions
                if a.risk_level == "high"
            ]
            if high_risk_assumptions:
                requirements.append(f"Validate assumptions: {high_risk_assumptions[0][:50]}...")

            # Add mitigation requirements for high-severity failures
            high_severity_scenarios = [
                fs for fs in devils_advocate_output.failure_scenarios
                if fs.impact_severity in ["high", "critical"]
            ]
            if high_severity_scenarios:
                requirements.append(f"Prepare mitigation for: {high_severity_scenarios[0].description[:50]}...")

            requirements_text = "\n".join(f"  - {r}" for r in requirements[:5])  # Max 5 requirements

            return f"""CONDITIONAL PROCEED

Adjusted confidence ({adjusted_confidence}%) suggests proceeding with caution. Required conditions:

{requirements_text}

Monitor execution closely and be prepared to rollback if issues arise."""

        else:
            # PROCEED - provide monitoring recommendations
            monitoring_items = []

            # Monitor any medium-risk assumptions
            medium_risk_assumptions = [
                a.statement for a in proposer_output.assumptions
                if a.risk_level == "medium"
            ]
            if medium_risk_assumptions:
                monitoring_items.append(f"Monitor assumption: {medium_risk_assumptions[0][:60]}...")

            # Monitor top failure scenarios
            if devils_advocate_output.failure_scenarios:
                top_scenario = devils_advocate_output.failure_scenarios[0]
                monitoring_items.append(f"Watch for: {top_scenario.description[:60]}...")

            # Monitor high-risk dimensions
            risk_breakdown = devils_advocate_output.risk_breakdown
            if risk_breakdown.execution >= 5:
                monitoring_items.append(f"Monitor execution closely (risk: {risk_breakdown.execution}/10)")
            if risk_breakdown.reputational >= 6:
                monitoring_items.append(f"Monitor public perception (risk: {risk_breakdown.reputational}/10)")

            monitoring_text = "\n".join(f"  - {m}" for m in monitoring_items[:4])  # Max 4 items

            if monitoring_items:
                return f"""PROCEED

Adjusted confidence ({adjusted_confidence}%) supports moving forward. Recommended monitoring:

{monitoring_text}

Confidence is high, but stay vigilant for early warning signs."""
            else:
                return f"""PROCEED

Adjusted confidence ({adjusted_confidence}%) strongly supports moving forward. No significant monitoring requirements identified."""
