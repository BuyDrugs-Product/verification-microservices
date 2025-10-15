"""
Performance Tests
Tests response times and performance characteristics
"""

import pytest
import time
import statistics
from tests.conftest import REAL_PHARMTECH_TEST_CASES, PERFORMANCE_THRESHOLDS


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.performance
class TestPerformance:
    """Test performance characteristics of the verification service"""

    def test_uncached_response_time(self, service, performance_thresholds):
        """Test that uncached verifications complete within acceptable time"""
        max_time = performance_thresholds["max_response_time"] / 1000  # Convert to seconds

        for test_case in REAL_PHARMTECH_TEST_CASES:
            start_time = time.time()
            result = service.verify_license_detailed(
                test_case["license_number"],
                use_cache=False
            )
            end_time = time.time()

            elapsed = end_time - start_time
            assert elapsed < max_time, f"Response took {elapsed:.2f}s, expected < {max_time}s"
            assert result["success"] is True

            print(f"\n⏱️  {test_case['license_number']}: {elapsed*1000:.2f}ms")

    def test_cached_response_time(self, cached_service, performance_thresholds):
        """Test that cached responses are significantly faster"""
        license_number = "PT2025D09630"
        max_cached_time = performance_thresholds["cached_response_time"] / 1000

        # First request (uncached)
        result1 = cached_service.verify_license_detailed(license_number, use_cache=True)
        assert result1["success"] is True
        assert result1["from_cache"] is False

        # Second request (cached)
        start_time = time.time()
        result2 = cached_service.verify_license_detailed(license_number, use_cache=True)
        end_time = time.time()

        elapsed = end_time - start_time
        assert result2["from_cache"] is True
        assert elapsed < max_cached_time, f"Cached response took {elapsed:.3f}s, expected < {max_cached_time}s"

        print(f"\n⚡ Cached response: {elapsed*1000:.2f}ms")

    def test_average_response_time(self, service, performance_thresholds):
        """Test that average response time is acceptable"""
        max_avg = performance_thresholds["average_response_time"] / 1000
        times = []

        for test_case in REAL_PHARMTECH_TEST_CASES:
            start_time = time.time()
            result = service.verify_license_detailed(
                test_case["license_number"],
                use_cache=False
            )
            end_time = time.time()

            if result["success"]:
                times.append(end_time - start_time)

        avg_time = statistics.mean(times)
        assert avg_time < max_avg, f"Average time {avg_time:.2f}s exceeds {max_avg}s"

        print(f"\n📊 Average response time: {avg_time*1000:.2f}ms")
        print(f"   Min: {min(times)*1000:.2f}ms")
        print(f"   Max: {max(times)*1000:.2f}ms")

    def test_processing_time_accuracy(self, service):
        """Test that reported processing_time_ms is accurate"""
        for test_case in REAL_PHARMTECH_TEST_CASES[:1]:  # Test one case
            start_time = time.time()
            result = service.verify_license_detailed(
                test_case["license_number"],
                use_cache=False
            )
            end_time = time.time()

            actual_time = (end_time - start_time) * 1000
            reported_time = result["processing_time_ms"]

            # Reported time should be within 10% of actual time
            tolerance = actual_time * 0.1
            diff = abs(actual_time - reported_time)

            assert diff < tolerance, f"Reported {reported_time}ms vs actual {actual_time}ms"

    def test_consecutive_requests_performance(self, service):
        """Test that consecutive requests maintain performance"""
        license_number = "PT2025D09630"
        times = []

        # Make 3 consecutive requests
        for i in range(3):
            start_time = time.time()
            result = service.verify_license_detailed(license_number, use_cache=False)
            end_time = time.time()

            times.append((end_time - start_time) * 1000)
            assert result["success"] is True

            # Rate limiting delay
            time.sleep(0.5)

        # Performance shouldn't degrade significantly
        first_time = times[0]
        last_time = times[-1]

        # Last request should be within 50% of first request time
        assert last_time < first_time * 1.5, "Performance degraded significantly"

        print(f"\n🔁 Consecutive requests: {', '.join(f'{t:.0f}ms' for t in times)}")

    def test_error_response_performance(self, service):
        """Test that error responses are fast (no PPB portal overhead)"""
        start_time = time.time()
        result = service.verify_license_detailed("INVALID123", use_cache=False)
        end_time = time.time()

        elapsed = (end_time - start_time) * 1000

        # Error responses should be very fast (< 100ms)
        assert elapsed < 100, f"Error response took {elapsed:.2f}ms"
        assert result["success"] is False

        print(f"\n⚠️  Error response time: {elapsed:.2f}ms")


@pytest.mark.unit
class TestPerformanceMetrics:
    """Test that performance metrics are properly tracked"""

    def test_processing_time_is_positive(self, service):
        """Test that processing_time_ms is always positive"""
        result = service.verify_license_detailed("PT2025D09630", use_cache=False)

        assert result["processing_time_ms"] > 0
        assert isinstance(result["processing_time_ms"], (int, float))

    def test_processing_time_for_cached_responses(self, cached_service):
        """Test that cached responses also report processing time"""
        license_number = "PT2025D09630"

        # First request
        result1 = cached_service.verify_license_detailed(license_number, use_cache=True)
        time1 = result1["processing_time_ms"]

        # Cached request
        result2 = cached_service.verify_license_detailed(license_number, use_cache=True)
        time2 = result2["processing_time_ms"]

        # Both should have processing times
        assert time1 > 0
        assert time2 > 0

        # Cached should be significantly faster
        assert time2 < time1 / 5, "Cached response not significantly faster"
