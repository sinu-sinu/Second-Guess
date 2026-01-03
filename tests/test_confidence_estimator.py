"""Tests for Confidence Estimator agent."""
from src.agents.confidence_estimator import ConfidenceEstimatorAgent
from src.models.schemas import (
    ContextAnalysis, ProposerOutput, DevilsAdvocateOutput, JudgeOutput,
    Assumption, FailureScenario, RiskBreakdown, WeakClaim, UnsupportedClaim
)


def test_confidence_penalties_for_missing_context():
    """Test that missing context items apply appropriate penalties."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["deployment readiness", "rollback plan", "monitoring"],
        provided_context=[],
        missing_context=["deployment readiness", "rollback plan", "monitoring"],
        completeness_score=0
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[],
        confidence=80,
        justification="Let's go for it"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["No evidence of readiness"],
        failure_scenarios=[
            FailureScenario(
                description="Deployment fails",
                trigger="Missing rollback plan",
                impact_severity="high"
            )
        ],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(execution=5, market_customer=4, reputational=3, opportunity_cost=2)
    )

    judge_output = JudgeOutput(
        proposer_strength=4,
        advocate_strength=7,
        weak_claims=[],
        unsupported_claims=[],
        reasoning_assessment="Proposer lacks evidence"
    )

    result = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)

    # With completeness_score=0, expect 20% penalty per missing item = 60% total
    assert result.initial_confidence == 80
    assert result.adjusted_confidence <= 20, "Should have heavy penalties for 0% context completeness"
    assert len(result.penalties) >= 3, "Should have penalties for each missing context item"
    assert result.delta < 0, "Delta should be negative"

    # Check that penalties reference specific missing items
    penalty_reasons = [p.reason for p in result.penalties]
    assert any("deployment readiness" in reason for reason in penalty_reasons)
    assert any("rollback plan" in reason for reason in penalty_reasons)


def test_confidence_penalties_for_unsupported_claims():
    """Test that unsupported claims from Proposer apply penalties."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["deployment readiness"],
        provided_context=["deployment readiness"],
        missing_context=[],
        completeness_score=100
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[],
        confidence=85,
        justification="Everything is ready"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["No proof of readiness"],
        failure_scenarios=[],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(execution=3, market_customer=2, reputational=2, opportunity_cost=1)
    )

    judge_output = JudgeOutput(
        proposer_strength=5,
        advocate_strength=6,
        weak_claims=[],
        unsupported_claims=[
            UnsupportedClaim(
                source="proposer",
                claim="Deployment pipeline is tested",
                missing_evidence="No evidence of testing provided in context"
            ),
            UnsupportedClaim(
                source="proposer",
                claim="Rollback is automated",
                missing_evidence="No documentation of rollback automation"
            )
        ],
        reasoning_assessment="Multiple unsupported claims detected"
    )

    result = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)

    # Should have penalties for 2 unsupported claims (8% each = 16% total)
    unsupported_penalties = [p for p in result.penalties if "Unsupported claim" in p.reason]
    assert len(unsupported_penalties) == 2, "Should have penalty for each unsupported claim from Proposer"
    assert result.adjusted_confidence < result.initial_confidence
    assert result.delta < 0


def test_confidence_penalties_for_high_risk_assumptions():
    """Test that high-risk assumptions apply penalties."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="technical",
        required_context=["system capacity"],
        provided_context=["system capacity"],
        missing_context=[],
        completeness_score=100
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Database can handle 10x load",
                basis="Current performance is good",
                risk_level="high"
            ),
            Assumption(
                statement="Cache layer will prevent bottlenecks",
                basis="Similar systems use caching",
                risk_level="high"
            )
        ],
        confidence=90,
        justification="System should scale fine"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["No load testing evidence"],
        failure_scenarios=[],
        high_risk_assumptions=[
            "Database can handle 10x load (UNVERIFIED)",
            "Cache layer will prevent bottlenecks (UNVERIFIED)"
        ],
        risk_breakdown=RiskBreakdown(execution=7, market_customer=5, reputational=4, opportunity_cost=3)
    )

    judge_output = JudgeOutput(
        proposer_strength=4,
        advocate_strength=8,
        weak_claims=[],
        unsupported_claims=[],
        reasoning_assessment="High-risk assumptions without verification"
    )

    result = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)

    # Should have penalties for 2 high-risk assumptions flagged by both
    high_risk_penalties = [p for p in result.penalties if "High-risk" in p.reason]
    assert len(high_risk_penalties) == 2, "Should have penalty for each high-risk assumption"
    assert result.adjusted_confidence < result.initial_confidence
    assert result.delta < 0


def test_confidence_penalties_for_weak_claims():
    """Test that weak claims from Proposer apply penalties."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["readiness"],
        provided_context=["readiness"],
        missing_context=[],
        completeness_score=100
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[],
        confidence=75,
        justification="Things should work out fine"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["Vague justification"],
        failure_scenarios=[],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(execution=4, market_customer=3, reputational=2, opportunity_cost=2)
    )

    judge_output = JudgeOutput(
        proposer_strength=4,
        advocate_strength=7,
        weak_claims=[
            WeakClaim(
                source="proposer",
                claim="Things should work out fine",
                weakness_reason="Vague and generic, lacks specificity"
            ),
            WeakClaim(
                source="proposer",
                claim="Probably ready",
                weakness_reason="Hedging language without concrete evidence"
            )
        ],
        unsupported_claims=[],
        reasoning_assessment="Proposer uses vague language"
    )

    result = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)

    # Should have penalties for weak claims (5% each)
    weak_penalties = [p for p in result.penalties if "Weak/vague claim" in p.reason]
    assert len(weak_penalties) == 2, "Should have penalty for each weak claim from Proposer"
    assert result.adjusted_confidence < result.initial_confidence
    assert result.delta < 0


def test_confidence_penalties_for_execution_risk():
    """Test that high execution risk applies penalties."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="technical",
        required_context=["implementation plan"],
        provided_context=["implementation plan"],
        missing_context=[],
        completeness_score=100
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[],
        confidence=80,
        justification="Implementation is straightforward"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["Complex implementation with many unknowns"],
        failure_scenarios=[
            FailureScenario(
                description="Integration failures",
                trigger="Incompatible APIs",
                impact_severity="critical"
            )
        ],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(execution=9, market_customer=4, reputational=5, opportunity_cost=3)
    )

    judge_output = JudgeOutput(
        proposer_strength=5,
        advocate_strength=8,
        weak_claims=[],
        unsupported_claims=[],
        reasoning_assessment="High execution risk identified"
    )

    result = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)

    # Should have penalty for critical execution risk (15%)
    execution_penalties = [p for p in result.penalties if "execution risk" in p.reason.lower()]
    assert len(execution_penalties) == 1, "Should have penalty for critical execution risk"
    assert execution_penalties[0].percentage_impact == 15, "Critical execution risk should be 15%"
    assert result.adjusted_confidence < result.initial_confidence


def test_adjusted_confidence_bounds():
    """Test that adjusted confidence stays within 0-100 bounds."""
    agent = ConfidenceEstimatorAgent()

    # Create scenario with massive penalties
    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["a", "b", "c", "d", "e"],
        provided_context=[],
        missing_context=["a", "b", "c", "d", "e"],
        completeness_score=0
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(statement="Assumption 1", basis="Guess", risk_level="high"),
            Assumption(statement="Assumption 2", basis="Guess", risk_level="high"),
            Assumption(statement="Assumption 3", basis="Guess", risk_level="high")
        ],
        confidence=50,
        justification="Just guessing"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["Everything is wrong"],
        failure_scenarios=[
            FailureScenario(description="Total failure", trigger="Everything", impact_severity="critical")
        ],
        high_risk_assumptions=[
            "Assumption 1 (UNVERIFIED)",
            "Assumption 2 (UNVERIFIED)",
            "Assumption 3 (UNVERIFIED)"
        ],
        risk_breakdown=RiskBreakdown(execution=10, market_customer=9, reputational=8, opportunity_cost=7)
    )

    judge_output = JudgeOutput(
        proposer_strength=1,
        advocate_strength=10,
        weak_claims=[
            WeakClaim(source="proposer", claim="Claim 1", weakness_reason="Vague"),
            WeakClaim(source="proposer", claim="Claim 2", weakness_reason="Vague"),
            WeakClaim(source="proposer", claim="Claim 3", weakness_reason="Vague")
        ],
        unsupported_claims=[
            UnsupportedClaim(source="proposer", claim="Unsupported 1", missing_evidence="No evidence"),
            UnsupportedClaim(source="proposer", claim="Unsupported 2", missing_evidence="No evidence")
        ],
        reasoning_assessment="Extremely poor reasoning"
    )

    result = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)

    # Adjusted confidence should never go below 0
    assert result.adjusted_confidence >= 0, "Adjusted confidence should not be negative"
    assert result.adjusted_confidence <= 100, "Adjusted confidence should not exceed 100"


def test_final_recommendation_delay():
    """Test that low adjusted confidence generates DELAY recommendation."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["deployment plan", "rollback strategy"],
        provided_context=[],
        missing_context=["deployment plan", "rollback strategy"],
        completeness_score=0
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(statement="Manual rollback works", basis="Assumption", risk_level="high")
        ],
        confidence=60,
        justification="Should be fine"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["No plan in place"],
        failure_scenarios=[
            FailureScenario(
                description="Cannot rollback",
                trigger="No documented process",
                impact_severity="critical"
            )
        ],
        high_risk_assumptions=["Manual rollback works (UNVERIFIED)"],
        risk_breakdown=RiskBreakdown(execution=8, market_customer=7, reputational=6, opportunity_cost=4)
    )

    judge_output = JudgeOutput(
        proposer_strength=3,
        advocate_strength=8,
        weak_claims=[],
        unsupported_claims=[],
        reasoning_assessment="Insufficient evidence"
    )

    confidence_output = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)
    recommendation = agent.generate_final_recommendation(
        confidence_output, proposer_output, devils_advocate_output, context_analysis
    )

    assert confidence_output.adjusted_confidence < 40, "Should have low adjusted confidence"
    assert "DELAY" in recommendation, "Should recommend DELAY for low confidence"
    assert "deployment plan" in recommendation or "rollback strategy" in recommendation, \
        "Should mention specific blockers"


def test_final_recommendation_conditional():
    """Test that medium adjusted confidence generates CONDITIONAL recommendation."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["deployment plan", "monitoring"],
        provided_context=["deployment plan"],
        missing_context=["monitoring"],
        completeness_score=50
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(statement="Monitoring can be added later", basis="Team capacity", risk_level="medium")
        ],
        confidence=70,
        justification="Deployment plan is solid"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["No monitoring in place"],
        failure_scenarios=[
            FailureScenario(
                description="Issues go undetected",
                trigger="No monitoring",
                impact_severity="high"
            )
        ],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(execution=5, market_customer=4, reputational=5, opportunity_cost=3)
    )

    judge_output = JudgeOutput(
        proposer_strength=6,
        advocate_strength=7,
        weak_claims=[],
        unsupported_claims=[],
        reasoning_assessment="Reasonable but incomplete"
    )

    confidence_output = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)
    recommendation = agent.generate_final_recommendation(
        confidence_output, proposer_output, devils_advocate_output, context_analysis
    )

    assert 40 <= confidence_output.adjusted_confidence < 70, "Should have medium adjusted confidence"
    assert "CONDITIONAL" in recommendation, "Should recommend CONDITIONAL PROCEED for medium confidence"
    assert "monitoring" in recommendation, "Should mention missing context as requirement"


def test_final_recommendation_proceed():
    """Test that high adjusted confidence generates PROCEED recommendation."""
    agent = ConfidenceEstimatorAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["deployment plan", "rollback strategy", "monitoring"],
        provided_context=["deployment plan", "rollback strategy", "monitoring"],
        missing_context=[],
        completeness_score=100
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Load will be within tested limits",
                basis="Historical traffic patterns and load tests",
                risk_level="low"
            )
        ],
        confidence=90,
        justification="All systems tested and ready"
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=["Unexpected traffic spikes possible"],
        failure_scenarios=[
            FailureScenario(
                description="Traffic spike",
                trigger="Media coverage",
                impact_severity="medium"
            )
        ],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(execution=3, market_customer=2, reputational=3, opportunity_cost=2)
    )

    judge_output = JudgeOutput(
        proposer_strength=8,
        advocate_strength=7,
        weak_claims=[],
        unsupported_claims=[],
        reasoning_assessment="Strong evidence-based reasoning from both sides"
    )

    confidence_output = agent.estimate(context_analysis, proposer_output, devils_advocate_output, judge_output)
    recommendation = agent.generate_final_recommendation(
        confidence_output, proposer_output, devils_advocate_output, context_analysis
    )

    assert confidence_output.adjusted_confidence >= 70, "Should have high adjusted confidence"
    assert "PROCEED" in recommendation, "Should recommend PROCEED for high confidence"
    assert "DELAY" not in recommendation and "CONDITIONAL" not in recommendation.split("PROCEED")[0], \
        "Should be pure PROCEED, not DELAY or CONDITIONAL"


if __name__ == "__main__":
    print("Running Confidence Estimator tests...")

    print("\n[Test 1/10] Testing confidence penalties for missing context...")
    test_confidence_penalties_for_missing_context()
    print("[PASS]")

    print("\n[Test 2/10] Testing confidence penalties for unsupported claims...")
    test_confidence_penalties_for_unsupported_claims()
    print("[PASS]")

    print("\n[Test 3/10] Testing confidence penalties for high-risk assumptions...")
    test_confidence_penalties_for_high_risk_assumptions()
    print("[PASS]")

    print("\n[Test 4/10] Testing confidence penalties for weak claims...")
    test_confidence_penalties_for_weak_claims()
    print("[PASS]")

    print("\n[Test 5/10] Testing confidence penalties for execution risk...")
    test_confidence_penalties_for_execution_risk()
    print("[PASS]")

    print("\n[Test 6/10] Testing adjusted confidence bounds...")
    test_adjusted_confidence_bounds()
    print("[PASS]")

    print("\n[Test 7/10] Testing final recommendation: DELAY...")
    test_final_recommendation_delay()
    print("[PASS]")

    print("\n[Test 8/10] Testing final recommendation: CONDITIONAL...")
    test_final_recommendation_conditional()
    print("[PASS]")

    print("\n[Test 9/10] Testing final recommendation: PROCEED...")
    test_final_recommendation_proceed()
    print("[PASS]")

    print("\n" + "="*60)
    print("All Confidence Estimator tests passed!")
    print("="*60)
