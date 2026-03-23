"""
Standalone test: LLM extraction with new schema.
Tests Cerebras (llama3.1-8b → gpt-oss-120b) then Ollama fallback.
Geocodes location using Nominatim.
Run from crime_extraction_service/ directory:
    python test_extraction.py
"""
import json
import httpx
import requests as req
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
CEREBRAS_API_URL = os.getenv("CEREBRAS_API_URL", "https://api.cerebras.ai/v1/chat/completions")
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
SAMPLE_URL = "https://www.siasat.com/delhi-mohammed-umardeen-shot-dead-while-trying-to-rescue-son-3371864/"

SAMPLE_TEXT = """
A 35-year-old Muslim man, who tried to save his teenage son from getting beaten up by a group,
was allegedly shot dead in Delhi's Nandi Nagri on Tuesday, February 17.

Mohammed Umardeen was relishing a cup of tea with his wife, mother and three daughters, when a
call from his 15-year-old son, Tehjeem, changed everything. Tehjeem, who sounded tense, asked
his father to rescue him after he was surrounded by an angry mob. According to his mother, the
teenager was targeted for his religious identity.

A grievously injured Tehjeem called up his father. Umardeen rushed to the spot and was shot dead
by the attackers. The suspects — Sonu and his brother Sardar — fled the scene. Police have
registered a case of murder and are searching for the accused. A country-made pistol was
recovered from the scene.
"""

# ── Prompt ────────────────────────────────────────────────────────────────────

def build_prompt(article_text: str) -> str:
    today = date.today().isoformat()
    return f"""Today's date is {today}.

Extract structured crime information from the article below.
Return ONLY a valid JSON object — no explanation, no markdown, no extra text.

JSON schema:
{{
  "crime_type": "one of: Murder / Robbery / Kidnapping / Rape / Assault / Theft / Burglary / Fraud / Other / null",
  "location_exact": "the most specific location mentioned — street, locality, neighbourhood, colony, sector (e.g. 'Nand Nagri', 'Rohini Sector 7'). null if not found.",
  "location_broad": "the broader area — city, district, region (e.g. 'Delhi', 'North Delhi'). null if not found.",
  "crime_date": "ISO 8601 date YYYY-MM-DD if determinable, else null. Use today ({today}) as reference for relative expressions like 'this Tuesday', 'last Sunday'.",
  "suspect": "name or description of suspect(s), or null",
  "victim": "name or description of victim(s), or null",
  "weapon_used": "weapon mentioned, or null"
}}

Rules:
- Return ONLY the JSON object.
- Use null for any field not found in the article.
- Do NOT invent or infer information not present.
- location_exact and location_broad are INDEPENDENT — extract both wherever possible.
  Example: "A murder occurred in Delhi's Nand Nagri colony" → location_exact: "Nand Nagri", location_broad: "Delhi"
- For relative dates: 'this Tuesday' means the most recent or upcoming Tuesday relative to today.

Article:
{article_text[:3000]}"""


# ── Geocoding ─────────────────────────────────────────────────────────────────

def normalize_location(location_text: str) -> str:
    """Normalize location string for better geocoding — remove possessives, extra punctuation."""
    if not location_text:
        return location_text
    import re
    # Remove possessives: "Delhi's" → "Delhi", "India's" → "India"
    normalized = re.sub(r"'s\b", "", location_text)
    # Remove any remaining apostrophes
    normalized = normalized.replace("'", "").replace("'", "")
    # Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def geocode(location_exact: str, location_broad: str = None):
    """Fetch lat/lng — tries exact first, falls back to broad."""
    def _search(location_text):
        if not location_text:
            return None, None
        clean = normalize_location(location_text)
        for query in [clean + ", Delhi, India", clean + ", India", clean]:
            try:
                resp = req.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": query, "format": "json", "limit": 1},
                    headers={"User-Agent": "delhi-crime-extractor/1.0"},
                    timeout=10,
                )
                results = resp.json()
                if results:
                    return float(results[0]["lat"]), float(results[0]["lon"])
            except Exception as e:
                print(f"  Geocode error: {e}")
        return None, None

    lat, lng = _search(location_exact)
    if lat:
        return lat, lng
    return _search(location_broad)
    return None, None


# ── LLM calls ─────────────────────────────────────────────────────────────────

def parse_json(content: str):
    """Strip markdown fences and parse JSON."""
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


def call_cerebras(model: str, prompt: str):
    print(f"\n  Calling Cerebras ({model})...")
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            CEREBRAS_API_URL,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 500,
            },
            headers={
                "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                "Content-Type": "application/json",
            },
        )
    if resp.status_code == 429:
        print(f"  Rate limited (429)")
        return None, "rate_limited"
    if resp.status_code != 200:
        print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
        return None, "error"
    content = resp.json()["choices"][0]["message"]["content"]
    return parse_json(content), "ok"


def call_ollama(prompt: str):
    print(f"\n  Calling Ollama ({OLLAMA_MODEL})...")
    try:
        resp = req.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=60,
        )
        content = resp.json()["message"]["content"]
        return parse_json(content)
    except Exception as e:
        print(f"  Ollama error: {e}")
        return None


# ── Main test ─────────────────────────────────────────────────────────────────

def run_test(article_url: str, article_text: str, label: str = ""):
    print(f"\n{'='*60}")
    print(f"  TEST{': ' + label if label else ''}")
    print(f"{'='*60}")
    print(f"  URL   : {article_url[:80]}")
    print(f"  Text  : {len(article_text)} chars")

    prompt = build_prompt(article_text)
    extracted = None

    # 1. Try llama3.1-8b
    extracted, status = call_cerebras("llama3.1-8b", prompt)
    if extracted is None and status == "rate_limited":
        # 2. Try gpt-oss-120b
        extracted, status = call_cerebras("gpt-oss-120b", prompt)
    if extracted is None:
        # 3. Ollama fallback
        extracted = call_ollama(prompt)

    if not extracted:
        print("\n  FAILED — no output from any model")
        return

    print(f"\n  Raw LLM output:")
    print(json.dumps(extracted, indent=4))

    # Geocode using both fields
    loc_exact = extracted.get("location_exact")
    loc_broad = extracted.get("location_broad")
    lat, lng = geocode(loc_exact, loc_broad) or (None, None)

    # Final record
    record = {
        "url":              article_url,
        "crime_type":       extracted.get("crime_type"),
        "location_exact":   normalize_location(loc_exact) if loc_exact else None,
        "location_broad":   normalize_location(loc_broad) if loc_broad else None,
        "coordinates":      {"lat": lat, "lng": lng} if lat else None,
        "crime_date":       extracted.get("crime_date"),
        "suspect":          extracted.get("suspect"),
        "victim":           extracted.get("victim"),
        "weapon_used":      extracted.get("weapon_used"),
        "processed_at":     datetime.utcnow().isoformat(),
    }

    print(f"\n  Final record:")
    print(json.dumps(record, indent=4))
    return record


if __name__ == "__main__":
    run_test(SAMPLE_URL, SAMPLE_TEXT, label="Murder article — exact date + geocode")

    # Second test: relative date reference
    SAMPLE2_URL = "https://example.com/robbery-rohini"
    SAMPLE2_TEXT = """
    A robbery took place this Wednesday at a jewellery shop in Rohini Sector 7, Delhi.
    The suspect, a man in his 30s wearing a black jacket, threatened the shopkeeper with a knife
    and fled with gold ornaments worth Rs 2 lakh. The victim, Ramesh Gupta, was unharmed.
    Police have registered a case and are reviewing CCTV footage.
    """
    run_test(SAMPLE2_URL, SAMPLE2_TEXT, label="Robbery — relative date + geocode")
