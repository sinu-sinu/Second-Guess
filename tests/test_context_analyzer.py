"""Test script for Phase 1 acceptance criteria."""
import httpx
import json
import sys

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test that the server is running."""
    print("[OK] Testing health check...")
    response = httpx.get(f"{BASE_URL}/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    print("  [OK] Server is healthy")


def test_decision_evaluation():
    """Test POST /api/v1/decisions with example from PRD."""
    print("\n[OK] Testing decision evaluation...")

    decision_input = {
        "decision": "Can we launch this week?",
        "context": "Auth service is stable"
    }

    response = httpx.post(
        f"{BASE_URL}/api/v1/decisions",
        json=decision_input,
        timeout=30.0
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    data = response.json()

    # Print response for visual inspection
    print("\n  Response:")
    print(json.dumps(data, indent=2))

    # Acceptance criteria checks
    print("\n  [OK] Checking acceptance criteria...")

    # 1. Response includes completeness_score between 0-100
    assert "context_analysis" in data, "Missing context_analysis"
    completeness = data["context_analysis"]["completeness_score"]
    assert 0 <= completeness <= 100, f"Completeness score {completeness} not in range 0-100"
    print(f"    [OK] Completeness score: {completeness} (valid range)")

    # 2. Response includes required_context array with at least 3 items
    required_context = data["context_analysis"]["required_context"]
    assert len(required_context) >= 3, f"Required context has {len(required_context)} items, expected at least 3"
    print(f"    [OK] Required context: {len(required_context)} items")

    # 3. Response includes missing_context array
    missing_context = data["context_analysis"]["missing_context"]
    assert isinstance(missing_context, list), "Missing context must be a list"
    print(f"    [OK] Missing context: {len(missing_context)} items")

    # 4. Response includes decision_id and version
    assert "decision_id" in data, "Missing decision_id"
    assert "version" in data, "Missing version"
    assert data["version"] == 1, f"Expected version 1, got {data['version']}"
    print(f"    [OK] Decision ID: {data['decision_id']}, Version: {data['version']}")

    return data


def test_duplicate_submission():
    """Test that running same input twice creates two separate records."""
    print("\n[OK] Testing duplicate submission creates separate records...")

    decision_input = {
        "decision": "Should we hire 5 engineers?",
        "context": "We have $2M runway"
    }

    # Submit first time
    response1 = httpx.post(
        f"{BASE_URL}/api/v1/decisions",
        json=decision_input,
        timeout=30.0
    )
    data1 = response1.json()

    # Submit second time
    response2 = httpx.post(
        f"{BASE_URL}/api/v1/decisions",
        json=decision_input,
        timeout=30.0
    )
    data2 = response2.json()

    # Should have different decision_ids (because timestamps differ)
    assert data1["decision_id"] != data2["decision_id"], "Duplicate submissions should have different decision_ids"
    print(f"    [OK] First submission: {data1['decision_id']}")
    print(f"    [OK] Second submission: {data2['decision_id']}")
    print("    [OK] Different decision_ids confirmed")


def test_decision_retrieval():
    """Test GET endpoint for retrieving decision."""
    print("\n[OK] Testing decision retrieval...")

    # First create a decision
    decision_input = {
        "decision": "Can we launch this week?",
        "context": "Auth service is stable"
    }

    create_response = httpx.post(
        f"{BASE_URL}/api/v1/decisions",
        json=decision_input,
        timeout=30.0
    )
    created_data = create_response.json()
    decision_id = created_data["decision_id"]
    version = created_data["version"]

    # Retrieve it
    get_response = httpx.get(
        f"{BASE_URL}/api/v1/decisions/{decision_id}/versions/{version}",
        timeout=30.0
    )

    assert get_response.status_code == 200, f"Expected 200, got {get_response.status_code}"
    retrieved_data = get_response.json()

    # Verify it matches
    assert retrieved_data["decision_id"] == decision_id, "Decision ID mismatch"
    assert retrieved_data["version"] == version, "Version mismatch"
    print(f"    [OK] Successfully retrieved decision {decision_id} version {version}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1 Acceptance Criteria Tests")
    print("=" * 60)

    try:
        test_health_check()
        test_decision_evaluation()
        test_duplicate_submission()
        test_decision_retrieval()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
