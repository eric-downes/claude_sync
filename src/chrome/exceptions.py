"""
Chrome-specific exceptions for claude-sync.
"""


class ClaudeSyncError(Exception):
    """Base exception for all claude-sync errors."""
    pass


class ChromeError(ClaudeSyncError):
    """Base exception for Chrome-related errors."""
    pass


class ChromeConnectionError(ChromeError):
    """Raised when unable to connect to Chrome."""
    pass


class ChromeNotFoundError(ChromeError):
    """Raised when Chrome is not running or not found."""
    pass


class ChromePageNotFoundError(ChromeError):
    """Raised when the expected page is not found in Chrome."""
    pass


class ChromeWebSocketError(ChromeError):
    """Raised when WebSocket communication fails."""
    pass


class ChromeTimeoutError(ChromeError):
    """Raised when Chrome operation times out."""
    pass


class ExtractionError(ClaudeSyncError):
    """Base exception for data extraction errors."""
    pass


class ProjectExtractionError(ExtractionError):
    """Raised when project extraction fails."""
    pass


class KnowledgeExtractionError(ExtractionError):
    """Raised when knowledge file extraction fails."""
    pass
