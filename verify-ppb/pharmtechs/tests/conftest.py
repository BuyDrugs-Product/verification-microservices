"""
Pytest configuration and shared fixtures
Provides test data, fixtures, and utilities for the test suite
"""

import pytest
from src.services.ppb_service import PPBService


# Real test data from PPB portal
REAL_PHARMTECH_TEST_CASES = [
    {
        "license_number": "PT2025D09630",
        "expected_data": {
            "full_name": "Kimutai Abel",
            "practice_license_number": "PT2025D09630",
            "status": "Active",
            "valid_till": "2025-12-31",
            "photo_url": "http://rhris.pharmacyboardkenya.org/photos/9b0a620f6d8860a.JPG"
        },
        "description": "Kimutai Abel - Active license with photo"
    },
    {
        "license_number": "PT2025D07035",
        "expected_data": {
            "full_name": "Gitau Alex Njuguna",
            "practice_license_number": "PT2025D07035",
            "status": "Active",
            "valid_till": "2025-12-31",
            "photo_url": "http://rhris.pharmacyboardkenya.org/photos/9b0f3c77e804a579337d0b446.JPG"
        },
        "description": "Gitau Alex Njuguna - Active license with photo"
    }
]

ERROR_TEST_CASES = [
    {
        "license_number": "PT2025D99999",
        "expected_error": "not found",
        "description": "Non-existent license number"
    },
    {
        "license_number": "INVALID123",
        "expected_error": "Invalid license number format",
        "description": "Malformed license - invalid format"
    },
    {
        "license_number": "PT2025",
        "expected_error": "Invalid license number format",
        "description": "Malformed license - too short"
    },
    {
        "license_number": "PT2099D12345",
        "expected_error": "Invalid license number format",
        "description": "Malformed license - invalid year"
    }
]

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "max_response_time": 3000,  # 3 seconds in milliseconds
    "cached_response_time": 200,  # 200ms for cached responses
    "average_response_time": 2500  # 2.5 seconds average
}


@pytest.fixture
def service():
    """Create PPBService instance with cache disabled for testing"""
    return PPBService(
        use_cache=False,
        rate_limit_delay=0.5  # Reduced delay for faster tests
    )


@pytest.fixture
def cached_service():
    """Create PPBService instance with cache enabled for cache tests"""
    return PPBService(
        use_cache=True,
        cache_backend="simple",
        cache_ttl=300,  # 5 minutes
        rate_limit_delay=0.5
    )


@pytest.fixture
def real_test_cases():
    """Provide real test cases for verification"""
    return REAL_PHARMTECH_TEST_CASES


@pytest.fixture
def error_test_cases():
    """Provide error test cases"""
    return ERROR_TEST_CASES


@pytest.fixture
def performance_thresholds():
    """Provide performance threshold values"""
    return PERFORMANCE_THRESHOLDS


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires PPB portal access)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance benchmark"
    )
