"""
Geocoding service.
  Primary  : Nominatim (free, no quota)
  Fallback : Google Maps Geocoding API (capped at GEOCODING_MONTHLY_BUDGET req/month)

Monthly usage is persisted in geocoding_usage.json next to this file so it
survives service restarts.
"""
import re
import json
import os
import requests
from datetime import datetime
from typing import Optional, Tuple
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Delhi locality correction dict ────────────────────────────────────────────
DELHI_LOCALITY_CORRECTIONS = {
    "nandi nagri":  "nand nagri",
    "nandhi nagri": "nand nagri",
    "nandinagri":   "nand nagri",
    "nandnagri":    "nand nagri",
    "rohni":        "rohini",
    "rohni sector": "rohini sector",
    "dwarka mor":   "dwarka more",
    "lajpatnagar":  "lajpat nagar",
    "vasantvihar":  "vasant vihar",
    "shahadra":     "shahdara",
    "mustfabad":    "mustafabad",
    "bhajan pura":  "bhajanpura",
    "trilok puri":  "trilokpuri",
    "gita colony":  "geeta colony",
}

_HEADERS = {"User-Agent": "delhi-crime-extractor/1.0 (research project)"}

# Path to usage tracking file (sits alongside this module)
_USAGE_FILE = os.path.join(os.path.dirname(__file__), "geocoding_usage.json")


# ── Usage tracker ─────────────────────────────────────────────────────────────

def _load_usage() -> dict:
    """Load monthly usage from disk. Resets automatically on new month."""
    try:
        if os.path.exists(_USAGE_FILE):
            with open(_USAGE_FILE) as f:
                data = json.load(f)
            # Reset if it's a new month
            if data.get("month") != datetime.utcnow().strftime("%Y-%m"):
                return {"month": datetime.utcnow().strftime("%Y-%m"), "count": 0}
            return data
    except Exception:
        pass
    return {"month": datetime.utcnow().strftime("%Y-%m"), "count": 0}


def _save_usage(data: dict):
    try:
        with open(_USAGE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning("usage_save_failed", error=str(e))


def _increment_google_usage() -> int:
    """Increment and persist Google API call count. Returns new count."""
    data = _load_usage()
    data["count"] += 1
    _save_usage(data)
    return data["count"]


def _google_budget_remaining() -> int:
    from app.config import settings
    data = _load_usage()
    return max(0, settings.geocoding_monthly_budget - data["count"])


# ── Normalize ─────────────────────────────────────────────────────────────────

def normalize_location(location_text: str) -> str:
    """Strip possessives, apply Delhi locality corrections, collapse whitespace."""
    if not location_text:
        return location_text

    normalized = re.sub(r"'s\b", "", location_text, flags=re.IGNORECASE)
    normalized = normalized.replace("\u2019s", "").replace("'", "")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    lower = normalized.lower()
    for wrong, correct in DELHI_LOCALITY_CORRECTIONS.items():
        if wrong in lower:
            normalized = re.sub(re.escape(wrong), correct, normalized, flags=re.IGNORECASE)
            break

    return normalized


# ── Nominatim ─────────────────────────────────────────────────────────────────

def _nominatim_search(query: str) -> Optional[Tuple[float, float]]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers=_HEADERS,
            timeout=10,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        logger.warning("nominatim_error", query=query, error=str(e))
    return None


# ── Google Geocoding API ───────────────────────────────────────────────────────

def _google_search(query: str) -> Optional[Tuple[float, float]]:
    """
    Call Google Maps Geocoding API.
    Only called when Nominatim fails AND monthly budget has not been exhausted.
    """
    from app.config import settings

    api_key = settings.google_geocoding_api_key
    if not api_key or api_key == "your_google_geocoding_api_key_here":
        logger.debug("google_geocoding_skipped", reason="no_api_key")
        return None

    remaining = _google_budget_remaining()
    if remaining <= 0:
        logger.warning("google_geocoding_budget_exhausted", month=datetime.utcnow().strftime("%Y-%m"))
        return None

    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": query, "key": api_key},
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            count = _increment_google_usage()
            logger.info("geocoded_google", query=query, remaining=remaining - 1, total_used=count)
            return float(loc["lat"]), float(loc["lng"])
        else:
            logger.warning("google_geocoding_no_result", query=query, status=data.get("status"))
    except Exception as e:
        logger.warning("google_geocoding_error", query=query, error=str(e))
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def _geocode_single(clean: str) -> Optional[Tuple[float, float]]:
    """Try Nominatim cascade then Google for one normalized location string."""
    for query in [f"{clean}, Delhi, India", f"{clean}, India", clean]:
        result = _nominatim_search(query)
        if result:
            logger.info("geocoded_nominatim", query=query, result=result)
            return result
    result = _google_search(clean)
    if result:
        return result
    return None


def geocode(location_exact: Optional[str], location_broad: Optional[str] = None) -> Optional[Tuple[float, float]]:
    """
    Geocode using exact + broad location from LLM.

    Strategy:
      1. Try location_exact (most specific — locality, colony, sector)
         - Nominatim: "<exact>, Delhi, India" / "<exact>, India" / "<exact>"
         - Google fallback: "<exact>"
      2. If exact fails, try location_broad (city/district)
         - Same cascade

    Returns (lat, lng) or None.
    """
    # Try exact first
    if location_exact:
        clean_exact = normalize_location(location_exact)
        logger.info("geocoding_exact", original=location_exact, normalized=clean_exact)
        result = _geocode_single(clean_exact)
        if result:
            return result
        logger.warning("geocode_exact_failed", location=clean_exact)

    # Fall back to broad
    if location_broad:
        clean_broad = normalize_location(location_broad)
        logger.info("geocoding_broad_fallback", original=location_broad, normalized=clean_broad)
        result = _geocode_single(clean_broad)
        if result:
            return result
        logger.warning("geocode_broad_failed", location=clean_broad)

    logger.warning("geocode_failed_all", exact=location_exact, broad=location_broad)
    return None


def get_usage_stats() -> dict:
    """Return current Google API usage stats — useful for health endpoint."""
    from app.config import settings
    data = _load_usage()
    return {
        "month": data["month"],
        "google_calls_used": data["count"],
        "google_calls_remaining": max(0, settings.geocoding_monthly_budget - data["count"]),
        "budget": settings.geocoding_monthly_budget,
    }
