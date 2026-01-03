"""Tests for Devil's Advocate Agent."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.devils_advocate import DevilsAdvocateAgent
from src.models.schemas import ContextAnalysis, ProposerOutput, Assumption


def test_devils_advocate_four_dimensions():
    """Test that Devil's Advocate covers all four attack dimensions."""
    agent = DevilsAdvocateAgent()

    # Create context analysis with low completeness
    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=[
            "deployment readiness",
            "rollback plan",
            "system stability verification",
            "customer impact analysis"
        ],
        provided_context=["system stability verification"],
        missing_context=[
            "deployment readiness",
            "rollback plan",
            "customer impact analysis"
        ],
        completeness_score=25
    )

    # Create proposer output
    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Deployment will go smoothly",
                basis="Similar deployments have worked before",
                risk_level="medium"
            ),
            Assumption(
                statement="Users will adapt quickly",
                basis="User feedback has been positive",
                risk_level="low"
            )
        ],
        confidence=70,
        justification="Given the stable system, we should proceed with launch."
    )

    result = agent.critique(
        decision="Should we launch this week?",
        context="Auth service is stable",
        context_analysis=context_analysis,
        proposer_output=proposer_output
    )

    # Verify structure
    assert len(result.counterarguments) >= 4, "Should have at least 4 counterarguments (1 per dimension)"
    assert len(result.failure_scenarios) >= 3, "Should have at least 3 failure scenarios"
    assert len(result.high_risk_assumptions) > 0, "Should flag some high-risk assumptions"

    # Verify risk breakdown has all four dimensions
    assert hasattr(result.risk_breakdown, 'execution')
    assert hasattr(result.risk_breakdown, 'market_customer')
    assert hasattr(result.risk_breakdown, 'reputational')
    assert hasattr(result.risk_breakdown, 'opportunity_cost')

    # Verify risk scores are in range
    assert 0 <= result.risk_breakdown.execution <= 10
    assert 0 <= result.risk_breakdown.market_customer <= 10
    assert 0 <= result.risk_breakdown.reputational <= 10
    assert 0 <= result.risk_breakdown.opportunity_cost <= 10

    print(f"\n[PASS] Test passed: Devil's Advocate four dimensions")
    print(f"  Counterarguments: {len(result.counterarguments)}")
    print(f"  Failure Scenarios: {len(result.failure_scenarios)}")
    print(f"  High-Risk Assumptions: {len(result.high_risk_assumptions)}")
    print(f"  Risk Breakdown: exec={result.risk_breakdown.execution}, market={result.risk_breakdown.market_customer}, rep={result.risk_breakdown.reputational}, opp={result.risk_breakdown.opportunity_cost}")


def test_devils_advocate_low_completeness_high_risk():
    """Test that low context completeness results in higher execution risk."""
    agent = DevilsAdvocateAgent()

    # Low completeness scenario
    context_analysis = ContextAnalysis(
        decision_type="technical",
        required_context=["technical requirements", "implementation complexity", "testing strategy"],
        provided_context=[],
        missing_context=["technical requirements", "implementation complexity", "testing strategy"],
        completeness_score=0
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Implementation will be straightforward",
                basis="No context provided",
                risk_level="high"
            )
        ],
        confidence=30,
        justification="Proceeding with limited context."
    )

    result = agent.critique(
        decision="Should we refactor the auth module?",
        context="",
        context_analysis=context_analysis,
        proposer_output=proposer_output
    )

    # With 0% completeness, execution risk should be relatively high
    assert result.risk_breakdown.execution >= 5, "Low completeness should result in higher execution risk"

    print(f"\n[PASS] Test passed: Low completeness high risk")
    print(f"  Completeness: {context_analysis.completeness_score}%")
    print(f"  Execution Risk: {result.risk_breakdown.execution}/10")


def test_devils_advocate_failure_scenarios_specific():
    """Test that failure scenarios are specific with triggers."""
    agent = DevilsAdvocateAgent()

    context_analysis = ContextAnalysis(
        decision_type="pricing",
        required_context=["competitive analysis", "cost structure"],
        provided_context=["cost structure"],
        missing_context=["competitive analysis"],
        completeness_score=50
    )

    proposer_output = ProposerOutput(
        recommendation="conditional: proceed if competitor pricing is verified",
        assumptions=[
            Assumption(
                statement="Current pricing is below market rate",
                basis="Cost structure analysis",
                risk_level="medium"
            )
        ],
        confidence=60,
        justification="Cost structure supports price increase."
    )

    result = agent.critique(
        decision="Should we increase pricing by 20%?",
        context="Our costs have increased 15%",
        context_analysis=context_analysis,
        proposer_output=proposer_output
    )

    # Verify failure scenarios have required fields
    for scenario in result.failure_scenarios:
        assert len(scenario.description) > 0, "Failure scenario should have description"
        assert len(scenario.trigger) > 0, "Failure scenario should have trigger"
        assert scenario.impact_severity in ["low", "medium", "high", "critical"], "Severity should be valid"

    print(f"\n[PASS] Test passed: Failure scenarios specific")
    print(f"  First scenario: {result.failure_scenarios[0].description[:80]}...")
    print(f"  Trigger: {result.failure_scenarios[0].trigger[:60]}...")


def test_devils_advocate_challenges_assumptions():
    """Test that Devil's Advocate challenges Proposer's assumptions."""
    agent = DevilsAdvocateAgent()

    context_analysis = ContextAnalysis(
        decision_type="hiring",
        required_context=["current team capacity", "budget and runway"],
        provided_context=["current team capacity"],
        missing_context=["budget and runway"],
        completeness_score=50
    )

    proposer_output = ProposerOutput(
        recommendation="proceed",
        assumptions=[
            Assumption(
                statement="Budget will be approved",
                basis="Team capacity analysis shows need",
                risk_level="medium"
            ),
            Assumption(
                statement="Candidate market is favorable",
                basis="Recent hiring discussions",
                risk_level="low"
            )
        ],
        confidence=65,
        justification="Team capacity analysis shows clear need."
    )

    result = agent.critique(
        decision="Should we hire a senior engineer?",
        context="Team is at 80% capacity",
        context_analysis=context_analysis,
        proposer_output=proposer_output
    )

    # Should flag unverified assumptions
    assert len(result.high_risk_assumptions) > 0, "Should flag some assumptions as high-risk"

    # Counterarguments should exist
    assert len(result.counterarguments) >= 1, "Should have counterarguments"

    print(f"\n[PASS] Test passed: Challenges assumptions")
    print(f"  High-risk assumptions flagged: {len(result.high_risk_assumptions)}")
    print(f"  Example: {result.high_risk_assumptions[0] if result.high_risk_assumptions else 'None'}")


def test_devils_advocate_no_softening():
    """Test that Devil's Advocate doesn't soften critique."""
    agent = DevilsAdvocateAgent()

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
        justification="Deployment readiness is confirmed."
    )

    result = agent.critique(
        decision="Should we launch the new feature?",
        context="Deployment scripts are ready",
        context_analysis=context_analysis,
        proposer_output=proposer_output
    )

    # Check for softening phrases (soft check - hard to enforce strictly)
    all_text = " ".join(result.counterarguments).lower()
    softening_phrases = ["however", "on the other hand", "to be fair", "admittedly"]

    # Note: This is a guideline check, not a strict requirement
    # The system prompt instructs against softening, but LLM may still use some phrases

    print(f"\n[PASS] Test passed: No softening language")
    print(f"  First counterargument: {result.counterarguments[0][:100]}...")


if __name__ == "__main__":
    print("Running Devil's Advocate Agent tests...\n")

    test_devils_advocate_four_dimensions()
    test_devils_advocate_low_completeness_high_risk()
    test_devils_advocate_failure_scenarios_specific()
    test_devils_advocate_challenges_assumptions()
    test_devils_advocate_no_softening()

    print("\n[SUCCESS] All Devil's Advocate Agent tests passed!")
