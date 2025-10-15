"""
PPB Pharmacist License Verification Service - Production Implementation
Two-step workflow with POST search and GET details

CRITICAL: This follows the same pattern as pharmtechs service but with:
- cadre_id: 2 (Pharmacists) instead of 4 (PharmTechs)
- License prefix: P instead of PT
- Same POST search + GET details workflow
- Photo URL extraction
"""

import re
import time
from typing import Dict, Optional
from datetime import datetime

from ..core.config import Config
from ..core.logger import get_logger
from ..adapters.http import build_session, RateLimiter
from ..adapters.cache_redis import get_cache

logger = get_logger(__name__)


class PPBVerificationError(Exception):
    """Base exception for PPB verification errors"""
    pass


class PharmacistNotFoundError(PPBVerificationError):
    """Raised when pharmacist is not found in registry"""
    pass


class PPBService:
    """PPB pharmacist license verification service"""

    def __init__(
        self,
        ppb_base_url: str = None,
        use_cache: bool = True,
        cache_backend: str = "simple",
        cache_ttl: int = None,
        rate_limit_delay: float = None,
        request_timeout: float = None,
        max_retries: int = None,
    ):
        """
        Initialize PPB Service with session management

        Args:
            ppb_base_url: PPB portal base URL (uses config default if None)
            use_cache: Whether to use caching
            cache_backend: Cache backend ('simple' or 'redis')
            cache_ttl: Cache TTL in seconds (uses config default if None)
            rate_limit_delay: Delay between requests (uses config default if None)
            request_timeout: Request timeout (uses config default if None)
            max_retries: Maximum retries (uses config default if None)
        """
        # Configuration with defaults from Config
        self.ppb_base_url = ppb_base_url or Config.PPB_BASE_URL
        self.ppb_search_url = f"{self.ppb_base_url}/ajax/public"
        self.timeout = request_timeout or Config.REQUEST_TIMEOUT
        self.max_retries = max_retries or Config.MAX_RETRIES

        # Session with retry logic
        self.session = build_session(
            max_retries=self.max_retries,
            backoff=Config.RETRY_BACKOFF
        )

        # Search headers - for POST search request
        self.search_headers = {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.ppb_base_url}/LicenseStatus?register=pharmacist"
        }

        # Details headers - for GET details request
        self.details_headers = {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": f"{self.ppb_base_url}/LicenseStatus?register=pharmacist",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Google Chrome";v="141", "Not-A-Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }

        # Rate limiter - CRITICAL: Prevents IP blocking
        delay = rate_limit_delay if rate_limit_delay is not None else Config.RATE_LIMIT_DELAY
        self.rate_limiter = RateLimiter(delay=delay)

        # Cache setup
        self.use_cache = use_cache and Config.CACHE_ENABLED
        if cache_ttl is None:
            cache_ttl = Config.CACHE_TTL
        self.cache_ttl = cache_ttl

        if self.use_cache:
            if cache_backend == "redis":
                self.cache = get_cache(
                    backend="redis",
                    redis_url=Config.REDIS_URL,
                    default_ttl=cache_ttl,
                    key_prefix="ppb:pharmacist:v1:"
                )
            else:
                self.cache = get_cache(
                    backend="simple",
                    max_size=Config.CACHE_MAX_SIZE,
                    default_ttl=cache_ttl
                )
            logger.info(f"Cache enabled: backend={cache_backend}, ttl={cache_ttl}s")
        else:
            self.cache = None
            logger.info("Cache disabled")

    def validate_license_format(self, license_number: str) -> bool:
        """
        Validate Pharmacist license number format

        Expected format: P + 4-digit year + letter + 5 digits
        Example: P2025D00463

        Args:
            license_number: License number to validate

        Returns:
            True if valid format, False otherwise
        """
        # Pattern: P + (2023-2029) + letter + 5 digits
        pattern = r'^P202[3-9][A-Z]\d{5}$'
        return bool(re.match(pattern, license_number, re.IGNORECASE))

    def search_pharmacist(self, license_number: str) -> Optional[str]:
        """
        STEP 1: Search for pharmacist using POST request

        Args:
            license_number: Pharmacist license number (e.g., P2025D00463)

        Returns:
            HTML response containing search results

        Raises:
            PPBVerificationError: If request fails
        """
        self.rate_limiter.wait()

        # Build POST payload - CRITICAL: These exact parameters are required
        payload = {
            "search_register": "1",
            "cadre_id": "2",  # Fixed value for Pharmacists
            "search_text": license_number
        }

        try:
            logger.debug(f"Searching PPB portal for: {license_number}")
            response = self.session.post(
                self.ppb_search_url,
                data=payload,
                headers=self.search_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.debug(f"Search successful for: {license_number}")
            return response.text

        except Exception as e:
            logger.error(f"Search failed for {license_number}: {str(e)}")
            raise PPBVerificationError(f"Failed to connect to PPB portal: {str(e)}")

    def extract_pharmacist_id(self, html: str) -> Optional[str]:
        """
        Extract encoded pharmacist ID from search results

        Looks for pattern: <a class="popStatus" href="#" rel='NDI5ODI='>

        Args:
            html: HTML response from search

        Returns:
            Base64-encoded pharmacist ID (e.g., "NDI5ODI=")
        """
        # Extract encoded ID from rel attribute
        id_match = re.search(r"rel='([^']+)'", html)
        if id_match:
            pharmacist_id = id_match.group(1)
            logger.debug(f"Extracted pharmacist ID: {pharmacist_id}")
            return pharmacist_id

        return None

    def extract_search_data(self, html: str) -> Dict:
        """
        Extract data from search results HTML

        Expected HTML structure:
        <tr style='background:#E0FEF2;'>
            <td>ACHEI BERYL GESARE</td>
            <td>P2025D00463</td>
            <td><span class='label label-success'>Status: Active</span> &nbsp; 2025-12-31</td>
            <td><a class="popStatus" href="#" rel='NDI5ODI='>View Details</a></td>
        </tr>

        Args:
            html: HTML response from search

        Returns:
            Dictionary with extracted search data
        """
        data = {}

        # Extract name (first <td> before license number)
        name_match = re.search(r"<td[^>]*>([^<]+)</td>\s*<td[^>]*>P", html, re.IGNORECASE)
        if name_match:
            data['name'] = name_match.group(1).strip()

        # Extract license number
        license_match = re.search(r"<td[^>]*>(P\d+[A-Z]\d+)</td>", html, re.IGNORECASE)
        if license_match:
            data['license_number'] = license_match.group(1).strip()

        # Extract status
        status_match = re.search(r"Status:\s*([^<]+)", html, re.IGNORECASE)
        if status_match:
            data['status'] = status_match.group(1).strip()

        # Extract valid_till date
        valid_till_match = re.search(r"&nbsp;\s*([\d-]+)</td>", html)
        if valid_till_match:
            data['valid_till'] = valid_till_match.group(1).strip()

        return data

    def get_pharmacist_details(self, pharmacist_id: str) -> Optional[str]:
        """
        STEP 2: Get detailed pharmacist information

        Args:
            pharmacist_id: Base64-encoded pharmacist ID from search

        Returns:
            HTML string containing pharmacist details, or None if failed
        """
        self.rate_limiter.wait()

        params = {
            "search_details": "get",
            "id": pharmacist_id
        }

        try:
            logger.debug(f"Fetching details for pharmacist ID: {pharmacist_id}")
            response = self.session.get(
                self.ppb_search_url,
                params=params,
                headers=self.details_headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                html = response.text
                logger.debug("Details retrieved successfully")
                return html

        except Exception as e:
            logger.error(f"Failed to get details for pharmacist ID {pharmacist_id}: {str(e)}")

        return None

    def parse_detailed_html(self, html: str) -> Dict:
        """
        Parse all fields from detailed pharmacist HTML

        Expected HTML structure:
        <b style="font-size:30px;">Gesare Achei Beryl</b>
        <a class="list-group-item text-boldest">Practice License Number: P2025D00463</a>
        <a class="list-group-item done">
            <span class="label label-success">Status: Active</span>
            <span class="text-boldest">Valid Till: 2025-12-31</span>
        </a>
        <img src="http://rhris.pharmacyboardkenya.org/photos/931801f625947bc9eb0c05e85dad5a0d684893e320250117095315am.png" width="200">

        Args:
            html: HTML content from details endpoint

        Returns:
            Dictionary with all extracted fields
        """
        info = {}

        # Extract full name (with proper capitalization)
        name_match = re.search(r'<b style="font-size:30px;">\s*([^<]+)\s*</b>', html, re.IGNORECASE)
        if name_match:
            info['full_name'] = name_match.group(1).strip()

        # Extract practice license number
        license_match = re.search(r'Practice License Number:\s*([^<]+)', html, re.IGNORECASE)
        if license_match:
            info['practice_license_number'] = license_match.group(1).strip()

        # Extract status
        status_match = re.search(r'Status:\s*([^<]+)</span>', html, re.IGNORECASE)
        if status_match:
            info['status'] = status_match.group(1).strip()

        # Extract valid_till date
        valid_till_match = re.search(r'Valid Till:\s*([\d-]+)', html, re.IGNORECASE)
        if valid_till_match:
            info['valid_till'] = valid_till_match.group(1).strip()

        # Extract photo URL
        photo_match = re.search(r'<img src="([^"]+)"\s+width="200"', html, re.IGNORECASE)
        if photo_match:
            info['photo_url'] = photo_match.group(1).strip()

        return info

    def verify_license_detailed(self, license_number: str, use_cache: bool = True) -> Dict:
        """
        Complete two-step verification with all detailed data

        STEP 1: Search for pharmacist via POST request
        STEP 2: Get detailed information using encoded ID
        STEP 3: Parse all fields including photo URL

        Args:
            license_number: Pharmacist license number (e.g., P2025D00463)
            use_cache: Whether to use cache

        Returns:
            Complete verification result with all fields
        """
        start_time = time.time()

        try:
            # Validate input
            if not license_number or not isinstance(license_number, str):
                raise PPBVerificationError("Invalid license number format")

            license_number = license_number.strip().upper()
            logger.info(f"Verifying Pharmacist license: {license_number}")

            # Validate format
            if not self.validate_license_format(license_number):
                raise PPBVerificationError(
                    "Invalid license number format. Expected format: PYYYYXNNNNN (e.g., P2025D00463)"
                )

            # Check cache
            cache_key = f"detailed:{license_number}"
            if use_cache and self.use_cache:
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    cached_result['from_cache'] = True
                    logger.info(f"Cache hit for: {license_number}")
                    return cached_result

            # STEP 1: Search for pharmacist
            search_html = self.search_pharmacist(license_number)

            if not search_html or "No records found" in search_html:
                raise PharmacistNotFoundError(
                    f"Pharmacist license '{license_number}' not found in registry"
                )

            # Extract pharmacist ID
            pharmacist_id = self.extract_pharmacist_id(search_html)

            # If the search succeeded but no ID was found, treat as not found
            if not pharmacist_id:
                raise PharmacistNotFoundError(
                    f"Pharmacist license '{license_number}' not found in registry"
                )

            # Extract basic data from search results
            search_data = self.extract_search_data(search_html)

            # STEP 2: Get detailed data
            detailed_html = self.get_pharmacist_details(pharmacist_id)

            if not detailed_html:
                raise PPBVerificationError("Failed to retrieve detailed pharmacist information")

            # STEP 3: Parse detailed data
            detailed_info = self.parse_detailed_html(detailed_html)

            # Merge search and detailed data (detailed takes precedence)
            final_data = {**search_data, **detailed_info}

            if not final_data.get('practice_license_number') and not final_data.get('license_number'):
                raise PPBVerificationError("Failed to extract complete pharmacist information")

            # Add metadata
            final_data['verified_at'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

            processing_time = round((time.time() - start_time) * 1000, 2)

            result = {
                "success": True,
                "license_number": license_number,
                "message": "Pharmacist verification successful",
                "processing_time_ms": processing_time,
                "from_cache": False,
                "data": final_data
            }

            # Cache result
            if use_cache and self.use_cache:
                self.cache.set(cache_key, result, self.cache_ttl)
                logger.debug(f"Cached result for: {license_number}")

            logger.info(f"Verification successful for {license_number} in {processing_time}ms")
            return result

        except PharmacistNotFoundError as e:
            processing_time = round((time.time() - start_time) * 1000, 2)
            logger.warning(f"Pharmacist not found: {license_number}")
            return {
                "success": False,
                "license_number": license_number,
                "message": str(e),
                "processing_time_ms": processing_time,
                "from_cache": False,
                "data": None
            }
        except PPBVerificationError as e:
            processing_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Verification error for {license_number}: {str(e)}")
            return {
                "success": False,
                "license_number": license_number,
                "message": str(e),
                "processing_time_ms": processing_time,
                "from_cache": False,
                "data": None
            }
        except Exception as e:
            processing_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Unexpected error for {license_number}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "license_number": license_number,
                "message": f"Unexpected error: {str(e)}",
                "processing_time_ms": processing_time,
                "from_cache": False,
                "data": None
            }

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.use_cache or self.cache is None:
            return {"cache_enabled": False}

        stats = self.cache.get_stats()
        stats['cache_enabled'] = True
        return stats

    def clear_cache(self) -> bool:
        """Clear all cache entries"""
        if self.use_cache and self.cache:
            self.cache.clear()
            logger.info("Cache cleared")
            return True
        return False
