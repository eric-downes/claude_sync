"""Knowledge file model."""
import hashlib
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


FileType = Literal["text", "pdf"]


class KnowledgeFile(BaseModel):
    """Represents a knowledge file in a Claude project."""
    
    name: str = Field(..., min_length=1, description="File name")
    file_type: FileType = Field(..., description="File type")
    content: Optional[str] = Field(None, description="File content")
    lines: Optional[int] = Field(None, ge=0, description="Number of lines")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    created_at: Optional[datetime] = Field(None, description="Creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    
    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        """Ensure file type is valid."""
        if v not in ["text", "pdf"]:
            raise ValueError(f"Invalid file type: {v}")
        return v
    
    def calculate_content_hash(self) -> Optional[str]:
        """Calculate SHA-256 hash of content."""
        if self.content is None:
            return None
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )