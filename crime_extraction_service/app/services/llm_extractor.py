"""
LLM-based crime extraction.
Chain: Cerebras llama3.1-8b → gpt-oss-120b → Ollama fallback.
"""
import json
import httpx
import requests as req
from datetime import date
from typing import Optional, Tuple
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_prompt(article_text: str, article_date: str = None) -> str:
    anchor = article_date if article_date else date.today().isoformat()
    anchor_note = f"article published on {anchor}" if article_date else f"today is {anchor} (article date unknown)"
    return f"""Reference date: {anchor} ({anchor_note}).

Extract structured crime information from the article below.
Return ONLY a valid JSON object — no explanation, no markdown, no extra text.

JSON schema:
{{
  "crime_type": "one of: Murder / Robbery / Kidnapping / Rape / Assault / Theft / Burglary / Fraud / Other / null",
  "location_exact": "the most specific location mentioned — street, locality, neighbourhood, colony, sector (e.g. 'Nand Nagri', 'Rohini Sector 7', 'Chandni Chowk'). null if not found.",
  "location_broad": "the broader area — city, district, region (e.g. 'Delhi', 'North Delhi', 'New Delhi'). null if not found.",
  "crime_date": "ISO 8601 date YYYY-MM-DD if determinable, else null. Use the reference date ({anchor}) to resolve relative expressions like 'this Tuesday', 'last Sunday', 'yesterday'.",
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
- For relative dates: resolve using the reference date above.

Article:
{article_text[:3000]}"""


def _parse_json(content: str) -> Optional[dict]:
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("json_parse_error", error=str(e), snippet=content[:200])
        return None


def _call_cerebras(model: str, prompt: str) -> Tuple[Optional[dict], str]:
    """Returns (parsed_dict, status) where status is 'ok' | 'rate_limited' | 'error'."""
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                settings.cerebras_api_url,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 500,
                },
                headers={
                    "Authorization": f"Bearer {settings.cerebras_api_key}",
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code == 429:
            logger.warning("cerebras_rate_limited", model=model)
            return None, "rate_limited"
        if resp.status_code != 200:
            logger.error("cerebras_http_error", model=model, status=resp.status_code)
            return None, "error"
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = _parse_json(content)
        return parsed, "ok" if parsed else "error"
    except Exception as e:
        logger.error("cerebras_exception", model=model, error=str(e))
        return None, "error"


def _call_ollama(prompt: str) -> Optional[dict]:
    try:
        resp = req.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=60,
        )
        content = resp.json()["message"]["content"]
        return _parse_json(content)
    except Exception as e:
        logger.error("ollama_error", error=str(e))
        return None


def extract_crime_info(article_text: str, article_date: str = None) -> Optional[dict]:
    """
    Extract crime fields from article text.
    article_date: ISO date string from DB (published_date / date field). Falls back to today if None.
    Returns dict with keys: crime_type, location_exact, location_broad, crime_date, suspect, victim, weapon_used
    or None on total failure.
    """
    if not article_text or not article_text.strip():
        return None

    prompt = _build_prompt(article_text, article_date)

    # 1. llama3.1-8b
    result, status = _call_cerebras("llama3.1-8b", prompt)
    if result:
        logger.info("extracted_via", model="llama3.1-8b")
        return result

    # 2. gpt-oss-120b (if rate limited or error on llama)
    result, status = _call_cerebras("gpt-oss-120b", prompt)
    if result:
        logger.info("extracted_via", model="gpt-oss-120b")
        return result

    # 3. Ollama fallback
    result = _call_ollama(prompt)
    if result:
        logger.info("extracted_via", model="ollama")
        return result

    logger.warning("extraction_failed_all_models")
    return None
