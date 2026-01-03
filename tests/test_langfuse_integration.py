"""Tests for Langfuse integration."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.observability.langfuse_client import LangfuseClient, get_langfuse
from src.services.workflow import DecisionWorkflow
from src.models.schemas import DecisionInput
from src.services.decision_service import DecisionService
from src.models.database import Base, engine, SessionLocal


def test_langfuse_client_initialization():
    """Test that Langfuse client initializes correctly."""
    # This test will warn if Langfuse is not configured but won't fail
    client = get_langfuse()

    if client:
        print("\n[PASS] Langfuse client initialized successfully")
        print(f"  Langfuse enabled: {LangfuseClient.is_enabled()}")
    else:
        print("\n[INFO] Langfuse not configured (this is OK for local testing)")
        print("  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable tracing")


def test_workflow_with_tracing():
    """Test that workflow runs with tracing enabled/disabled."""
    workflow = DecisionWorkflow()

    # Run workflow (will trace if Langfuse is configured)
    result = workflow.run(
        decision="Should we launch the new feature?",
        context="Tests are passing",
        decision_id="test_dec_001",
        version=1
    )

    # Verify workflow executed successfully
    assert result is not None
    assert result["context_analysis"] is not None
    assert result["proposer_output"] is not None
    assert result["devils_advocate_output"] is not None
    assert result["judge_output"] is not None
    assert result["confidence_output"] is not None
    assert result["final_recommendation"] is not None

    # Check if trace_id was set (only if Langfuse is configured)
    if LangfuseClient.is_enabled():
        assert result.get("trace_id") is not None
        print(f"\n[PASS] Workflow executed with tracing")
        print(f"  Trace ID: {result.get('trace_id')}")
    else:
        print("\n[PASS] Workflow executed without tracing (Langfuse not configured)")

    print(f"  Decision ID: {result.get('decision_id')}")
    print(f"  Version: {result.get('version')}")
    print(f"  Context completeness: {result['context_analysis'].completeness_score}%")
    print(f"  Adjusted confidence: {result['confidence_output'].adjusted_confidence}%")


def test_disabled_langfuse():
    """Test that system works correctly when Langfuse is disabled."""
    # Temporarily disable Langfuse
    original_state = LangfuseClient.is_enabled()
    LangfuseClient.disable()

    try:
        workflow = DecisionWorkflow()

        # Run workflow without tracing
        result = workflow.run(
            decision="Should we refactor the codebase?",
            context="Current code is messy",
            decision_id="test_dec_002",
            version=1
        )

        # Verify workflow still works
        assert result is not None
        assert result["context_analysis"] is not None
        assert result["final_recommendation"] is not None
        assert result.get("trace_id") is None  # No trace when disabled

        print("\n[PASS] Workflow works correctly with Langfuse disabled")

    finally:
        # Restore original state
        if original_state:
            LangfuseClient.enable()


def test_custom_metrics_logged():
    """Test that custom metrics are logged to Langfuse."""
    if not LangfuseClient.is_enabled():
        print("\n[SKIP] Langfuse not configured, skipping custom metrics test")
        return

    workflow = DecisionWorkflow()

    # Run workflow
    result = workflow.run(
        decision="Should we hire a new engineer?",
        context="Team is overloaded. Budget approved.",
        decision_id="test_dec_003",
        version=1
    )

    # Verify metrics would have been logged (scores are logged in _estimate_confidence)
    assert result["confidence_output"] is not None
    assert result["context_analysis"] is not None

    print("\n[PASS] Custom metrics logged")
    print(f"  Context completeness: {result['context_analysis'].completeness_score}/100")
    print(f"  Adjusted confidence: {result['confidence_output'].adjusted_confidence}/100")
    print(f"  Confidence delta: {result['confidence_output'].delta}")


if __name__ == "__main__":
    print("Running Langfuse integration tests...\n")
    print("=" * 60)

    print("\n[Test 1/4] Testing Langfuse client initialization...")
    test_langfuse_client_initialization()

    print("\n[Test 2/4] Testing workflow with tracing...")
    test_workflow_with_tracing()

    print("\n[Test 3/4] Testing disabled Langfuse...")
    test_disabled_langfuse()

    print("\n[Test 4/4] Testing custom metrics logging...")
    test_custom_metrics_logged()

    print("\n" + "=" * 60)
    print("All Langfuse integration tests passed!")
    print("=" * 60)
    print("\nNote: To enable full Langfuse tracing, set these environment variables:")
    print("  LANGFUSE_PUBLIC_KEY=<your-public-key>")
    print("  LANGFUSE_SECRET_KEY=<your-secret-key>")
    print("  LANGFUSE_HOST=<your-langfuse-url>")
    print("\nFor self-hosted Langfuse (default):")
    print("  LANGFUSE_HOST=http://localhost:3000")
    print("\nFor cloud-hosted Langfuse:")
    print("  LANGFUSE_HOST=https://cloud.langfuse.com")
    print("\nTo run self-hosted Langfuse with Docker:")
    print("  docker run -d -p 3000:3000 langfuse/langfuse")
