"""Browser management for Claude Sync."""
from .config import BrowserConfig
from .connection import ChromeConnection
from .manager import ChromeManager

__all__ = ["BrowserConfig", "ChromeManager", "ChromeConnection"]