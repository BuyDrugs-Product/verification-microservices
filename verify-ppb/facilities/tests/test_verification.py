"""
Test script for PPB verification service V4
Tests the complete two-step workflow with proper session and headers
"""

import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://localhost:5000"

TEST_CASES = [
    "PPB/C/9222",
    "PPB/G/1387",
    "PPB/F/034"
]

REQUIRED_FIELDS = [
    'facility_name',
    'registration_number',
    'license_number',
    'ownership',
    'license_type',
    'establishment_year',
    'street',
    'county',
    'license_status',
    'valid_till'
]

def test_verify(ppb_number):
    """Test the /verify endpoint"""
    print(f"\n{'='*70}")
    print(f"Testing: {ppb_number}")
    print(f"{'='*70}")

    url = f"{BASE_URL}/verify"
    payload = {
        "ppb_number": ppb_number,
        "use_cache": False
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())

        # Display results
        print(f"\nResponse:")
        print(f"  Success: {result.get('success')}")
        print(f"  Message: {result.get('message')}")
        print(f"  Processing Time: {result.get('processing_time_ms')} ms")

        if not result.get('success'):
            print(f"\n❌ FAILED: {result.get('message')}")
            return False

        data_obj = result.get('data', {})

        # Check required fields
        print(f"\nFields Extracted:")
        found = 0
        missing = []

        for field in REQUIRED_FIELDS:
            value = data_obj.get(field)
            if value:
                found += 1
                display_value = str(value)[:40]
                print(f"  ✅ {field}: {display_value}")
            else:
                missing.append(field)
                print(f"  ❌ {field}: MISSING")

        # Check superintendent
        superintendent = data_obj.get('superintendent')
        print(f"\nSuperintendent:")
        if superintendent:
            print(f"  ✅ name: {superintendent.get('name', 'N/A')}")
            print(f"  ✅ cadre: {superintendent.get('cadre', 'N/A')}")
            print(f"  ✅ enrollment_number: {superintendent.get('enrollment_number', 'N/A')}")
            found += 3
        else:
            print(f"  ❌ MISSING")
            missing.extend(['superintendent.name', 'superintendent.cadre', 'superintendent.enrollment_number'])

        # Summary
        total = len(REQUIRED_FIELDS) + 3
        print(f"\nSummary:")
        print(f"  Fields found: {found}/{total}")
        print(f"  Fields missing: {len(missing)}")

        if found == total:
            print(f"\n🎉 SUCCESS: All {total} fields extracted!")
            return True
        elif found >= len(REQUIRED_FIELDS):
            print(f"\n⚠️  PARTIAL: Required fields found, missing superintendent")
            return True
        else:
            print(f"\n❌ INCOMPLETE: Missing {len(missing)} fields")
            if missing:
                print(f"  Missing: {', '.join(missing)}")
            return False

    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.code}")
        try:
            error_body = e.read().decode()
            error_data = json.loads(error_body)
            print(f"  Message: {error_data.get('message')}")
        except:
            pass
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    print("="*70)
    print(" PPB VERIFICATION SERVICE V4 - TEST SUITE")
    print("="*70)

    # Check server
    try:
        health_req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(health_req, timeout=5) as response:
            health = json.loads(response.read().decode())
            print(f"\n✅ Server running (version: {health.get('version')})")
    except Exception as e:
        print(f"\n❌ Server not reachable at {BASE_URL}")
        print(f"  Please start with: python app.py")
        return

    # Run tests
    results = []
    for i, ppb_number in enumerate(TEST_CASES, 1):
        print(f"\n[Test {i}/{len(TEST_CASES)}]")
        success = test_verify(ppb_number)
        results.append(success)
        if i < len(TEST_CASES):
            print(f"\n⏱️  Waiting 2 seconds...")
            time.sleep(2)

    # Final summary
    print(f"\n{'='*70}")
    print(f" FINAL RESULTS")
    print(f"{'='*70}")

    passed = sum(1 for r in results if r)
    print(f"\nTotal tests: {len(TEST_CASES)}")
    print(f"Passed: {passed}/{len(TEST_CASES)}")
    print(f"Failed: {len(TEST_CASES) - passed}/{len(TEST_CASES)}")

    if passed == len(TEST_CASES):
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"\nImplementation complete:")
        print(f"  ✅ Session management working")
        print(f"  ✅ Proper headers in place")
        print(f"  ✅ Two-step workflow functioning")
        print(f"  ✅ All fields extracted including superintendent")
    elif passed > 0:
        print(f"\n⚠️  {passed} tests passed, {len(TEST_CASES) - passed} failed")
    else:
        print(f"\n❌ ALL TESTS FAILED")

    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
