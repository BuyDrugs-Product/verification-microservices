"""
Simple entry point for running the service
For development use only - use gunicorn for production
"""

from src.app import app

if __name__ == "__main__":
    app.run(
        debug=app.config.get("DEBUG", False),
        host=app.config.get("HOST", "0.0.0.0"),
        port=app.config.get("PORT", 5002),
    )
