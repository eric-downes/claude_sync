"""Project model."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer


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
    
    @field_serializer('updated_at')
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return v.isoformat() if v else None
    
    model_config = ConfigDict()