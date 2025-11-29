"""
Core module for workplace-roleplay application.
Contains extensions, error handlers, and middleware.
"""

from core.error_handlers import register_error_handlers
from core.extensions import init_extensions
from core.middleware import register_middleware

__all__ = [
    "init_extensions",
    "register_error_handlers",
    "register_middleware",
]
