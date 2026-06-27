"""
Custom exceptions for the frontpunch library.
"""

class FrontpunchException(Exception):
    """Base exception for all frontpunch-specific errors."""
    pass

class ConnectionError(FrontpunchException):
    """Raised when a connection to a service (e.g., Redis) fails."""
    pass
