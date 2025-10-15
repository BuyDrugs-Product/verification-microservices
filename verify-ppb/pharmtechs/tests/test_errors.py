"""
Error Handling Tests
Tests error scenarios and edge cases
"""

import pytest
from tests.conftest import ERROR_TEST_CASES
from src.services.ppb_service import PPBService, PharmTechNotFoundError


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling for various invalid inputs"""

    def test_license_not_found(self, service):
        """Test non-existent license number"""
        result = service.verify_license_detailed("PT2025D99999", use_cache=False)

        assert result["success"] is False
        assert result["license_number"] == "PT2025D99999"
        assert result["data"] is None
        assert "not found" in result["message"].lower()
        assert result["processing_time_ms"] > 0

    def test_invalid_license_format(self, service):
        """Test malformed license number"""
        result = service.verify_license_detailed("INVALID123", use_cache=False)

        assert result["success"] is False
        assert result["license_number"] == "INVALID123"
        assert result["data"] is None
        assert "invalid" in result["message"].lower()
        assert "format" in result["message"].lower()

    def test_license_too_short(self, service):
        """Test license number that's too short"""
        result = service.verify_license_detailed("PT2025", use_cache=False)

        assert result["success"] is False
        assert "invalid" in result["message"].lower() or "format" in result["message"].lower()

    def test_invalid_year_format(self, service):
        """Test license with invalid year"""
        result = service.verify_license_detailed("PT2099D12345", use_cache=False)

        assert result["success"] is False
        assert "invalid" in result["message"].lower() or "format" in result["message"].lower()

    @pytest.mark.parametrize("test_case", ERROR_TEST_CASES)
    def test_all_error_cases_parametrized(self, service, test_case):
        """Parametrized test for all error cases"""
        result = service.verify_license_detailed(
            test_case["license_number"],
            use_cache=False
        )

        assert result["success"] is False
        assert result["data"] is None
        assert test_case["expected_error"].lower() in result["message"].lower()
        print(f"\n✅ {test_case['description']}: Properly handled")


@pytest.mark.unit
class TestInputValidation:
    """Test input validation logic"""

    def test_empty_license_number(self, service):
        """Test empty string license number"""
        result = service.verify_license_detailed("", use_cache=False)

        assert result["success"] is False
        assert result["data"] is None

    def test_none_license_number(self, service):
        """Test None as license number"""
        result = service.verify_license_detailed(None, use_cache=False)

        assert result["success"] is False
        assert result["data"] is None

    def test_numeric_only_license(self, service):
        """Test license with only numbers"""
        result = service.verify_license_detailed("12345678", use_cache=False)

        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_special_characters_in_license(self, service):
        """Test license with special characters"""
        result = service.verify_license_detailed("PT2025@#$%", use_cache=False)

        assert result["success"] is False

    def test_spaces_in_license_number(self, service):
        """Test license number with spaces in the middle"""
        result = service.verify_license_detailed("PT 2025 D 09630", use_cache=False)

        # Should handle this gracefully (either normalize or reject)
        assert "success" in result
        assert isinstance(result["success"], bool)


@pytest.mark.unit
class TestLicenseFormatValidation:
    """Test license number format validation function"""

    def test_validate_license_format_valid(self, service):
        """Test validation function with valid licenses"""
        assert service.validate_license_format("PT2025D09630") is True
        assert service.validate_license_format("PT2024A12345") is True
        assert service.validate_license_format("PT2023Z99999") is True
        assert service.validate_license_format("PT2026B00001") is True

    def test_validate_license_format_invalid(self, service):
        """Test validation function with invalid licenses"""
        assert service.validate_license_format("INVALID") is False
        assert service.validate_license_format("PT202D05614") is False
        assert service.validate_license_format("2025D05614") is False
        assert service.validate_license_format("PT2025D0561") is False
        assert service.validate_license_format("PT2099D12345") is False
        assert service.validate_license_format("") is False

    def test_validate_license_format_edge_cases(self, service):
        """Test validation with edge cases"""
        # Year boundaries
        assert service.validate_license_format("PT2023A00000") is True
        assert service.validate_license_format("PT2029Z99999") is True
        assert service.validate_license_format("PT2022A00000") is False  # Year too old
        assert service.validate_license_format("PT2030A00000") is False  # Year too new

        # Missing parts
        assert service.validate_license_format("PT2025D") is False
        assert service.validate_license_format("PT2025") is False
        assert service.validate_license_format("PT") is False


@pytest.mark.integration
class TestResponseStructure:
    """Test that error responses have consistent structure"""

    def test_error_response_structure(self, service):
        """Verify error responses have all required fields"""
        result = service.verify_license_detailed("PT2025D99999", use_cache=False)

        # Required fields
        assert "success" in result
        assert "license_number" in result
        assert "message" in result
        assert "processing_time_ms" in result
        assert "from_cache" in result
        assert "data" in result

        # Values for errors
        assert result["success"] is False
        assert result["data"] is None
        assert isinstance(result["message"], str)
        assert len(result["message"]) > 0

    def test_error_messages_are_descriptive(self, service):
        """Verify error messages provide useful information"""
        # Not found
        result_not_found = service.verify_license_detailed("PT2025D99999", use_cache=False)
        assert len(result_not_found["message"]) > 20
        assert "PT2025D99999" in result_not_found["message"] or "not found" in result_not_found["message"].lower()

        # Invalid format
        result_invalid = service.verify_license_detailed("INVALID123", use_cache=False)
        assert len(result_invalid["message"]) > 20
        assert "format" in result_invalid["message"].lower() or "invalid" in result_invalid["message"].lower()
