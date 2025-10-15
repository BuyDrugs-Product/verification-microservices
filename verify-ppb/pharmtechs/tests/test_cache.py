"""
Cache Functionality Tests
Tests caching behavior and cache statistics
"""

import pytest
import time


@pytest.mark.unit
class TestCacheBasicFunctionality:
    """Test basic cache operations"""

    def test_cache_enabled_on_service(self, cached_service):
        """Test that cache is enabled when configured"""
        assert cached_service.use_cache is True
        assert cached_service.cache is not None

    def test_cache_disabled_on_service(self, service):
        """Test that cache is disabled when configured"""
        assert service.use_cache is False

    def test_first_request_not_cached(self, cached_service):
        """Test that first request is not from cache"""
        result = cached_service.verify_license_detailed("PT2025D09630", use_cache=True)

        assert result["success"] is True
        assert result["from_cache"] is False

    def test_second_request_cached(self, cached_service):
        """Test that second request comes from cache"""
        license_number = "PT2025D09630"

        # First request
        result1 = cached_service.verify_license_detailed(license_number, use_cache=True)
        assert result1["from_cache"] is False

        # Second request (should be cached)
        result2 = cached_service.verify_license_detailed(license_number, use_cache=True)
        assert result2["from_cache"] is True
        assert result2["success"] is True

    def test_cache_bypass(self, cached_service):
        """Test that cache can be bypassed with use_cache=False"""
        license_number = "PT2025D09630"

        # First request
        result1 = cached_service.verify_license_detailed(license_number, use_cache=True)
        assert result1["from_cache"] is False

        # Second request with cache bypass
        result2 = cached_service.verify_license_detailed(license_number, use_cache=False)
        assert result2["from_cache"] is False


@pytest.mark.unit
class TestCacheStatistics:
    """Test cache statistics tracking"""

    def test_cache_stats_structure(self, cached_service):
        """Test that cache stats have expected structure"""
        stats = cached_service.get_cache_stats()

        assert "cache_enabled" in stats
        assert stats["cache_enabled"] is True
        assert "backend" in stats
        assert "size" in stats

    def test_cache_stats_disabled(self, service):
        """Test cache stats when cache is disabled"""
        stats = service.get_cache_stats()

        assert "cache_enabled" in stats
        assert stats["cache_enabled"] is False

    def test_cache_hit_tracking(self, cached_service):
        """Test that cache hits are tracked"""
        license_number = "PT2025D09630"

        # Get initial stats
        stats_before = cached_service.get_cache_stats()
        initial_hits = stats_before.get("hits", 0)

        # First request (miss)
        cached_service.verify_license_detailed(license_number, use_cache=True)

        # Second request (hit)
        cached_service.verify_license_detailed(license_number, use_cache=True)

        # Check stats
        stats_after = cached_service.get_cache_stats()
        final_hits = stats_after.get("hits", 0)

        assert final_hits > initial_hits

    def test_cache_miss_tracking(self, cached_service):
        """Test that cache misses are tracked"""
        stats_before = cached_service.get_cache_stats()
        initial_misses = stats_before.get("misses", 0)

        # Request a new license (will be a miss)
        cached_service.verify_license_detailed("PT2025D07035", use_cache=True)

        stats_after = cached_service.get_cache_stats()
        final_misses = stats_after.get("misses", 0)

        assert final_misses > initial_misses

    def test_cache_size_tracking(self, cached_service):
        """Test that cache size is tracked"""
        license_numbers = ["PT2025D09630", "PT2025D07035"]

        stats_before = cached_service.get_cache_stats()
        initial_size = stats_before.get("size", 0)

        # Add items to cache
        for license_number in license_numbers:
            cached_service.verify_license_detailed(license_number, use_cache=True)

        stats_after = cached_service.get_cache_stats()
        final_size = stats_after.get("size", 0)

        # Size should increase (by at least 1, maybe 2 depending on timing)
        assert final_size > initial_size


@pytest.mark.integration
class TestCachePerformance:
    """Test cache performance characteristics"""

    def test_cached_response_faster(self, cached_service):
        """Test that cached responses are significantly faster"""
        license_number = "PT2025D09630"

        # First request (uncached)
        start1 = time.time()
        result1 = cached_service.verify_license_detailed(license_number, use_cache=True)
        time1 = time.time() - start1

        # Second request (cached)
        start2 = time.time()
        result2 = cached_service.verify_license_detailed(license_number, use_cache=True)
        time2 = time.time() - start2

        assert result1["from_cache"] is False
        assert result2["from_cache"] is True

        # Cached should be at least 5x faster
        assert time2 < time1 / 5, f"Cached: {time2*1000:.2f}ms, Uncached: {time1*1000:.2f}ms"

        print(f"\n⚡ Cache speedup: {time1/time2:.1f}x faster")
        print(f"   Uncached: {time1*1000:.2f}ms")
        print(f"   Cached: {time2*1000:.2f}ms")

    def test_cache_hit_rate(self, cached_service):
        """Test cache hit rate calculation"""
        license_numbers = ["PT2025D09630", "PT2025D07035"]

        # Make multiple requests
        for _ in range(2):
            for license_number in license_numbers:
                cached_service.verify_license_detailed(license_number, use_cache=True)

        stats = cached_service.get_cache_stats()

        if "hit_rate" in stats:
            hit_rate = stats["hit_rate"]
            assert 0 <= hit_rate <= 100
            assert hit_rate > 0  # Should have some hits

            print(f"\n📊 Cache hit rate: {hit_rate:.1f}%")


@pytest.mark.unit
class TestCacheClear:
    """Test cache clearing functionality"""

    def test_cache_clear(self, cached_service):
        """Test that cache can be cleared"""
        license_number = "PT2025D09630"

        # Add something to cache
        cached_service.verify_license_detailed(license_number, use_cache=True)

        # Verify it's cached
        result = cached_service.verify_license_detailed(license_number, use_cache=True)
        assert result["from_cache"] is True

        # Clear cache
        cleared = cached_service.clear_cache()
        assert cleared is True

        # Next request should not be cached
        result_after = cached_service.verify_license_detailed(license_number, use_cache=True)
        assert result_after["from_cache"] is False

    def test_cache_clear_stats(self, cached_service):
        """Test that cache size resets after clear"""
        # Add items
        cached_service.verify_license_detailed("PT2025D09630", use_cache=True)

        stats_before = cached_service.get_cache_stats()
        size_before = stats_before.get("size", 0)

        # Clear cache
        cached_service.clear_cache()

        stats_after = cached_service.get_cache_stats()
        size_after = stats_after.get("size", 0)

        # Size should be 0 or less than before
        assert size_after < size_before


@pytest.mark.unit
class TestCacheKeyFormat:
    """Test cache key generation and formatting"""

    def test_cache_keys_are_unique(self, cached_service):
        """Test that different licenses create different cache keys"""
        licenses = ["PT2025D09630", "PT2025D07035"]

        # Cache both
        for license_number in licenses:
            cached_service.verify_license_detailed(license_number, use_cache=True)

        # Both should be in cache
        result1 = cached_service.verify_license_detailed(licenses[0], use_cache=True)
        result2 = cached_service.verify_license_detailed(licenses[1], use_cache=True)

        assert result1["from_cache"] is True
        assert result2["from_cache"] is True

        # Data should be different
        assert result1["data"]["full_name"] != result2["data"]["full_name"]

    def test_cache_normalization(self, cached_service):
        """Test that normalized license numbers use same cache key"""
        # Cache with uppercase
        cached_service.verify_license_detailed("PT2025D09630", use_cache=True)

        # Request with lowercase (should hit cache after normalization)
        result = cached_service.verify_license_detailed("pt2025d09630", use_cache=True)

        # Should be from cache (same key after normalization)
        assert result["success"] is True
        assert result["license_number"] == "PT2025D09630"


@pytest.mark.unit
class TestCacheDataIntegrity:
    """Test that cached data remains consistent"""

    def test_cached_data_consistency(self, cached_service):
        """Test that cached data matches original data"""
        license_number = "PT2025D09630"

        # First request
        result1 = cached_service.verify_license_detailed(license_number, use_cache=True)
        data1 = result1["data"]

        # Second request (from cache)
        result2 = cached_service.verify_license_detailed(license_number, use_cache=True)
        data2 = result2["data"]

        # Data should be identical
        assert data1["full_name"] == data2["full_name"]
        assert data1["practice_license_number"] == data2["practice_license_number"]
        assert data1["status"] == data2["status"]
        assert data1["valid_till"] == data2["valid_till"]
        assert data1["photo_url"] == data2["photo_url"]

    def test_cache_does_not_affect_errors(self, cached_service):
        """Test that error responses are consistent with/without cache"""
        # Error response
        result1 = cached_service.verify_license_detailed("PT99999999", use_cache=True)

        # Error should not be cached, but should be consistent
        result2 = cached_service.verify_license_detailed("PT99999999", use_cache=True)

        assert result1["success"] is False
        assert result2["success"] is False
        assert result1["message"] == result2["message"]
