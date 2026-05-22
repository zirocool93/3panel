class AppError(Exception):
    """Base class for expected application errors."""


class AuthenticationError(AppError):
    """Raised when credentials or tokens cannot be accepted."""


class PermissionDenied(AppError):
    """Raised when the authenticated actor cannot perform an action."""
