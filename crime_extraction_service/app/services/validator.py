"""
Validates and assembles a CrimeRecord from raw LLM output + geocoding result.
"""
from typing import Optional
from app.models.crime import CrimeRecord, Coordinates
from app.utils.logger import get_logger

logger = get_logger(__name__)

VALID_CRIME_TYPES = {
    "murder", "robbery", "kidnapping", "rape", "assault",
    "theft", "burglary", "fraud", "other",
}


def build_crime_record(
    url: str,
    llm_data: dict,
    location_used: Optional[str],   # the normalized string that was actually geocoded
    coords: Optional[tuple],        # (lat, lng) or None
) -> Optional[CrimeRecord]:
    """
    Build and return a CrimeRecord from LLM output + geocoding.
    Returns None only if url is missing.
    """
    if not url:
        logger.error("build_crime_record_no_url")
        return None

    crime_type = llm_data.get("crime_type")
    if crime_type and crime_type.lower() not in VALID_CRIME_TYPES:
        crime_type = "Other"

    coordinates = None
    if coords:
        coordinates = Coordinates(lat=coords[0], lng=coords[1])

    record = CrimeRecord(
        url=url,
        crime_type=crime_type,
        location_exact=llm_data.get("location_exact"),
        location_broad=llm_data.get("location_broad"),
        location=location_used,
        coordinates=coordinates,
        crime_date=llm_data.get("crime_date"),
        suspect=llm_data.get("suspect"),
        victim=llm_data.get("victim"),
        weapon_used=llm_data.get("weapon_used"),
    )

    logger.info(
        "crime_record_built",
        url=url[:60],
        crime_type=record.crime_type,
        location_exact=record.location_exact,
        location_broad=record.location_broad,
        has_coords=coordinates is not None,
    )
    return record
