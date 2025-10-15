"""
Centralized error handlers for the Flask application
"""

from flask import jsonify
from pydantic import ValidationError
from ..core.logger import get_logger

logger = get_logger(__name__)


def register_error_handlers(app):
    """
    Register error handlers with the Flask app

    Args:
        app: Flask application instance
    """

    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors"""
        logger.warning(f"Bad request: {error}")
        return jsonify({
            "success": False,
            "message": "Bad request",
            "data": None
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors"""
        return jsonify({
            "success": False,
            "message": "Endpoint not found",
            "data": None
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle method not allowed errors"""
        return jsonify({
            "success": False,
            "message": "Method not allowed",
            "data": None
        }), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        """Handle payload too large errors"""
        logger.warning("Payload too large")
        return jsonify({
            "success": False,
            "message": "Request payload too large",
            "data": None
        }), 413

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "data": None
        }), 500

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle Pydantic validation errors"""
        logger.warning(f"Validation error: {error}")
        errors = error.errors()
        return jsonify({
            "success": False,
            "message": f"Validation error: {errors[0]['msg']}",
            "data": None
        }), 400
