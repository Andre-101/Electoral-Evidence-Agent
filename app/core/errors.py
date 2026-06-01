class AppError(Exception):
    """Base application error."""


class ConfigError(AppError):
    """Configuration loading or validation error."""


class DatabaseError(AppError):
    """Database connectivity or query error."""
