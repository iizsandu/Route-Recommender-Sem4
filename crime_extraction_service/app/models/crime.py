"""
Crime data models — new flat schema with url as unique ID
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Coordinates(BaseModel):
    lat: float
    lng: float


class CrimeRecord(BaseModel):
    """Structured crime record extracted from an article"""
    url: str                                  # unique ID — source article URL
    crime_type: Optional[str] = None          # Murder / Robbery / Kidnapping / etc.
    location_exact: Optional[str] = None      # specific locality/colony/sector from article
    location_broad: Optional[str] = None      # city/district/region from article
    location: Optional[str] = None            # normalized string used for geocoding (exact or broad)
    coordinates: Optional[Coordinates] = None
    crime_date: Optional[str] = None          # ISO 8601 date YYYY-MM-DD
    suspect: Optional[str] = None
    victim: Optional[str] = None
    weapon_used: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessBatchRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=500)
    reprocess: bool = Field(default=False, description="If true, reprocess already-processed articles")


class ProcessBatchResponse(BaseModel):
    processed: int
    successful: int
    failed: int
    skipped: int = 0
    errors: list[str] = []
