"""
HTTP client adapter with retry logic and rate limiting
Provides resilient HTTP communication with the PPB portal
"""

import random
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional
from ..core.logger import get_logger

logger = get_logger(__name__)


def build_session(max_retries: int = 2, backoff: float = 0.3) -> requests.Session:
    """
    Build a requests session with retry logic

    Args:
        max_retries: Maximum number of retries
        backoff: Backoff factor for exponential backoff

    Returns:
        Configured requests session
    """
    session = requests.Session()

    # Configure retry strategy for GET requests only (idempotent)
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    logger.debug(f"HTTP session created with max_retries={max_retries}, backoff={backoff}")

    return session


class RateLimiter:
    """
    Rate limiter to prevent IP blocking

    CRITICAL: The PPB portal blocks IPs that make requests too quickly.
    Default delay of 1.5s has been tested and prevents blocking.
    """

    def __init__(self, delay: float = 1.5):
        """
        Initialize rate limiter

        Args:
            delay: Minimum seconds between requests
        """
        self.delay = delay
        self.last_request = 0.0
        logger.debug(f"RateLimiter initialized with {delay}s delay")

    def wait(self):
        """Wait if necessary to maintain rate limit"""
        now = time.time()
        elapsed = now - self.last_request

        if elapsed < self.delay:
            wait_time = (self.delay - elapsed) + random.uniform(0, 0.05)  # Add small jitter
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)

        self.last_request = time.time()
