"""Core modules for configuration, logging, and versioning"""

from .config import Config, get_config
from .logger import setup_logging, get_logger, set_correlation_id, get_correlation_id
from .version import __version__

__all__ = [
    "Config",
    "get_config",
    "setup_logging",
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    "__version__",
]
