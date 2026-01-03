"""Tests for LangGraph workflow orchestration."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.workflow import DecisionWorkflow


def test_workflow_end_to_end():
    """Test that workflow executes both agents in sequence."""
    workflow = DecisionWorkflow()

    result = workflow.run(
        decision="Should we launch the new feature next week?",
        context="Team is ready and tests are passing"
    )

    # Verify workflow state has all expected outputs
    assert "decision" in result
    assert "context" in result
    assert "context_analysis" in result
    assert "proposer_output" in result
    assert "devils_advocate_output" in result
    assert "judge_output" in result

    # Verify context analysis
    context_analysis = result["context_analysis"]
    assert context_analysis is not None
    assert hasattr(context_analysis, 'decision_type')
    assert hasattr(context_analysis, 'completeness_score')
    assert hasattr(context_analysis, 'required_context')
    assert hasattr(context_analysis, 'provided_context')
    assert hasattr(context_analysis, 'missing_context')

    # Verify proposer output
    proposer_output = result["proposer_output"]
    assert proposer_output is not None
    assert hasattr(proposer_output, 'recommendation')
    assert hasattr(proposer_output, 'assumptions')
    assert hasattr(proposer_output, 'confidence')
    assert hasattr(proposer_output, 'justification')

    # Verify devil's advocate output
    devils_advocate_output = result["devils_advocate_output"]
    assert devils_advocate_output is not None
    assert hasattr(devils_advocate_output, 'counterarguments')
    assert hasattr(devils_advocate_output, 'failure_scenarios')
    assert hasattr(devils_advocate_output, 'high_risk_assumptions')
    assert hasattr(devils_advocate_output, 'risk_breakdown')

    # Verify judge output
    judge_output = result["judge_output"]
    assert judge_output is not None
    assert hasattr(judge_output, 'proposer_strength')
    assert hasattr(judge_output, 'advocate_strength')
    assert hasattr(judge_output, 'weak_claims')
    assert hasattr(judge_output, 'unsupported_claims')
    assert hasattr(judge_output, 'reasoning_assessment')
    assert 0 <= judge_output.proposer_strength <= 10
    assert 0 <= judge_output.advocate_strength <= 10

    print(f"\n[PASS] Workflow end-to-end test passed")
    print(f"  Decision Type: {context_analysis.decision_type}")
    print(f"  Completeness: {context_analysis.completeness_score}%")
    print(f"  Recommendation: {proposer_output.recommendation}")
    print(f"  Confidence: {proposer_output.confidence}")
    print(f"  Counterarguments: {len(devils_advocate_output.counterarguments)}")
    print(f"  Risk Breakdown: exec={devils_advocate_output.risk_breakdown.execution}, market={devils_advocate_output.risk_breakdown.market_customer}")
    print(f"  Proposer Strength: {judge_output.proposer_strength}/10, Advocate Strength: {judge_output.advocate_strength}/10")


def test_workflow_with_no_context():
    """Test workflow when no context is provided."""
    workflow = DecisionWorkflow()

    result = workflow.run(
        decision="Should we hire a senior engineer?",
        context=None
    )

    # Should still complete successfully
    assert result["context_analysis"] is not None
    assert result["proposer_output"] is not None

    # With no context, should have low completeness
    context_analysis = result["context_analysis"]
    assert context_analysis.completeness_score < 50, "No context should result in low completeness"

    # Should have assumptions
    proposer_output = result["proposer_output"]
    assert len(proposer_output.assumptions) > 0, "No context should generate assumptions"

    print(f"\n[PASS] Workflow with no context test passed")
    print(f"  Completeness: {context_analysis.completeness_score}%")
    print(f"  Assumptions: {len(proposer_output.assumptions)}")


def test_workflow_sequential_execution():
    """Test that context analysis output feeds into proposer."""
    workflow = DecisionWorkflow()

    result = workflow.run(
        decision="Should we change our pricing model?",
        context="Current MRR is $50k"
    )

    context_analysis = result["context_analysis"]
    proposer_output = result["proposer_output"]

    # Proposer should reference the context analysis
    # (implicitly through the workflow)
    assert proposer_output is not None
    assert context_analysis is not None

    # The proposer's confidence and assumptions should reflect
    # the completeness score from context analysis
    if context_analysis.completeness_score < 50:
        # Low completeness should mean more assumptions
        assert len(proposer_output.assumptions) >= 2

    print(f"\n[PASS] Sequential execution test passed")


if __name__ == "__main__":
    print("Running Workflow tests...\n")

    test_workflow_end_to_end()
    test_workflow_with_no_context()
    test_workflow_sequential_execution()

    print("\n[SUCCESS] All Workflow tests passed!")
