"""
Standalone geocoding test.
Tests Nominatim primary + Google fallback + usage tracking.
Run from crime_extraction_service/ directory:
    python test_geocoding.py
"""
import sys
import os
import json

# Make app importable without running FastAPI
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("COSMOS_ENDPOINT", "https://placeholder.documents.azure.com:443/")
os.environ.setdefault("COSMOS_KEY", "placeholder")
os.environ.setdefault("CEREBRAS_API_KEY", "placeholder")

from dotenv import load_dotenv
load_dotenv()

from app.services.geocoder import (
    normalize_location,
    geocode,
    get_usage_stats,
    _nominatim_search,
    _google_search,
)

SEP = "-" * 60

def test_normalize():
    print(f"\n{SEP}")
    print("  TEST: normalize_location()")
    print(SEP)
    cases = [
        ("Delhi's Nandi Nagri",      "Delhi Nand Nagri"),
        ("India\u2019s capital",     "India capital"),
        ("Rohni Sector 7",           "Rohini Sector 7"),
        ("Dwarka Mor",               "Dwarka More"),
        ("Lajpatnagar",              "Lajpat Nagar"),
        ("Connaught Place, Delhi",   "Connaught Place, Delhi"),  # no change
    ]
    all_pass = True
    for inp, expected in cases:
        result = normalize_location(inp)
        status = "PASS" if result.lower() == expected.lower() else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}]  '{inp}'  →  '{result}'  (expected: '{expected}')")
    return all_pass


def test_nominatim():
    print(f"\n{SEP}")
    print("  TEST: Nominatim geocoding")
    print(SEP)
    cases = [
        "Connaught Place, Delhi, India",
        "Rohini Sector 7, Delhi, India",
        "Nand Nagri, Delhi, India",
        "Dwarka More, Delhi, India",
    ]
    results = {}
    for query in cases:
        coords = _nominatim_search(query)
        status = "PASS" if coords else "FAIL"
        print(f"  [{status}]  '{query}'  →  {coords}")
        results[query] = coords
    return results


def test_google_fallback():
    print(f"\n{SEP}")
    print("  TEST: Google Geocoding API fallback")
    print(SEP)
    # Use a query that Nominatim might not resolve well
    query = "Nand Nagri, Delhi, India"
    coords = _google_search(query)
    status = "PASS" if coords else "FAIL"
    print(f"  [{status}]  '{query}'  →  {coords}")
    return coords


def test_full_geocode_pipeline():
    print(f"\n{SEP}")
    print("  TEST: Full geocode() pipeline (Nominatim → Google fallback)")
    print(SEP)
    cases = [
        # (raw input from LLM, expect coords)
        ("Delhi's Nandi Nagri",         True),   # typo + possessive — should resolve via correction
        ("Rohini Sector 7, Delhi",      True),
        ("Saket, New Delhi",            True),
        ("Chandni Chowk",               True),
        ("xyznonexistentplace12345",    False),  # should fail gracefully
    ]
    all_pass = True
    for location, expect_result in cases:
        coords = geocode(location)
        got_result = coords is not None
        status = "PASS" if got_result == expect_result else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}]  '{location}'  →  {coords}")
    return all_pass


def test_usage_stats():
    print(f"\n{SEP}")
    print("  TEST: Usage stats")
    print(SEP)
    stats = get_usage_stats()
    print(f"  Month             : {stats['month']}")
    print(f"  Google calls used : {stats['google_calls_used']}")
    print(f"  Google remaining  : {stats['google_calls_remaining']}")
    print(f"  Budget            : {stats['budget']}")
    return stats


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  GEOCODING TEST SUITE")
    print("=" * 60)

    norm_ok   = test_normalize()
    nom_res   = test_nominatim()
    goog_res  = test_google_fallback()
    pipe_ok   = test_full_geocode_pipeline()
    stats     = test_usage_stats()

    print(f"\n{SEP}")
    print("  SUMMARY")
    print(SEP)
    print(f"  Normalize tests   : {'PASS' if norm_ok else 'FAIL'}")
    print(f"  Nominatim hits    : {sum(1 for v in nom_res.values() if v)}/{len(nom_res)}")
    print(f"  Google fallback   : {'PASS' if goog_res else 'FAIL (check API key)'}")
    print(f"  Pipeline tests    : {'PASS' if pipe_ok else 'PARTIAL (check logs)'}")
    print(f"  Google used today : {stats['google_calls_used']} / {stats['budget']}")
    print(SEP)
