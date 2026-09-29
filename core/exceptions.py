"""Custom exceptions for IBVAP."""

class IBVAPError(Exception):
    """Base exception for IBVAP."""
    pass


class ModelNotFoundError(IBVAPError):
    """Raised when a required AI model file is missing."""
    def __init__(self, model_name: str, path: str):
        self.model_name = model_name
        self.path = path
        super().__init__(f"{model_name} model not found:\n{path}")


class CameraError(IBVAPError):
    """Camera connection or stream related error."""
    pass


class ConfigError(IBVAPError):
    """Configuration related error."""
    pass


class DatabaseError(IBVAPError):
    """Database operation error."""
    pass
