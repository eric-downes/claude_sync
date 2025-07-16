"""Project model."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Project(BaseModel):
    """Represents a Claude.ai project."""
    
    id: str = Field(..., min_length=1, description="Unique project ID")
    name: str = Field(..., min_length=1, description="Project name")
    url: str = Field(..., min_length=1, description="Project URL")
    description: Optional[str] = Field(None, description="Project description")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is valid Claude project URL."""
        if not v.startswith(("https://claude.ai/project/", "http://localhost")):
            # Allow localhost for testing
            raise ValueError("URL must be a valid Claude.ai project URL")
        return v
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )