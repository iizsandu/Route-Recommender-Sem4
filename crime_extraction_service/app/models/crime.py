"""
Crime data models using Pydantic
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import uuid4


class Location(BaseModel):
    """Location information for crime"""
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None


class Crime(BaseModel):
    """Crime record schema"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    crime_type: Optional[str] = None
    description: Optional[str] = None
    location: Optional[Location] = None
    date_time: Optional[datetime] = None
    victim_count: Optional[int] = None
    suspect_count: Optional[int] = None
    weapon_used: Optional[str] = None
    source_article_id: str
    extraction_confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def calculate_confidence(self) -> float:
        """Calculate extraction confidence based on filled fields"""
        total_fields = 9  # crime_type, description, location (4 subfields), date_time, victim_count, suspect_count, weapon_used
        filled_fields = 0
        
        if self.crime_type:
            filled_fields += 1
        if self.description:
            filled_fields += 1
        if self.date_time:
            filled_fields += 1
        if self.victim_count is not None:
            filled_fields += 1
        if self.suspect_count is not None:
            filled_fields += 1
        if self.weapon_used:
            filled_fields += 1
        
        # Location subfields
        if self.location:
            if self.location.city:
                filled_fields += 1
            if self.location.state:
                filled_fields += 1
            if self.location.country:
                filled_fields += 1
            if self.location.address:
                filled_fields += 1
        
        return round(filled_fields / total_fields, 2)


class ProcessBatchRequest(BaseModel):
    """Request model for batch processing"""
    limit: int = Field(default=10, ge=1, le=100)


class ProcessBatchResponse(BaseModel):
    """Response model for batch processing"""
    processed: int
    successful: int
    failed: int
    errors: list[str] = []
