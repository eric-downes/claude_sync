"""Sync state model."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


SyncStatus = Literal["success", "error", "in_progress"]


class SyncState(BaseModel):
    """Represents the state of a sync operation."""
    
    last_sync: datetime = Field(..., description="Last sync timestamp")
    project_count: int = Field(..., ge=0, description="Number of projects synced")
    status: SyncStatus = Field(..., description="Sync status")
    error: Optional[str] = Field(None, description="Error message if status is error")
    chrome_pid: Optional[int] = Field(None, description="Chrome process ID")
    
    @property
    def hours_since_sync(self) -> float:
        """Calculate hours since last sync."""
        delta = datetime.now() - self.last_sync
        return delta.total_seconds() / 3600
    
    @field_serializer('last_sync')
    def serialize_datetime(self, v: datetime) -> str:
        """Serialize datetime to ISO format."""
        return v.isoformat()
    
    model_config = ConfigDict()