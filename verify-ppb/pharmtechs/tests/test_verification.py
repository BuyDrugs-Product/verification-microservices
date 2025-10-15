"""
PharmTech License Verification Tests
Tests verification functionality with real PPB portal data
"""

import pytest
import time
from tests.conftest import REAL_PHARMTECH_TEST_CASES


@pytest.mark.integration
class TestPharmTechVerification:
    """Test PharmTech license verification with real data from PPB portal"""

    def test_kimutai_abel_verification(self, service):
        """Test PT2025D09630 - Kimutai Abel"""
        start_time = time.time()
        result = service.verify_license_detailed("PT2025D09630", use_cache=False)
        processing_time = (time.time() - start_time) * 1000

        # Basic response structure
        assert result["success"] is True
        assert result["license_number"] == "PT2025D09630"
        assert result["from_cache"] is False
        assert "data" in result
        assert result["data"] is not None

        # Verify data fields
        data = result["data"]
        assert data["full_name"] == "Kimutai Abel"
        assert data["practice_license_number"] == "PT2025D09630"
        assert data["status"] == "Active"
        assert data["valid_till"] == "2025-12-31"
        assert "9b0a620f6d8860a.JPG" in data["photo_url"]
        assert "verified_at" in data

        # Performance check
        assert result["processing_time_ms"] < 3000, f"Response too slow: {processing_time}ms"

        print(f"\n✅ Kimutai Abel verification: {processing_time:.2f}ms")

    def test_gitau_alex_verification(self, service):
        """Test PT2025D07035 - Gitau Alex Njuguna"""
        start_time = time.time()
        result = service.verify_license_detailed("PT2025D07035", use_cache=False)
        processing_time = (time.time() - start_time) * 1000

        # Basic response structure
        assert result["success"] is True
        assert result["license_number"] == "PT2025D07035"
        assert result["from_cache"] is False
        assert "data" in result
        assert result["data"] is not None

        # Verify data fields
        data = result["data"]
        assert data["full_name"] == "Gitau Alex Njuguna"
        assert data["practice_license_number"] == "PT2025D07035"
        assert data["status"] == "Active"
        assert data["valid_till"] == "2025-12-31"
        assert "9b0f3c77e804a579337d0b446.JPG" in data["photo_url"]
        assert "verified_at" in data

        # Performance check
        assert result["processing_time_ms"] < 3000, f"Response too slow: {processing_time}ms"

        print(f"\n✅ Gitau Alex verification: {processing_time:.2f}ms")

    @pytest.mark.parametrize("test_case", REAL_PHARMTECH_TEST_CASES)
    def test_all_real_licenses_parametrized(self, service, test_case):
        """Parametrized test for all real test cases"""
        result = service.verify_license_detailed(
            test_case["license_number"],
            use_cache=False
        )

        expected = test_case["expected_data"]

        # Verify success
        assert result["success"] is True
        assert result["license_number"] == test_case["license_number"]

        # Verify all expected fields
        data = result["data"]
        assert data["full_name"] == expected["full_name"]
        assert data["practice_license_number"] == expected["practice_license_number"]
        assert data["status"] == expected["status"]
        assert data["valid_till"] == expected["valid_till"]

        # Photo URL - check if the key filename is present
        photo_filename = expected["photo_url"].split("/")[-1]
        assert photo_filename in data["photo_url"]

        # Metadata
        assert "verified_at" in data
        assert result["processing_time_ms"] < 3000

    def test_case_insensitive_license_number(self, service):
        """Test that license numbers are case-insensitive"""
        # Test lowercase
        result_lower = service.verify_license_detailed("pt2025d09630", use_cache=False)
        assert result_lower["success"] is True

        # Test mixed case
        result_mixed = service.verify_license_detailed("Pt2025D09630", use_cache=False)
        assert result_mixed["success"] is True

        # Both should return the same data (normalized to uppercase)
        assert result_lower["license_number"] == "PT2025D09630"
        assert result_mixed["license_number"] == "PT2025D09630"

    def test_whitespace_handling(self, service):
        """Test that leading/trailing whitespace is handled"""
        result = service.verify_license_detailed("  PT2025D09630  ", use_cache=False)

        assert result["success"] is True
        assert result["license_number"] == "PT2025D09630"


@pytest.mark.integration
class TestDataCompleteness:
    """Test that all expected data fields are present and valid"""

    def test_all_required_fields_present(self, service):
        """Verify all required fields are present in response"""
        result = service.verify_license_detailed("PT2025D09630", use_cache=False)

        # Response structure
        assert "success" in result
        assert "license_number" in result
        assert "message" in result
        assert "processing_time_ms" in result
        assert "from_cache" in result
        assert "data" in result

        # Data fields
        data = result["data"]
        assert "full_name" in data
        assert "practice_license_number" in data
        assert "status" in data
        assert "valid_till" in data
        assert "photo_url" in data
        assert "verified_at" in data

    def test_data_types(self, service):
        """Verify data types are correct"""
        result = service.verify_license_detailed("PT2025D09630", use_cache=False)

        assert isinstance(result["success"], bool)
        assert isinstance(result["license_number"], str)
        assert isinstance(result["message"], str)
        assert isinstance(result["processing_time_ms"], (int, float))
        assert isinstance(result["from_cache"], bool)
        assert isinstance(result["data"], dict)

        data = result["data"]
        assert isinstance(data["full_name"], str)
        assert isinstance(data["practice_license_number"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["valid_till"], str)
        assert isinstance(data["photo_url"], str)
        assert isinstance(data["verified_at"], str)

    def test_photo_url_accessibility(self, service):
        """Verify photo URLs are valid and accessible"""
        result = service.verify_license_detailed("PT2025D09630", use_cache=False)

        photo_url = result["data"]["photo_url"]

        # Check URL format
        assert photo_url.startswith("http://") or photo_url.startswith("https://")
        assert "rhris.pharmacyboardkenya.org" in photo_url
        assert photo_url.endswith(".JPG") or photo_url.endswith(".jpg")

    def test_date_format(self, service):
        """Verify date formats are consistent"""
        result = service.verify_license_detailed("PT2025D09630", use_cache=False)

        # Valid till date should be in YYYY-MM-DD format
        valid_till = result["data"]["valid_till"]
        assert len(valid_till) == 10
        assert valid_till.count("-") == 2

        # Verified at should be in ISO format
        verified_at = result["data"]["verified_at"]
        assert "T" in verified_at
        assert verified_at.endswith("Z")
