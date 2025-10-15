"""
Pydantic models for request/response validation
Provides automatic validation, serialization, and OpenAPI schema generation
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class VerifyRequest(BaseModel):
    """Request model for pharmtech license verification"""

    license_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="PharmTech license number (e.g., PT2025D05614)",
        examples=["PT2025D05614"],
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to use cached results if available",
    )

    @field_validator("license_number")
    @classmethod
    def normalize_license_number(cls, v: str) -> str:
        """Normalize license number by stripping whitespace and converting to uppercase"""
        return v.strip().upper()


class PharmTechData(BaseModel):
    """Complete pharmtech verification data"""

    full_name: Optional[str] = Field(None, description="PharmTech's full name (formatted)")
    name: Optional[str] = Field(None, description="PharmTech's name from search")
    practice_license_number: Optional[str] = Field(None, description="Practice license number")
    license_number: Optional[str] = Field(None, description="License number from search")
    status: str = Field(..., description="Current license status (e.g., Active, Expired)")
    valid_till: str = Field(..., description="License expiry date (YYYY-MM-DD)")
    photo_url: Optional[str] = Field(None, description="URL to pharmtech's photo")
    verified_at: str = Field(..., description="Timestamp of verification in ISO format")


class VerifyResponse(BaseModel):
    """Response model for pharmtech license verification"""

    success: bool = Field(..., description="Whether verification was successful")
    license_number: str = Field(..., description="License number that was verified")
    message: str = Field(..., description="Human-readable message about the result")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    from_cache: bool = Field(..., description="Whether result was served from cache")
    data: Optional[PharmTechData] = Field(
        None, description="PharmTech data (null if verification failed)"
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
