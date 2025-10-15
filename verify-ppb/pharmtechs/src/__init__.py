"""PPB PharmTech License Verification Microservice"""

from .app import create_app
from .core.version import __version__

__all__ = ["create_app", "__version__"]
