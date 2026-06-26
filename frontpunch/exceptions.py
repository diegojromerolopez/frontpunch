class FrontpunchException(Exception):
    """Base exception for all frontpunch errors."""
    pass

class ConnectionError(FrontpunchException):
    """Raised when a connection to Redis cannot be established."""
    pass
