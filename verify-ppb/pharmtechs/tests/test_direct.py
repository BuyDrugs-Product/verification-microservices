#!/usr/bin/env python3
"""
PharmTech Verification Test Suite - Direct Test Runner
Professional test runner matching facilities service quality

Run with: python tests/test_direct.py
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.ppb_service import PPBService
from tests.conftest import REAL_PHARMTECH_TEST_CASES, ERROR_TEST_CASES, PERFORMANCE_THRESHOLDS


class Colors:
    """Terminal colors for output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print("=" * 70)


def print_success(text: str):
    """Print success message"""
    print(f"   {Colors.GREEN}✅ {text}{Colors.END}")


def print_failure(text: str):
    """Print failure message"""
    print(f"   {Colors.RED}❌ {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"   {Colors.BLUE}ℹ️  {text}{Colors.END}")


def validate_verification_result(result: Dict, test_case: Dict) -> Tuple[bool, str]:
    """
    Validate successful verification results

    Returns:
        Tuple of (is_valid, error_message)
    """
    expected = test_case["expected_data"]

    checks = [
        (result.get("success") == True, "Success flag not True"),
        (result.get("license_number") == test_case["license_number"], "License number mismatch"),
        (result.get("data", {}).get("full_name") == expected["full_name"],
         f"Name mismatch: got '{result.get('data', {}).get('full_name')}', expected '{expected['full_name']}'"),
        (result.get("data", {}).get("practice_license_number") == expected["practice_license_number"],
         "Practice license number mismatch"),
        (result.get("data", {}).get("status") == expected["status"], "Status mismatch"),
        (result.get("data", {}).get("valid_till") == expected["valid_till"], "Valid till date mismatch"),
        (expected["photo_url"].split("/")[-1] in result.get("data", {}).get("photo_url", ""),
         "Photo URL mismatch"),
        (result.get("processing_time_ms", 0) < PERFORMANCE_THRESHOLDS["max_response_time"],
         f"Response time {result.get('processing_time_ms')}ms exceeds {PERFORMANCE_THRESHOLDS['max_response_time']}ms"),
    ]

    for check, error_msg in checks:
        if not check:
            return False, error_msg

    return True, ""


def validate_error_result(result: Dict, test_case: Dict) -> Tuple[bool, str]:
    """
    Validate error handling results

    Returns:
        Tuple of (is_valid, error_message)
    """
    if result.get("success") != False:
        return False, "Success flag should be False for errors"

    if test_case["expected_error"].lower() not in result.get("message", "").lower():
        return False, f"Expected error message not found: '{test_case['expected_error']}'"

    if result.get("data") is not None:
        return False, "Data should be None for errors"

    return True, ""


def test_valid_license_verification(service: PPBService) -> Dict:
    """Test valid license verification with real data"""
    print_header("1. TESTING VALID LICENSE VERIFICATION")

    results = {
        'passed': 0,
        'failed': 0,
        'times': []
    }

    for test_case in REAL_PHARMTECH_TEST_CASES:
        license_number = test_case["license_number"]
        description = test_case.get("description", license_number)

        start_time = time.time()
        result = service.verify_license_detailed(license_number, use_cache=False)
        end_time = time.time()

        processing_time = (end_time - start_time) * 1000
        results['times'].append(processing_time)

        is_valid, error_msg = validate_verification_result(result, test_case)

        if is_valid:
            print_success(f"{description}: PASSED ({processing_time:.2f}ms)")
            results['passed'] += 1

            # Print key data
            data = result.get("data", {})
            print_info(f"Name: {data.get('full_name')}")
            print_info(f"Status: {data.get('status')} until {data.get('valid_till')}")
        else:
            print_failure(f"{description}: FAILED - {error_msg}")
            results['failed'] += 1

    return results


def test_error_handling(service: PPBService) -> Dict:
    """Test error handling scenarios"""
    print_header("2. TESTING ERROR HANDLING")

    results = {
        'passed': 0,
        'failed': 0
    }

    for test_case in ERROR_TEST_CASES:
        license_number = test_case["license_number"]
        description = test_case.get("description", license_number)

        result = service.verify_license_detailed(license_number, use_cache=False)
        is_valid, error_msg = validate_error_result(result, test_case)

        if is_valid:
            print_success(f"{description}: Correctly handled")
            results['passed'] += 1
        else:
            print_failure(f"{description}: {error_msg}")
            results['failed'] += 1

    return results


def test_performance(service: PPBService) -> Dict:
    """Test performance benchmarks"""
    print_header("3. TESTING PERFORMANCE")

    results = {
        'passed': 0,
        'failed': 0
    }

    max_time = PERFORMANCE_THRESHOLDS["max_response_time"] / 1000

    print_info(f"Performance threshold: {max_time}s per request")

    all_pass = True
    for test_case in REAL_PHARMTECH_TEST_CASES:
        license_number = test_case["license_number"]

        start_time = time.time()
        result = service.verify_license_detailed(license_number, use_cache=False)
        elapsed = time.time() - start_time

        if elapsed > max_time:
            print_failure(f"{license_number}: Too slow ({elapsed:.2f}s > {max_time}s)")
            all_pass = False
        elif not result.get("success"):
            print_failure(f"{license_number}: Verification failed")
            all_pass = False

    if all_pass:
        print_success("All requests completed within threshold")
        results['passed'] = 1
    else:
        print_failure("Some requests exceeded performance threshold")
        results['failed'] = 1

    return results


def test_cache_functionality(cached_service: PPBService) -> Dict:
    """Test cache functionality"""
    print_header("4. TESTING CACHE FUNCTIONALITY")

    results = {
        'passed': 0,
        'failed': 0
    }

    license_number = "PT2025D09630"

    # First request (uncached)
    start1 = time.time()
    result1 = cached_service.verify_license_detailed(license_number, use_cache=True)
    time1 = (time.time() - start1) * 1000

    if result1.get("from_cache"):
        print_failure("First request should not be from cache")
        results['failed'] += 1
    else:
        print_success(f"First request (uncached): {time1:.2f}ms")
        results['passed'] += 1

    # Second request (cached)
    start2 = time.time()
    result2 = cached_service.verify_license_detailed(license_number, use_cache=True)
    time2 = (time.time() - start2) * 1000

    if not result2.get("from_cache"):
        print_failure("Second request should be from cache")
        results['failed'] += 1
    else:
        speedup = time1 / time2
        print_success(f"Second request (cached): {time2:.2f}ms ({speedup:.1f}x faster)")
        results['passed'] += 1

    # Cache stats
    stats = cached_service.get_cache_stats()
    if stats.get("cache_enabled"):
        print_info(f"Cache size: {stats.get('size', 0)}")
        print_info(f"Cache hit rate: {stats.get('hit_rate', 0):.1f}%")
        results['passed'] += 1
    else:
        print_failure("Cache not enabled")
        results['failed'] += 1

    return results


def print_summary(all_results: List[Dict], total_time: float):
    """Print test summary"""
    print_header("📊 TEST SUMMARY")

    total_passed = sum(r['passed'] for r in all_results)
    total_failed = sum(r['failed'] for r in all_results)
    total_tests = total_passed + total_failed

    print(f"\n   Tests Passed: {Colors.GREEN}{total_passed}{Colors.END}")
    print(f"   Tests Failed: {Colors.RED}{total_failed}{Colors.END}")
    print(f"   Total Tests:  {Colors.BOLD}{total_tests}{Colors.END}")
    print(f"   Total Time:   {Colors.CYAN}{total_time:.2f}s{Colors.END}")

    # Calculate average time from verification tests
    verification_results = all_results[0]
    if verification_results.get('times'):
        avg_time = sum(verification_results['times']) / len(verification_results['times'])
        print(f"   Average Time: {Colors.CYAN}{avg_time:.2f}ms{Colors.END}")

    print()

    if total_failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED!{Colors.END}\n")
        return 1


def run_tests():
    """Main test runner"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🧪 PHARMTECH VERIFICATION TEST SUITE{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")

    start_time = time.time()

    # Create service instances
    service = PPBService(use_cache=False, rate_limit_delay=0.5)
    cached_service = PPBService(use_cache=True, cache_backend="simple", rate_limit_delay=0.5)

    # Run test suites
    all_results = []

    try:
        # Test 1: Valid license verification
        results1 = test_valid_license_verification(service)
        all_results.append(results1)

        # Test 2: Error handling
        results2 = test_error_handling(service)
        all_results.append(results2)

        # Test 3: Performance
        results3 = test_performance(service)
        all_results.append(results3)

        # Test 4: Cache functionality
        results4 = test_cache_functionality(cached_service)
        all_results.append(results4)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        return 130
    except Exception as e:
        print(f"\n\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    total_time = time.time() - start_time
    return print_summary(all_results, total_time)


if __name__ == "__main__":
    sys.exit(run_tests())
