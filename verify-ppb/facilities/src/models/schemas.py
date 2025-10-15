"""
Pydantic models for request/response validation
Provides automatic validation, serialization, and OpenAPI schema generation
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class VerifyRequest(BaseModel):
    """Request model for license verification"""

    ppb_number: str = Field(
        ...,
        min_length=5,
        max_length=50,
        description="PPB registration number (e.g., PPB/C/9222)",
        examples=["PPB/C/9222"],
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to use cached results if available",
    )

    @field_validator("ppb_number")
    @classmethod
    def normalize_ppb_number(cls, v: str) -> str:
        """Normalize PPB number by stripping whitespace"""
        return v.strip()


class SuperintendentData(BaseModel):
    """Superintendent information"""

    name: str = Field(..., description="Superintendent's full name")
    cadre: str = Field(..., description="Professional cadre (e.g., PHARMACIST, PHARMTECH)")
    enrollment_number: str = Field(..., description="Professional enrollment/registration number")


class FacilityData(BaseModel):
    """Complete facility verification data"""

    facility_name: str = Field(..., description="Name of the facility")
    registration_number: str = Field(..., description="PPB registration number")
    license_number: str = Field(..., description="Current license number")
    ownership: str = Field(..., description="Ownership type")
    license_type: str = Field(..., description="Type of license (e.g., RETAIL, HOSPITAL)")
    establishment_year: str = Field(..., description="Year the facility was established")
    street: str = Field(..., description="Street address")
    county: str = Field(..., description="County location")
    license_status: str = Field(..., description="Current license status (e.g., VALID, EXPIRED)")
    valid_till: str = Field(..., description="License expiry date")
    superintendent: Optional[SuperintendentData] = Field(
        None, description="Superintendent information (if available)"
    )
    verified_at: str = Field(..., description="Timestamp of verification in ISO format")


class VerifyResponse(BaseModel):
    """Response model for license verification"""

    success: bool = Field(..., description="Whether verification was successful")
    ppb_number: str = Field(..., description="PPB registration number that was verified")
    message: str = Field(..., description="Human-readable message about the result")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    from_cache: bool = Field(..., description="Whether result was served from cache")
    data: Optional[FacilityData] = Field(
        None, description="Facility data (null if verification failed)"
    )


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Current timestamp")
    cache: dict = Field(..., description="Cache statistics")


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = Field(default=False, description="Always false for errors")
    message: str = Field(..., description="Error message")
    data: Optional[dict] = Field(default=None, description="Always null for errors")

