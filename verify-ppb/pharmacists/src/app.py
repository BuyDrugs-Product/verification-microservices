"""
Main Flask application factory
Creates and configures the Flask application
"""

import os
from flask import Flask
from .core.config import get_config
from .core.logger import setup_logging, get_logger
from .core.version import __version__
from .api.routes import api_bp, init_service
from .api.errors import register_error_handlers

logger = get_logger(__name__)


def create_app(config_name=None):
    """
    Application factory pattern for creating Flask app

    Args:
        config_name: Configuration name (development/production/testing)

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Setup logging
    setup_logging(
        log_level=app.config.get("LOG_LEVEL", "INFO"),
        log_format=app.config.get("LOG_FORMAT", "json")
    )

    logger.info(f"Starting PPB Pharmacist Verification Service v{__version__} ({config_name} mode)")

    # Register blueprints
    app.register_blueprint(api_bp)

    # Register error handlers
    register_error_handlers(app)

    # Initialize services
    with app.app_context():
        init_service(app)

    logger.info("Application initialized successfully")

    return app


# Create app instance for direct execution
app = create_app()

if __name__ == "__main__":
    app.run(
        debug=app.config.get("DEBUG", False),
        host=app.config.get("HOST", "0.0.0.0"),
        port=app.config.get("PORT", 5002),
    )
