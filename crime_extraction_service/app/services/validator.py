"""
Crime data validation service
"""
from typing import Optional
from pydantic import ValidationError
from app.models.crime import Crime, Location
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CrimeValidator:
    """Validates and transforms extracted crime data"""
    
    async def validate_crime(self, data: dict, source_article_id: str) -> Optional[Crime]:
        """
        Validate extracted crime data against Pydantic schema
        
        Args:
            data: Dictionary with extracted crime information
            source_article_id: ID of the source article
            
        Returns:
            Crime object if validation succeeds, None otherwise
        """
        try:
            # Handle location separately
            location_data = data.get("location")
            location = None
            if location_data and isinstance(location_data, dict):
                try:
                    location = Location(**location_data)
                except ValidationError as e:
                    logger.warning(
                        "location_validation_failed",
                        source_article_id=source_article_id,
                        error=str(e)
                    )
            
            # Create Crime object
            crime = Crime(
                crime_type=data.get("crime_type"),
                description=data.get("description"),
                location=location,
                date_time=data.get("date_time"),
                victim_count=data.get("victim_count"),
                suspect_count=data.get("suspect_count"),
                weapon_used=data.get("weapon_used"),
                source_article_id=source_article_id
            )
            
            # Calculate confidence
            crime.extraction_confidence = crime.calculate_confidence()
            
            logger.info(
                "validation_success",
                source_article_id=source_article_id,
                crime_type=crime.crime_type,
                confidence=crime.extraction_confidence
            )
            
            return crime
            
        except ValidationError as e:
            logger.error(
                "validation_failed",
                source_article_id=source_article_id,
                error=str(e),
                data=data
            )
            return None
        except Exception as e:
            logger.error(
                "validation_error",
                source_article_id=source_article_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
