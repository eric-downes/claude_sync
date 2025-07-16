"""Browser configuration."""
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field


class BrowserConfig(BaseModel):
    """Configuration for Chrome browser management."""
    
    headless: bool = Field(
        default=True,
        description="Run Chrome in headless mode"
    )
    user_data_dir: Path = Field(
        default_factory=lambda: Path.home() / ".claude-sync" / "chrome-profile",
        description="Chrome user data directory for persistent session"
    )
    memory_limit_mb: int = Field(
        default=100,
        description="Memory limit for Chrome process in MB"
    )
    remote_debugging_port: int = Field(
        default=9222,
        description="Port for Chrome DevTools Protocol"
    )
    viewport_width: int = Field(
        default=1280,
        description="Browser viewport width"
    )
    viewport_height: int = Field(
        default=720,
        description="Browser viewport height"
    )
    
    def get_chrome_args(self) -> List[str]:
        """Get Chrome launch arguments for memory optimization and stability."""
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            f"--remote-debugging-port={self.remote_debugging_port}",
            # Disable automation detection
            "--disable-blink-features=AutomationControlled",
            # Memory optimization
            "--memory-pressure-off",
            "--max_old_space_size=96",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            # Disable unnecessary features
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-default-apps",
            "--no-first-run",
            "--disable-background-networking",
            "--disable-sync",
        ]
        
        if self.headless:
            args.extend([
                "--headless=new",  # Use new headless mode
                "--disable-gpu",
                "--disable-software-rasterizer",
            ])
        
        return args
    
    def get_viewport(self) -> Dict[str, int]:
        """Get viewport configuration."""
        return {
            "width": self.viewport_width,
            "height": self.viewport_height,
        }