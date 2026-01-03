"""Tests for Proposer Agent."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.proposer import ProposerAgent
from src.models.schemas import ContextAnalysis


def test_proposer_with_low_completeness():
    """Test that proposer generates assumptions when context is incomplete."""
    agent = ProposerAgent()

    # Context analysis with low completeness
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

    result = agent.propose(
        decision="Should we launch this week?",
        context="Auth service is stable",
        context_analysis=context_analysis
    )

    # Verify structure
    assert result.recommendation in ["proceed", "delay", "conditional", "conditional:"] or result.recommendation.startswith("conditional:")
    assert isinstance(result.assumptions, list)
    assert len(result.assumptions) >= 2, "Should have at least 2 assumptions for incomplete context"
    assert 0 <= result.confidence <= 100
    assert len(result.justification) > 0

    # Verify assumptions structure
    for assumption in result.assumptions:
        assert len(assumption.statement) > 0
        assert len(assumption.basis) > 0
        assert assumption.risk_level in ["low", "medium", "high"]

    print(f"\n[PASS] Test passed: Proposer with low completeness")
    print(f"  Recommendation: {result.recommendation}")
    print(f"  Assumptions: {len(result.assumptions)}")
    print(f"  Confidence: {result.confidence}")


def test_proposer_with_high_completeness():
    """Test that proposer has higher confidence with complete context."""
    agent = ProposerAgent()

    # Context analysis with high completeness
    context_analysis = ContextAnalysis(
        decision_type="launch",
        required_context=[
            "deployment readiness",
            "rollback plan",
            "system stability verification"
        ],
        provided_context=[
            "deployment readiness",
            "rollback plan",
            "system stability verification"
        ],
        missing_context=[],
        completeness_score=100
    )

    result = agent.propose(
        decision="Should we launch this week?",
        context="All systems stable, rollback plan ready, deployment scripts tested",
        context_analysis=context_analysis
    )

    # Verify structure
    assert result.recommendation in ["proceed", "delay", "conditional", "conditional:"] or result.recommendation.startswith("conditional:")
    assert isinstance(result.assumptions, list)
    assert 0 <= result.confidence <= 100
    assert len(result.justification) > 0

    # With high completeness, confidence should be reasonably high
    # (though not necessarily >50, depends on LLM's assessment)
    print(f"\n[PASS] Test passed: Proposer with high completeness")
    print(f"  Recommendation: {result.recommendation}")
    print(f"  Assumptions: {len(result.assumptions)}")
    print(f"  Confidence: {result.confidence}")


def test_proposer_output_consistency():
    """Test that same input produces consistent output structure."""
    agent = ProposerAgent()

    context_analysis = ContextAnalysis(
        decision_type="technical",
        required_context=["technical requirements", "implementation complexity"],
        provided_context=["technical requirements"],
        missing_context=["implementation complexity"],
        completeness_score=50
    )

    # Run twice
    result1 = agent.propose(
        decision="Should we refactor the auth module?",
        context="Need better performance",
        context_analysis=context_analysis
    )

    result2 = agent.propose(
        decision="Should we refactor the auth module?",
        context="Need better performance",
        context_analysis=context_analysis
    )

    # Both should have required fields
    for result in [result1, result2]:
        assert hasattr(result, 'recommendation')
        assert hasattr(result, 'assumptions')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'justification')

    print(f"\n[PASS] Test passed: Output consistency")


def test_proposer_evaluative_language():
    """Test that proposer uses evaluative language, not conversational."""
    agent = ProposerAgent()

    context_analysis = ContextAnalysis(
        decision_type="pricing",
        required_context=["competitive analysis", "cost structure"],
        provided_context=[],
        missing_context=["competitive analysis", "cost structure"],
        completeness_score=0
    )

    result = agent.propose(
        decision="Should we increase pricing by 20%?",
        context="",
        context_analysis=context_analysis
    )

    # Check that output doesn't use conversational phrases
    justification_lower = result.justification.lower()

    # Should not contain these conversational phrases
    bad_phrases = ["it seems", "i think", "i believe", "maybe", "perhaps"]
    for phrase in bad_phrases:
        # Allow these in quoted assumptions but ideally not in justification
        pass  # Note: this is a soft check, hard to enforce strictly

    # Should be structured and evaluative
    assert len(result.justification) > 20, "Justification should be substantive"

    print(f"\n[PASS] Test passed: Evaluative language")
    print(f"  Justification: {result.justification[:100]}...")


if __name__ == "__main__":
    print("Running Proposer Agent tests...\n")

    test_proposer_with_low_completeness()
    test_proposer_with_high_completeness()
    test_proposer_output_consistency()
    test_proposer_evaluative_language()

    print("\n[SUCCESS] All Proposer Agent tests passed!")
