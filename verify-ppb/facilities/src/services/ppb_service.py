"""
PPB License Verification Service - Production Implementation
Two-step workflow with proper session management, headers, and resilient error handling

CRITICAL: Maintains the exact same verification logic as the original implementation
to ensure 100% compatibility with existing functionality.
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


class FacilityNotFoundError(PPBVerificationError):
    """Raised when facility is not found in registry"""
    pass


class PPBService:
    """PPB license verification service with complete implementation"""

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

        # Search headers - CRITICAL: Do not modify without testing
        self.search_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.ppb_base_url}/LicenseStatus?register=facilities"
        }

        # Details headers - CRITICAL: Required for accessing modal content
        self.details_headers = {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": f"{self.ppb_base_url}/LicenseStatus?register=facilities",
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
                    key_prefix="ppb:v1:"
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

    def get_current_timestamp(self) -> str:
        """Get current timestamp in milliseconds"""
        return str(int(time.time() * 1000))

    def build_search_params(self, search_term: str) -> Dict:
        """Build parameters for the search request"""
        return {
            "fetch": "facilities",
            "ftype": "",
            "draw": "1",
            "columns[0][data]": "0", "columns[0][name]": "", "columns[0][searchable]": "true",
            "columns[0][orderable]": "true", "columns[0][search][value]": "", "columns[0][search][regex]": "false",
            "columns[1][data]": "1", "columns[1][name]": "", "columns[1][searchable]": "true",
            "columns[1][orderable]": "true", "columns[1][search][value]": "", "columns[1][search][regex]": "false",
            "columns[2][data]": "2", "columns[2][name]": "", "columns[2][searchable]": "true",
            "columns[2][orderable]": "true", "columns[2][search][value]": "", "columns[2][search][regex]": "false",
            "columns[3][data]": "3", "columns[3][name]": "", "columns[3][searchable]": "true",
            "columns[3][orderable]": "true", "columns[3][search][value]": "", "columns[3][search][regex]": "false",
            "columns[4][data]": "4", "columns[4][name]": "", "columns[4][searchable]": "true",
            "columns[4][orderable]": "true", "columns[4][search][value]": "", "columns[4][search][regex]": "false",
            "order[0][column]": "0", "order[0][dir]": "asc",
            "start": "0", "length": "10",
            "search[value]": search_term, "search[regex]": "false",
            "_": self.get_current_timestamp()
        }

    def search_facilities(self, ppb_number: str) -> Optional[Dict]:
        """
        STEP 1: Search for facilities using the PPB portal API

        Args:
            ppb_number: PPB registration number

        Returns:
            Search results dictionary with facility data

        Raises:
            PPBVerificationError: If request fails
        """
        self.rate_limiter.wait()

        params = self.build_search_params(ppb_number)

        try:
            logger.debug(f"Searching PPB portal for: {ppb_number}")
            response = self.session.get(
                self.ppb_search_url,
                params=params,
                headers=self.search_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.debug(f"Search successful for: {ppb_number}")
            return response.json()

        except Exception as e:
            logger.error(f"Search failed for {ppb_number}: {str(e)}")
            raise PPBVerificationError(f"Failed to connect to PPB portal: {str(e)}")

    def extract_facility_id(self, search_data: Dict) -> Optional[str]:
        """
        Extract encoded facility ID from search results

        Args:
            search_data: Search API response

        Returns:
            Base64-encoded facility ID (e.g., "Mjc2ODk=")
        """
        if not search_data or not search_data.get('data') or len(search_data['data']) == 0:
            return None

        facility_data = search_data['data'][0]

        # Extract encoded ID from column 4 (View Details link)
        if len(facility_data) > 4 and facility_data[4]:
            view_details_html = str(facility_data[4])
            id_match = re.search(r"rel='([^']+)'", view_details_html)
            if id_match:
                facility_id = id_match.group(1)
                logger.debug(f"Extracted facility ID: {facility_id}")
                return facility_id

        return None

    def validate_details_response(self, html: str) -> bool:
        """
        Validate that the details response contains expected facility data

        Args:
            html: HTML response from details endpoint

        Returns:
            True if response is valid, False otherwise
        """
        required_patterns = [
            r'Facility Registration Number:',
            r'License Number:',
            r'Licence Status:'
        ]
        return all(re.search(pattern, html, re.IGNORECASE) for pattern in required_patterns)

    def get_facility_details(self, facility_id: str) -> Optional[str]:
        """
        STEP 2: Get detailed facility information with robust error handling

        Uses multiple fallback strategies to handle potential issues

        Args:
            facility_id: Base64-encoded facility ID from search

        Returns:
            HTML string containing facility details, or None if failed
        """
        self.rate_limiter.wait()

        params = {
            "search_details": "facility",
            "id": facility_id
        }

        # Try multiple strategies
        strategies = [
            # Primary strategy - exact headers from working implementation
            lambda: self.session.get(
                self.ppb_search_url,
                params=params,
                headers=self.details_headers,
                timeout=self.timeout
            ),
            # Fallback 1 - different accept header
            lambda: self.session.get(
                self.ppb_search_url,
                params=params,
                headers={**self.details_headers, "Accept": "*/*"},
                timeout=self.timeout
            ),
            # Fallback 2 - minimal headers
            lambda: self.session.get(
                self.ppb_search_url,
                params=params,
                headers={
                    "User-Agent": self.details_headers["User-Agent"],
                    "Referer": self.details_headers["Referer"],
                    "X-Requested-With": "XMLHttpRequest"
                },
                timeout=self.timeout
            ),
        ]

        for idx, strategy in enumerate(strategies):
            try:
                logger.debug(f"Fetching details (strategy {idx + 1})")
                response = strategy()
                if response.status_code == 200:
                    html = response.text
                    if self.validate_details_response(html):
                        logger.debug(f"Details retrieved successfully (strategy {idx + 1})")
                        return html
            except Exception as e:
                logger.warning(f"Strategy {idx + 1} failed: {str(e)}")
                continue

        logger.error(f"All strategies failed for facility ID: {facility_id}")
        return None

    def extract_superintendent_from_comments(self, html: str) -> Optional[Dict]:
        """
        Extract superintendent data from HTML comments
        
        CRITICAL: Uses three-tier fallback strategy to ensure maximum reliability
        This is the most complex extraction component - DO NOT modify without testing

        The PPB portal stores superintendent data in HTML comments like:

        Hospital/Retail format:
        <!--<a class="list-group-item text-boldest" >
            Superintendent : KELVIN KIPCHIRCHIR                     <br />
            Cadre: PHARMTECH                    <br />
            Enrollment Number: 10858                    </a>-->

        Manufacturer/Wholesale format:
        <!--<a class="list-group-item text-boldest" >
            Superintendent : SROYA ZAHID<br />
            Cadre: PHARMACIST<br />
            Registration Number: 2462</a>-->

        Args:
            html: HTML content containing superintendent data

        Returns:
            Dictionary with superintendent info or None
        """
        try:
            # PRIMARY PATTERN - captures the ENTIRE commented superintendent section
            # Handles both "Enrollment Number" (Hospital/Retail) and "Registration Number" (Manufacturer/Wholesale)
            comment_pattern = r'<!--\s*<a class="list-group-item text-boldest"\s*>\s*Superintendent\s*:\s*([^<]+?)\s*<br\s*\/?>\s*Cadre:\s*([^<]+?)\s*<br\s*\/?>\s*(?:Enrollment Number|Registration Number):\s*([^<]+?)\s*<\/a>\s*-->'

            match = re.search(comment_pattern, html, re.DOTALL | re.IGNORECASE)

            if match:
                name = match.group(1).strip()
                cadre = match.group(2).strip()
                enrollment = match.group(3).strip()

                logger.debug(f"Superintendent extracted (primary pattern): {name}")
                return {
                    "name": name,
                    "cadre": cadre,
                    "enrollment_number": enrollment
                }

            # FALLBACK PATTERN 1 - More flexible approach
            # Matches superintendent data anywhere in the HTML (not just in comments)
            alt_pattern = r'Superintendent\s*:\s*([^\n<]+)[\s\S]{0,200}?Cadre:\s*([^\n<]+)[\s\S]{0,200}?(?:Enrollment Number|Registration Number):\s*([^\n<]+)'
            alt_match = re.search(alt_pattern, html, re.IGNORECASE)

            if alt_match:
                logger.debug("Superintendent extracted (fallback pattern 1)")
                return {
                    "name": alt_match.group(1).strip(),
                    "cadre": alt_match.group(2).strip(),
                    "enrollment_number": alt_match.group(3).strip()
                }

            # FALLBACK PATTERN 2 - Find commented section first, then extract
            comment_section = r'<!--.*?Superintendent.*?-->'
            comment_match = re.search(comment_section, html, re.DOTALL | re.IGNORECASE)

            if comment_match:
                comment_text = comment_match.group(0)

                # Now extract from the comment text
                name_match = re.search(r'Superintendent\s*:\s*([^\n<]+)', comment_text, re.IGNORECASE)
                cadre_match = re.search(r'Cadre:\s*([^\n<]+)', comment_text, re.IGNORECASE)
                enrollment_match = re.search(r'(?:Enrollment Number|Registration Number):\s*([^\n<]+)', comment_text, re.IGNORECASE)

                if name_match and cadre_match and enrollment_match:
                    logger.debug("Superintendent extracted (fallback pattern 2)")
                    return {
                        "name": name_match.group(1).strip(),
                        "cadre": cadre_match.group(1).strip(),
                        "enrollment_number": enrollment_match.group(1).strip()
                    }

            logger.warning("Superintendent data not found in HTML")
            return None

        except Exception as e:
            logger.error(f"Error extracting superintendent: {str(e)}")
            return None

    def parse_detailed_html(self, html: str) -> Dict:
        """
        Parse all fields from detailed facility HTML

        Args:
            html: HTML content from details endpoint

        Returns:
            Dictionary with all extracted fields
        """
        info = {}

        # Extraction patterns
        patterns = {
            'facility_name': r'<b style="font-size:20px;">\s*([^<]+)\s*</b>',
            'registration_number': r'Facility Registration Number:\s*([^<]+)',
            'license_number': r'License Number:\s*([^<]+)',
            'ownership': r'Ownership\s*:\s*([^<]+)',
            'license_type': r'License Type:\s*([^<]+)',
            'establishment_year': r'Establishment Year\s*:\s*([^<]+)',
            'street': r'Street:\s*([^<]+)',
            'county': r'County\s*:\s*([^<]+)',
            'license_status': r'Licence Status:\s*([A-Z]+)',
            'valid_till': r'Valid Till:\s*([\d-]+)'
        }

        # Extract each field
        for field, pattern in patterns.items():
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean whitespace
                value = re.sub(r'\s+', ' ', value)
                info[field] = value
                logger.debug(f"Extracted {field}: {value}")

        # Extract superintendent from comments
        superintendent = self.extract_superintendent_from_comments(html)
        if superintendent:
            info['superintendent'] = superintendent

        return info

    def verify_license_detailed(self, ppb_number: str, use_cache: bool = True) -> Dict:
        """
        Complete two-step verification with all detailed data

        STEP 1: Search for facility and extract ID
        STEP 2: Get detailed information using proper session and headers
        STEP 3: Parse all fields including superintendent from comments

        Args:
            ppb_number: PPB registration number
            use_cache: Whether to use cache

        Returns:
            Complete verification result with all fields
        """
        start_time = time.time()

        try:
            # Validate input
            if not ppb_number or not isinstance(ppb_number, str):
                raise PPBVerificationError("Invalid PPB number format")

            ppb_number = ppb_number.strip()
            logger.info(f"Verifying PPB number: {ppb_number}")

            # Check cache
            cache_key = f"detailed:{ppb_number}"
            if use_cache and self.use_cache:
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    cached_result['from_cache'] = True
                    logger.info(f"Cache hit for: {ppb_number}")
                    return cached_result

            # STEP 1: Search for facility
            search_data = self.search_facilities(ppb_number)

            if not search_data or not search_data.get('data') or len(search_data['data']) == 0:
                raise FacilityNotFoundError(f"Facility with PPB number '{ppb_number}' not found in registry")

            # Extract facility ID
            facility_id = self.extract_facility_id(search_data)

            if not facility_id:
                raise PPBVerificationError("Failed to extract facility ID from search results")

            # STEP 2: Get detailed data
            detailed_html = self.get_facility_details(facility_id)

            if not detailed_html:
                raise PPBVerificationError("Failed to retrieve detailed facility information")

            # STEP 3: Parse all data
            detailed_info = self.parse_detailed_html(detailed_html)

            if not detailed_info.get('license_number'):
                raise PPBVerificationError("Failed to extract complete facility information")

            # Add metadata
            detailed_info['verified_at'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

            processing_time = round((time.time() - start_time) * 1000, 2)

            result = {
                "success": True,
                "ppb_number": ppb_number,
                "message": "Complete license verification successful",
                "processing_time_ms": processing_time,
                "from_cache": False,
                "data": detailed_info
            }

            # Cache result
            if use_cache and self.use_cache:
                self.cache.set(cache_key, result, self.cache_ttl)
                logger.debug(f"Cached result for: {ppb_number}")

            logger.info(f"Verification successful for {ppb_number} in {processing_time}ms")
            return result

        except FacilityNotFoundError as e:
            processing_time = round((time.time() - start_time) * 1000, 2)
            logger.warning(f"Facility not found: {ppb_number}")
            return {
                "success": False,
                "ppb_number": ppb_number,
                "message": str(e),
                "processing_time_ms": processing_time,
                "from_cache": False,
                "data": None
            }
        except PPBVerificationError as e:
            processing_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Verification error for {ppb_number}: {str(e)}")
            return {
                "success": False,
                "ppb_number": ppb_number,
                "message": str(e),
                "processing_time_ms": processing_time,
                "from_cache": False,
                "data": None
            }
        except Exception as e:
            processing_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Unexpected error for {ppb_number}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "ppb_number": ppb_number,
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

