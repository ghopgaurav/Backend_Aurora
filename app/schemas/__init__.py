"""
Pydantic schemas for request and response validation.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search query request schema."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    skip: int = Field(0, ge=0, description="Number of results to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")


class MessageItem(BaseModel):
    """Individual search result schema returned from external API."""
    
    id: str
    user_id: str
    user_name: str
    timestamp: datetime
    message: str


class SearchResponse(BaseModel):
    """Search response schema."""
    
    query: str = Field(..., description="Original search query")
    total: int = Field(..., ge=0, description="Total number of matching results")
    skip: int = Field(..., ge=0, description="Number of results skipped")
    limit: int = Field(..., ge=1, description="Requested number of results")
    results: List[MessageItem] = Field(..., description="List of matching results")


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
