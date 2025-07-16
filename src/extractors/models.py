"""
Data models for Claude projects and knowledge files.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Project(BaseModel):
    """Model representing a Claude project."""

    model_config = ConfigDict()

    id: str = Field(..., description="Unique project ID")
    name: str = Field(..., description="Project name")
    url: str = Field(..., description="Full URL to the project")
    created_at: Optional[datetime] = Field(None, description="Project creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    updated: Optional[str] = Field(None, description="Human-readable update time (e.g., 'Updated 2 days ago')")
    description: Optional[str] = Field(None, description="Project description")


class KnowledgeFile(BaseModel):
    """Model representing a knowledge file in a project."""

    model_config = ConfigDict()

    name: str = Field(..., description="File name")
    content: str = Field(..., description="File content")
    file_type: Optional[str] = Field(None, description="File type/extension")
    size: Optional[int] = Field(None, description="File size in bytes")
    hash: Optional[str] = Field(None, description="Content hash for change detection")
    created_at: Optional[datetime] = Field(None, description="File creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class ProjectWithFiles(BaseModel):
    """Model representing a project with its knowledge files."""

    project: Project
    files: List[KnowledgeFile] = Field(default_factory=list)

    @property
    def file_count(self) -> int:
        """Get the number of files in the project."""
        return len(self.files)
