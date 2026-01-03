"""Tests for decision versioning and comparison."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.decision_service import DecisionService
from src.models.schemas import DecisionInput
from src.models.database import Base, engine, SessionLocal


def setup_test_db():
    """Set up a fresh test database."""
    # Drop all tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_decision_versioning():
    """Test that re-evaluating a decision creates new versions."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create initial decision (v1)
        v1_input = DecisionInput(
            decision="Should we launch the new feature?",
            context="Basic tests are passing"
        )

        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id

        assert v1_response.version == 1
        assert v1_response.context_provided == "Basic tests are passing"
        print(f"\n[PASS] v1 created: {decision_id}")
        print(f"  v1 context completeness: {v1_response.context_analysis.completeness_score}%")
        print(f"  v1 adjusted confidence: {v1_response.confidence_output.adjusted_confidence if v1_response.confidence_output else 'N/A'}%")

        # Re-evaluate with more context (v2)
        v2_input = DecisionInput(
            decision="Should we launch the new feature?",  # Same decision
            context="Basic tests passing. Load tests completed successfully. Rollback plan documented."
        )

        v2_response = service.reevaluate_decision(decision_id, v2_input, db)

        assert v2_response.version == 2
        assert v2_response.decision_id == decision_id
        assert v2_response.decision == v1_response.decision
        assert v2_response.context_provided != v1_response.context_provided
        print(f"\n[PASS] v2 created")
        print(f"  v2 context completeness: {v2_response.context_analysis.completeness_score}%")
        print(f"  v2 adjusted confidence: {v2_response.confidence_output.adjusted_confidence if v2_response.confidence_output else 'N/A'}%")

        # Verify v1 is still retrievable
        v1_retrieved = service.get_decision(decision_id, 1, db)
        assert v1_retrieved.version == 1
        assert v1_retrieved.context_provided == v1_response.context_provided

        print("\n[PASS] v1 still retrievable independently")

    finally:
        db.close()


def test_reevaluate_prevents_decision_change():
    """Test that re-evaluation prevents changing the decision statement."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create initial decision
        v1_input = DecisionInput(
            decision="Should we launch feature A?",
            context="Tests passing"
        )

        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id

        # Try to re-evaluate with different decision statement
        v2_input = DecisionInput(
            decision="Should we launch feature B?",  # Different decision
            context="More tests passing"
        )

        try:
            service.reevaluate_decision(decision_id, v2_input, db)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Decision statement must match original" in str(e)
            print(f"\n[PASS] Decision statement change prevented: {e}")

    finally:
        db.close()


def test_get_latest_decision():
    """Test retrieving the latest version of a decision."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create v1
        v1_input = DecisionInput(
            decision="Should we hire a senior engineer?",
            context="Budget approved"
        )
        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id

        # Create v2
        v2_input = DecisionInput(
            decision="Should we hire a senior engineer?",
            context="Budget approved. Candidate identified. References checked."
        )
        v2_response = service.reevaluate_decision(decision_id, v2_input, db)

        # Get latest should return v2
        latest = service.get_latest_decision(decision_id, db)
        assert latest.version == 2
        assert latest.context_provided == v2_response.context_provided

        print(f"\n[PASS] get_latest_decision returns v2")
        print(f"  Latest version: {latest.version}")

    finally:
        db.close()


def test_get_all_versions():
    """Test retrieving all versions as summaries."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create v1
        v1_input = DecisionInput(
            decision="Should we refactor the authentication service?",
            context="Current service is slow"
        )
        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id

        # Create v2
        v2_input = DecisionInput(
            decision="Should we refactor the authentication service?",
            context="Current service is slow. New design reviewed. Performance improvements estimated at 5x."
        )
        v2_response = service.reevaluate_decision(decision_id, v2_input, db)

        # Create v3
        v3_input = DecisionInput(
            decision="Should we refactor the authentication service?",
            context="Current service is slow. New design reviewed. Performance improvements estimated at 5x. Migration plan ready. Rollback tested."
        )
        v3_response = service.reevaluate_decision(decision_id, v3_input, db)

        # Get all versions
        all_versions = service.get_all_versions(decision_id, db)

        assert len(all_versions) == 3
        assert all_versions[0].version == 1
        assert all_versions[1].version == 2
        assert all_versions[2].version == 3

        print(f"\n[PASS] get_all_versions returns all 3 versions")
        for summary in all_versions:
            print(f"  v{summary.version}: completeness={summary.context_completeness}%, confidence={summary.adjusted_confidence}%")

    finally:
        db.close()


def test_version_comparison():
    """Test comparing two versions of a decision."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create v1 with minimal context
        v1_input = DecisionInput(
            decision="Should we deploy to production?",
            context="Code is ready"
        )
        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id

        # Create v2 with more context
        v2_input = DecisionInput(
            decision="Should we deploy to production?",
            context="Code is ready. All tests passing. Load testing completed. Rollback plan documented. Monitoring configured."
        )
        v2_response = service.reevaluate_decision(decision_id, v2_input, db)

        # Compare v1 and v2
        comparison = service.compare_versions(decision_id, 1, 2, db)

        assert comparison.decision_id == decision_id
        assert comparison.v1 == 1
        assert comparison.v2 == 2

        # Context completeness should improve
        assert comparison.context_completeness_delta > 0, "Context completeness should increase"

        # Confidence should improve (or stay same) when context is added
        print(f"\n[PASS] Version comparison")
        print(f"  Context completeness delta: {comparison.context_completeness_delta}")
        print(f"  Confidence delta: {comparison.confidence_delta}")
        print(f"  Risk reduction: exec={comparison.risk_reduction.execution}, market={comparison.risk_reduction.market_customer}")
        print(f"  Resolved missing context: {comparison.resolved_missing_context}")
        print(f"  Remaining missing context: {comparison.remaining_missing_context}")

        # Should have resolved some missing context items
        assert len(comparison.resolved_missing_context) > 0, "Should have resolved some missing context"

    finally:
        db.close()


def test_comparison_shows_context_resolution():
    """Test that comparison correctly identifies resolved vs remaining context."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create v1 with no context (many missing items)
        v1_input = DecisionInput(
            decision="Should we migrate to the new database?",
            context=""
        )
        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id
        v1_missing = set(v1_response.context_analysis.missing_context)

        print(f"\n[INFO] v1 missing context ({len(v1_missing)} items): {list(v1_missing)[:3]}...")

        # Create v2 with partial context
        v2_input = DecisionInput(
            decision="Should we migrate to the new database?",
            context="Migration plan documented. Data backup strategy in place."
        )
        v2_response = service.reevaluate_decision(decision_id, v2_input, db)
        v2_missing = set(v2_response.context_analysis.missing_context)

        print(f"[INFO] v2 missing context ({len(v2_missing)} items): {list(v2_missing)[:3]}...")

        # Compare
        comparison = service.compare_versions(decision_id, 1, 2, db)

        # Should have some resolved items (v1 had them, v2 doesn't)
        resolved = set(comparison.resolved_missing_context)
        remaining = set(comparison.remaining_missing_context)

        print(f"\n[PASS] Context resolution tracking")
        print(f"  Resolved items ({len(resolved)}): {list(resolved)[:3] if resolved else 'None'}")
        print(f"  Remaining items ({len(remaining)}): {list(remaining)[:3] if remaining else 'None'}")

        # Verify set relationships
        assert resolved == (v1_missing - v2_missing), "Resolved should be items in v1 but not v2"
        assert remaining == (v1_missing & v2_missing), "Remaining should be items in both v1 and v2"

    finally:
        db.close()


def test_comparison_non_adjacent_versions():
    """Test that comparison works for non-adjacent versions."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create v1
        v1_input = DecisionInput(
            decision="Should we adopt the new framework?",
            context="Team is interested"
        )
        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id

        # Create v2
        v2_input = DecisionInput(
            decision="Should we adopt the new framework?",
            context="Team is interested. Proof of concept built."
        )
        service.reevaluate_decision(decision_id, v2_input, db)

        # Create v3
        v3_input = DecisionInput(
            decision="Should we adopt the new framework?",
            context="Team is interested. Proof of concept built. Performance benchmarks completed. Migration path identified. Training plan ready."
        )
        v3_response = service.reevaluate_decision(decision_id, v3_input, db)

        # Compare v1 and v3 (skip v2)
        comparison = service.compare_versions(decision_id, 1, 3, db)

        assert comparison.v1 == 1
        assert comparison.v2 == 3  # Note: v2 in comparison schema means "second version being compared", which is v3
        assert comparison.context_completeness_delta > 0

        print(f"\n[PASS] Non-adjacent version comparison (v1 vs v3)")
        print(f"  Context delta: {comparison.context_completeness_delta}")
        print(f"  Confidence delta: {comparison.confidence_delta}")

    finally:
        db.close()


def test_comparison_handles_missing_data():
    """Test that comparison handles cases where some data might be None."""
    setup_test_db()
    service = DecisionService()
    db = SessionLocal()

    try:
        # Create v1
        v1_input = DecisionInput(
            decision="Should we sunset the legacy API?",
            context="API is old"
        )
        v1_response = service.evaluate_decision(v1_input, db)
        decision_id = v1_response.decision_id

        # Create v2
        v2_input = DecisionInput(
            decision="Should we sunset the legacy API?",
            context="API is old. Usage analytics reviewed. Migration guide drafted. Customer communication plan ready."
        )
        v2_response = service.reevaluate_decision(decision_id, v2_input, db)

        # Compare (should handle all cases gracefully)
        comparison = service.compare_versions(decision_id, 1, 2, db)

        # Should not crash even if some fields are None
        assert comparison is not None
        assert hasattr(comparison, 'confidence_delta')
        assert hasattr(comparison, 'risk_reduction')

        print(f"\n[PASS] Comparison handles potential None values gracefully")

    finally:
        db.close()


if __name__ == "__main__":
    print("Running decision versioning and comparison tests...\n")
    print("=" * 60)

    print("\n[Test 1/8] Testing decision versioning...")
    test_decision_versioning()

    print("\n[Test 2/8] Testing re-evaluation prevents decision change...")
    test_reevaluate_prevents_decision_change()

    print("\n[Test 3/8] Testing get latest decision...")
    test_get_latest_decision()

    print("\n[Test 4/8] Testing get all versions...")
    test_get_all_versions()

    print("\n[Test 5/8] Testing version comparison...")
    test_version_comparison()

    print("\n[Test 6/8] Testing context resolution tracking...")
    test_comparison_shows_context_resolution()

    print("\n[Test 7/8] Testing non-adjacent version comparison...")
    test_comparison_non_adjacent_versions()

    print("\n[Test 8/8] Testing comparison with missing data...")
    test_comparison_handles_missing_data()

    print("\n" + "=" * 60)
    print("All versioning and comparison tests passed!")
    print("=" * 60)
