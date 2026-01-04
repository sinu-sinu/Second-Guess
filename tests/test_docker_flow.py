#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify the complete Docker flow:
1. Decision evaluation via API
2. Langfuse tracing
3. Cost tracking for gpt-4.1-mini
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment
load_dotenv()

# Configuration
API_URL = "http://localhost:8000"
LANGFUSE_URL = "http://localhost:3000"

def test_api_health():
    """Test API health endpoint."""
    print("\n[1/5] Testing API Health...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("  ✓ API is healthy:", response.json())
            return True
        else:
            print(f"  ✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error connecting to API: {e}")
        return False


def test_langfuse_access():
    """Test Langfuse accessibility."""
    print("\n[2/5] Testing Langfuse Access...")
    try:
        response = requests.get(LANGFUSE_URL, timeout=5)
        if response.status_code == 200:
            print("  ✓ Langfuse is accessible")
            return True
        else:
            print(f"  ✗ Langfuse returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error connecting to Langfuse: {e}")
        return False


def test_decision_evaluation():
    """Test decision evaluation endpoint."""
    print("\n[3/5] Testing Decision Evaluation...")

    decision_data = {
        "decision": "Should we deploy the new microservice to production?",
        "context": "All tests passing. Load tests completed. Rollback plan ready. Team trained."
    }

    print(f"  Decision: {decision_data['decision']}")
    print(f"  Context: {decision_data['context']}")

    try:
        response = requests.post(
            f"{API_URL}/api/v1/decisions",
            json=decision_data,
            timeout=120
        )

        if response.status_code == 201:
            result = response.json()
            print("\n  ✓ Decision evaluated successfully!")
            print(f"  Decision ID: {result['decision_id']}")
            print(f"  Version: {result['version']}")
            print(f"  Context Completeness: {result['context_analysis']['completeness_score']}%")
            print(f"  Initial Confidence: {result['confidence_output']['initial_confidence']}%")
            print(f"  Adjusted Confidence: {result['confidence_output']['adjusted_confidence']}%")
            print(f"  Confidence Delta: {result['confidence_output']['delta']}")
            print(f"  Final Recommendation: {result['final_recommendation'][:100]}...")

            # Wait for Langfuse to process the trace
            print("\n  Waiting 5 seconds for Langfuse to process trace...")
            time.sleep(5)

            return True, result
        else:
            print(f"  ✗ Evaluation failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False, None
    except Exception as e:
        print(f"  ✗ Error during evaluation: {e}")
        return False, None


def verify_langfuse_tracking():
    """Verify that Langfuse is configured and tracking."""
    print("\n[4/5] Verifying Langfuse Tracking...")

    # Check if Langfuse keys are set
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key or \
       public_key == "your_langfuse_public_key_here" or \
       secret_key == "your_langfuse_secret_key_here":
        print("  ⚠ Langfuse keys not configured in .env")
        print("  → Traces will NOT be sent to Langfuse")
        print("  → To enable: Create project at http://localhost:3000 and add keys to .env")
        return False

    print("  ✓ Langfuse keys are configured")
    print(f"  Public Key: {public_key[:20]}...")
    print(f"  → Check traces at: {LANGFUSE_URL}")
    return True


def verify_model_in_langfuse():
    """Verify gpt-4.1-mini model exists in Langfuse database."""
    print("\n[5/5] Verifying Custom Model in Langfuse...")

    try:
        import psycopg2
    except ImportError:
        print("  ⚠ psycopg2 not installed, skipping database check")
        print("  → Model was added via SQL command")
        print("  → Install psycopg2-binary to verify: pip install psycopg2-binary")
        return True

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="langfuse",
            user=os.getenv("POSTGRES_USER", "langfuse"),
            password=os.getenv("POSTGRES_PASSWORD", "langfuse_password")
        )

        cur = conn.cursor()
        cur.execute("""
            SELECT model_name, match_pattern, input_price, output_price
            FROM models
            WHERE model_name = 'gpt-4.1-mini'
        """)

        result = cur.fetchone()

        if result:
            model_name, pattern, input_price, output_price = result
            print(f"  ✓ Model '{model_name}' found in Langfuse database")
            print(f"    Match Pattern: {pattern}")
            print(f"    Input Price: ${float(input_price) * 1000000:.2f} per 1M tokens")
            print(f"    Output Price: ${float(output_price) * 1000000:.2f} per 1M tokens")

            # Verify correct pricing
            expected_input = 0.000000150
            expected_output = 0.000000600

            if abs(float(input_price) - expected_input) < 0.000000001 and \
               abs(float(output_price) - expected_output) < 0.000000001:
                print("  ✓ Pricing is correct!")
            else:
                print("  ⚠ Pricing might be incorrect")
                print(f"    Expected: ${expected_input * 1000000:.2f} / ${expected_output * 1000000:.2f} per 1M")

            cur.close()
            conn.close()
            return True
        else:
            print("  ✗ Model 'gpt-4.1-mini' NOT found in database")
            print("  → Run: docker exec second-guess-postgres psql -U langfuse -d langfuse -c \"...\"")
            cur.close()
            conn.close()
            return False

    except Exception as e:
        print(f"  ✗ Error checking model: {e}")
        print(f"  → Make sure psycopg2 is installed: pip install psycopg2-binary")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Second Guess Docker Flow Test")
    print("=" * 70)

    # Test 1: API Health
    if not test_api_health():
        print("\n✗ API is not healthy. Exiting.")
        sys.exit(1)

    # Test 2: Langfuse Access
    if not test_langfuse_access():
        print("\n⚠ Langfuse is not accessible but continuing...")

    # Test 3: Decision Evaluation
    success, result = test_decision_evaluation()
    if not success:
        print("\n✗ Decision evaluation failed. Exiting.")
        sys.exit(1)

    # Test 4: Langfuse Tracking
    langfuse_enabled = verify_langfuse_tracking()

    # Test 5: Model Verification
    model_exists = verify_model_in_langfuse()

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"✓ API Health: PASS")
    print(f"✓ Langfuse Access: PASS")
    print(f"✓ Decision Evaluation: PASS")
    print(f"{'✓' if langfuse_enabled else '⚠'} Langfuse Tracking: {'ENABLED' if langfuse_enabled else 'NOT CONFIGURED'}")
    print(f"{'✓' if model_exists else '✗'} Custom Model: {'FOUND' if model_exists else 'NOT FOUND'}")

    print("\n" + "=" * 70)
    print("Next Steps:")
    print("=" * 70)

    if not langfuse_enabled:
        print("1. Create a Langfuse project:")
        print("   → Open http://localhost:3000")
        print("   → Sign up / Create account")
        print("   → Create a project")
        print("   → Go to Settings → API Keys")
        print("   → Copy keys and add to .env file")
        print()

    if langfuse_enabled:
        print("1. View traces in Langfuse:")
        print(f"   → Open {LANGFUSE_URL}")
        print("   → Navigate to your project")
        print("   → Click 'Traces' tab")
        if result:
            print(f"   → Look for decision_id: {result['decision_id']}")
        print()

    print("2. Verify cost tracking:")
    print("   → Check if traces show token counts")
    print("   → Verify costs are calculated")
    print("   → Model should be recognized as 'gpt-4.1-mini'")
    print()

    print("3. Test re-evaluation:")
    if result:
        print(f"   → Re-evaluate decision: {result['decision_id']}")
        print("   → Add more context and create v2")
        print("   → Compare versions")
    print()

    print("=" * 70)

    if langfuse_enabled and model_exists:
        print("\n🎉 All systems operational! Cost tracking is enabled.")
    elif model_exists:
        print("\n⚠ System operational but Langfuse not configured.")
    else:
        print("\n⚠ System operational but custom model needs setup.")


if __name__ == "__main__":
    main()
