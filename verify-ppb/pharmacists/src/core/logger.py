"""
Structured logging configuration for the PPB Pharmacist verification service
Supports both JSON and text formats with correlation ID tracking
"""

import logging
import sys
import json
import uuid
from datetime import datetime
from typing import Optional
from contextvars import ContextVar
from flask import has_request_context, request

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            log_data["correlation_id"] = corr_id

        # Add request context if available
        if has_request_context():
            log_data["request"] = {
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development"""

    def format(self, record):
        corr_id = correlation_id.get()
        corr_str = f" [CID:{corr_id[:8]}]" if corr_id else ""

        base_format = f"%(asctime)s - %(name)s - %(levelname)s{corr_str} - %(message)s"
        formatter = logging.Formatter(base_format)
        return formatter.format(record)


def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """
    Setup application logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if log_format.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_correlation_id(corr_id: Optional[str] = None):
    """
    Set correlation ID for request tracking

    Args:
        corr_id: Correlation ID (generates UUID if None)
    """
    if corr_id is None:
        corr_id = str(uuid.uuid4())
    correlation_id.set(corr_id)
    return corr_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id.get()
