class FrontpunchException(Exception):
    """Base exception for all frontpunch errors."""
    pass

class ConnectionError(FrontpunchException):
    """Raised when a connection to the Front API fails."""
    pass
