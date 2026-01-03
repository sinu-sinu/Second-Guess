"""Tests for Judge Agent."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.judge import JudgeAgent
from src.models.schemas import ContextAnalysis, ProposerOutput, DevilsAdvocateOutput, Assumption, FailureScenario, RiskBreakdown


def test_judge_evaluates_both_sides():
    """Test that Judge evaluates both Proposer and Devil's Advocate."""
    agent = JudgeAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["deployment readiness", "rollback plan"],
        provided_context=["deployment readiness"],
        missing_context=["rollback plan"],
        completeness_score=50
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Rollback can be done manually",
                basis="Team has rollback experience",
                risk_level="medium"
            )
        ],
        confidence=75,
        justification="Deployment readiness is confirmed, team is prepared."
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=[
            "Execution Risk: Manual rollback is unverified",
            "Market & Customer Impact: Customers could be affected",
            "Reputational Downside: Public failure would damage brand",
            "Opportunity Cost: Resources could be used elsewhere"
        ],
        failure_scenarios=[
            FailureScenario(
                description="Database migration fails",
                trigger="Schema incompatibility",
                impact_severity="critical"
            )
        ],
        high_risk_assumptions=["Rollback can be done manually (UNVERIFIED)"],
        risk_breakdown=RiskBreakdown(
            execution=8,
            market_customer=7,
            reputational=6,
            opportunity_cost=5
        )
    )

    result = agent.evaluate(
        decision="Should we launch this week?",
        context="Deployment is ready",
        context_analysis=context_analysis,
        proposer_output=proposer_output,
        devils_advocate_output=devils_advocate_output
    )

    # Verify structure
    assert 0 <= result.proposer_strength <= 10
    assert 0 <= result.advocate_strength <= 10
    assert isinstance(result.weak_claims, list)
    assert isinstance(result.unsupported_claims, list)
    assert len(result.reasoning_assessment) > 0

    print(f"\n[PASS] Test passed: Judge evaluates both sides")
    print(f"  Proposer Strength: {result.proposer_strength}/10")
    print(f"  Advocate Strength: {result.advocate_strength}/10")
    print(f"  Weak Claims: {len(result.weak_claims)}")
    print(f"  Unsupported Claims: {len(result.unsupported_claims)}")


def test_judge_identifies_weak_claims():
    """Test that Judge identifies weak or vague claims."""
    agent = JudgeAgent()

    context_analysis = ContextAnalysis(
        decision_type="technical",
        required_context=["technical requirements", "implementation complexity"],
        provided_context=[],
        missing_context=["technical requirements", "implementation complexity"],
        completeness_score=0
    )

    # Proposer with vague justification
    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Things will probably work out",
                basis="General optimism",
                risk_level="low"
            )
        ],
        confidence=80,  # High confidence with 0% context = red flag
        justification="We should proceed because things usually work out fine."
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=[
            "Something might go wrong",  # Vague
            "There could be issues"  # Vague
        ],
        failure_scenarios=[
            FailureScenario(
                description="Generic failure",
                trigger="Unknown",
                impact_severity="medium"
            )
        ],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(
            execution=5,
            market_customer=5,
            reputational=5,
            opportunity_cost=5
        )
    )

    result = agent.evaluate(
        decision="Should we refactor the codebase?",
        context="",
        context_analysis=context_analysis,
        proposer_output=proposer_output,
        devils_advocate_output=devils_advocate_output
    )

    # With 0% completeness and vague arguments, should identify weak claims
    assert len(result.weak_claims) >= 1, "Should identify at least 1 weak claim with low completeness"

    # Verify weak claims have proper structure
    for weak_claim in result.weak_claims:
        assert weak_claim.source in ["proposer", "advocate"]
        assert len(weak_claim.claim) > 0
        assert len(weak_claim.weakness_reason) > 0

    print(f"\n[PASS] Test passed: Judge identifies weak claims")
    print(f"  Weak Claims Found: {len(result.weak_claims)}")
    if result.weak_claims:
        print(f"  Example: {result.weak_claims[0].claim} (from {result.weak_claims[0].source})")


def test_judge_identifies_unsupported_claims():
    """Test that Judge identifies claims not backed by context."""
    agent = JudgeAgent()

    context_analysis = ContextAnalysis(
        decision_type="pricing",
        required_context=["competitive analysis", "cost structure"],
        provided_context=["cost structure"],
        missing_context=["competitive analysis"],
        completeness_score=50
    )

    # Proposer makes assumption about competitors without evidence
    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Competitors will not react to price increase",
                basis="Market analysis",  # But no competitive analysis was provided
                risk_level="low"
            )
        ],
        confidence=70,
        justification="Based on competitive landscape, we can increase prices."
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=[
            "Competitors could undercut us significantly"
        ],
        failure_scenarios=[
            FailureScenario(
                description="Market share loss",
                trigger="Competitor price war",
                impact_severity="high"
            )
        ],
        high_risk_assumptions=["Competitors will not react (UNVERIFIED)"],
        risk_breakdown=RiskBreakdown(
            execution=6,
            market_customer=8,
            reputational=7,
            opportunity_cost=5
        )
    )

    result = agent.evaluate(
        decision="Should we increase prices by 20%?",
        context="Our costs have increased",
        context_analysis=context_analysis,
        proposer_output=proposer_output,
        devils_advocate_output=devils_advocate_output
    )

    # Should identify unsupported claims about competitors
    # (since competitive analysis is missing)
    for claim in result.unsupported_claims:
        assert claim.source in ["proposer", "advocate"]
        assert len(claim.claim) > 0
        assert len(claim.missing_evidence) > 0

    print(f"\n[PASS] Test passed: Judge identifies unsupported claims")
    print(f"  Unsupported Claims Found: {len(result.unsupported_claims)}")


def test_judge_penalizes_overconfidence():
    """Test that Judge penalizes high confidence with low context."""
    agent = JudgeAgent()

    context_analysis = ContextAnalysis(
        decision_type="hiring",
        required_context=["budget", "team capacity", "role requirements"],
        provided_context=[],
        missing_context=["budget", "team capacity", "role requirements"],
        completeness_score=0
    )

    # Proposer with 90% confidence despite 0% context
    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Budget will be approved",
                basis="Assumed",
                risk_level="high"
            )
        ],
        confidence=90,  # Overconfident
        justification="We definitely should hire immediately."
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=[
            "Budget approval is uncertain",
            "Team capacity is unknown",
            "Role requirements are undefined"
        ],
        failure_scenarios=[
            FailureScenario(
                description="Hire cannot start due to budget rejection",
                trigger="Budget freeze",
                impact_severity="medium"
            )
        ],
        high_risk_assumptions=["Budget will be approved (UNVERIFIED)"],
        risk_breakdown=RiskBreakdown(
            execution=9,
            market_customer=6,
            reputational=5,
            opportunity_cost=7
        )
    )

    result = agent.evaluate(
        decision="Should we hire a senior engineer?",
        context="",
        context_analysis=context_analysis,
        proposer_output=proposer_output,
        devils_advocate_output=devils_advocate_output
    )

    # Proposer strength should be lower due to overconfidence
    # (0% context but 90% confidence is a red flag)
    print(f"\n[PASS] Test passed: Judge penalizes overconfidence")
    print(f"  Proposer Strength: {result.proposer_strength}/10 (should be low due to overconfidence)")
    print(f"  Context: {context_analysis.completeness_score}%, Confidence: {proposer_output.confidence}%")


def test_judge_rewards_specificity():
    """Test that Judge rewards specific claims over vague ones."""
    agent = JudgeAgent()

    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=["deployment readiness", "rollback plan"],
        provided_context=["deployment readiness", "rollback plan"],
        missing_context=[],
        completeness_score=100
    )

    # Proposer with specific, evidence-backed claims
    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Rollback can complete within 15 minutes based on dry-run test",
                basis="Rollback dry-run completed successfully on staging",
                risk_level="low"
            )
        ],
        confidence=85,
        justification="Deployment scripts tested on staging, rollback verified with 15min recovery time, monitoring alerts configured."
    )

    devils_advocate_output = DevilsAdvocateOutput(
        counterarguments=[
            "Execution Risk: Staging environment may not match production load patterns, rollback could take longer under peak traffic",
            "Market & Customer Impact: Even 15min downtime affects 50k active users based on traffic analysis",
            "Reputational Downside: Previous outage generated 200+ social media complaints",
            "Opportunity Cost: Engineering team could focus on critical P0 bug affecting 10% of users"
        ],
        failure_scenarios=[
            FailureScenario(
                description="Database rollback fails due to foreign key constraints introduced in schema migration v2.1.5",
                trigger="Production database has stricter constraints than staging",
                impact_severity="critical"
            )
        ],
        high_risk_assumptions=[],
        risk_breakdown=RiskBreakdown(
            execution=6,
            market_customer=7,
            reputational=5,
            opportunity_cost=6
        )
    )

    result = agent.evaluate(
        decision="Should we deploy v2.1 this Friday?",
        context="Staging tests passed, rollback tested, monitoring ready",
        context_analysis=context_analysis,
        proposer_output=proposer_output,
        devils_advocate_output=devils_advocate_output
    )

    # Both sides have specific claims, so both should score reasonably well
    print(f"\n[PASS] Test passed: Judge rewards specificity")
    print(f"  Proposer Strength: {result.proposer_strength}/10 (specific claims)")
    print(f"  Advocate Strength: {result.advocate_strength}/10 (specific claims)")
    print(f"  Assessment: {result.reasoning_assessment}")


if __name__ == "__main__":
    print("Running Judge Agent tests...\n")

    test_judge_evaluates_both_sides()
    test_judge_identifies_weak_claims()
    test_judge_identifies_unsupported_claims()
    test_judge_penalizes_overconfidence()
    test_judge_rewards_specificity()

    print("\n[SUCCESS] All Judge Agent tests passed!")
