"""
API routes for PPB pharmtech license verification
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from pydantic import ValidationError

from ..models.schemas import VerifyRequest, VerifyResponse
from ..services.ppb_service import PPBService
from ..core.logger import get_logger, set_correlation_id, get_correlation_id
from ..core.version import __version__

logger = get_logger(__name__)

# Create blueprint
api_bp = Blueprint("api", __name__)

# Service instance (will be initialized in create_app)
_ppb_service = None


def init_service(app):
    """
    Initialize PPB service with app configuration

    Args:
        app: Flask application instance
    """
    global _ppb_service
    _ppb_service = PPBService(
        use_cache=app.config.get("CACHE_ENABLED", True),
        cache_backend=app.config.get("CACHE_BACKEND", "simple"),
        cache_ttl=app.config.get("CACHE_TTL", 3600),
        rate_limit_delay=app.config.get("RATE_LIMIT_DELAY", 1.5),
        request_timeout=app.config.get("REQUEST_TIMEOUT", 15),
        max_retries=app.config.get("MAX_RETRIES", 2),
    )
    logger.info("PPB PharmTech service initialized")


@api_bp.before_request
def before_request():
    """Set up request context (correlation ID, logging)"""
    # Generate and set correlation ID
    corr_id = request.headers.get("X-Correlation-ID") or set_correlation_id()

    logger.info(
        f"Request started",
        extra={"extra_data": {
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
        }}
    )


@api_bp.after_request
def after_request(response):
    """Add correlation ID to response headers"""
    corr_id = get_correlation_id()
    if corr_id:
        response.headers["X-Correlation-ID"] = corr_id

    logger.info(
        f"Request completed",
        extra={"extra_data": {"status_code": response.status_code}}
    )
    return response


@api_bp.route("/", methods=["GET"])
def index():
    """Root endpoint with API information"""
    return jsonify({
        "service": "PPB PharmTech License Verification Microservice",
        "version": __version__,
        "description": "Verify Kenya PPB pharmaceutical technician licenses with complete details",
        "endpoints": {
            "info": "GET /",
            "health": "GET /health",
            "ready": "GET /ready",
            "verify": "POST /verify",
            "cache_stats": "GET /cache/stats",
            "cache_clear": "DELETE /cache"
        }
    }), 200


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint with cache stats"""
    cache_stats = _ppb_service.get_cache_stats() if _ppb_service else {"cache_enabled": False}

    return jsonify({
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cache": cache_stats
    }), 200


@api_bp.route("/ready", methods=["GET"])
def readiness_check():
    """Readiness check endpoint for Kubernetes/production"""
    if _ppb_service is None:
        return jsonify({
            "status": "not_ready",
            "message": "Service not initialized"
        }), 503

    return jsonify({
        "status": "ready",
        "version": __version__,
    }), 200


@api_bp.route("/verify", methods=["POST"])
def verify_license():
    """
    Verify a pharmtech license with complete detailed information

    Request body:
    {
        "license_number": "PT2025D05614",
        "use_cache": true  // optional, defaults to true
    }

    Response:
    {
        "success": true,
        "license_number": "PT2025D05614",
        "message": "PharmTech verification successful",
        "processing_time_ms": 1850.25,
        "from_cache": false,
        "data": {
            "full_name": "Changwony Gloria",
            "practice_license_number": "PT2025D05614",
            "status": "Active",
            "valid_till": "2025-12-31",
            "photo_url": "http://rhris.pharmacyboardkenya.org/photos/d4383c55f6b74dc528d9.JPG",
            "verified_at": "2025-10-15T12:00:00Z"
        }
    }
    """
    # Validate content type
    if not request.is_json:
        return jsonify({
            "success": False,
            "message": "Content-Type must be application/json",
            "data": None
        }), 400

    try:
        # Validate and parse request
        payload = VerifyRequest(**request.get_json())

        logger.info(f"Verifying license: {payload.license_number}")

        # Perform verification
        result = _ppb_service.verify_license_detailed(
            payload.license_number,
            use_cache=payload.use_cache
        )

        # Return appropriate status code
        status_code = 200 if result.get("success") else 404

        return jsonify(result), status_code

    except ValidationError as e:
        errors = e.errors()
        error_msg = errors[0]['msg'] if errors else "Invalid request"
        logger.warning(f"Validation error: {error_msg}")
        return jsonify({
            "success": False,
            "message": f"Validation error: {error_msg}",
            "data": None
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error in verify endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "data": None
        }), 500


@api_bp.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Get cache statistics"""
    stats = _ppb_service.get_cache_stats() if _ppb_service else {"cache_enabled": False}
    return jsonify(stats), 200


@api_bp.route("/cache", methods=["DELETE"])
def clear_cache():
    """Clear all cache entries"""
    if not _ppb_service:
        return jsonify({
            "success": False,
            "message": "Service not initialized"
        }), 500

    success = _ppb_service.clear_cache()

    if success:
        logger.info("Cache cleared via API")
        return jsonify({
            "success": True,
            "message": "Cache cleared successfully"
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "Cache not enabled"
        }), 400
