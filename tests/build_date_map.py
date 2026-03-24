"""
Build a JSON map of { url: date_string } for all URLs in files/urls.csv.

Run modes:
    python build_date_map.py              # test on first 100 URLs
    python build_date_map.py --all        # process all 3250, write dates.json
    python build_date_map.py --retry-nulls  # re-run only nulls in existing dates.json

Output:
    tests/dates.json   { "<cleaned_url>": "YYYY-MM-DDTHH:MM:SS" | null }

Strategies (in order, no per-source code):
    1. newspaper3k
    2. itemprop="datePublished"   schema.org
    3. itemprop="dateModified"    schema.org fallback
    4. <meta> tags                og/DC properties
    5. JSON-LD <script>           structured data
    6. Classed elements           byline/timestamp/date class names
    7. Full-page keyword scan     near published/updated/posted — first 5000 chars
    8. Full-page early scan       any date pattern in first 5000 chars
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import csv, json, re, time
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser
from datetime import datetime, timezone
from article_text_extractor import get_extractor

# ── Config ────────────────────────────────────────────────────────────────────
CSV_PATH    = os.path.join(os.path.dirname(__file__), '..', 'files', 'urls.csv')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'dates.json')
HEADERS     = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
DELAY_SEC   = 0.5
TIMEOUT_SEC = 15

# Every date format we recognise
DATE_PATTERNS = [
    # ISO 8601 with time:  2026-01-27T20:39:00+05:30
    re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)?'),
    # ISO date only:  2026-01-27
    re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
    # Month-name:  Jan 27, 2026  /  January 27, 2026, 20:39 IST
    re.compile(
        r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{1,2},?\s+\d{4}(?:[,\s]+\d{1,2}:\d{2}(?:\s*[AP]M)?(?:\s*IST)?)?',
        re.IGNORECASE
    ),
    # DD Month YYYY:  27 January 2026
    re.compile(
        r'\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{4}\b',
        re.IGNORECASE
    ),
    # Slash/dot:  27/01/2026  or  01.27.2026
    re.compile(r'\b\d{1,2}[/\.]\d{1,2}[/\.]\d{4}\b'),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_url(url: str) -> str:
    for p in ['&ved=', '&usg=', '&sa=', '&source=', '&cd=', '&cad=',
              '&utm_source=', '&utm_medium=', '&utm_campaign=', '&fbclid=', '&gclid=']:
        if p in url:
            url = url.split(p)[0]
    return url.strip()


def _parse_date(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        cleaned = re.sub(r'\s*IST\s*$', '', raw.strip(), flags=re.IGNORECASE)
        return dateutil_parser.parse(cleaned, fuzzy=True)
    except Exception:
        return None


def _first_date_in(text: str) -> datetime | None:
    """Try every DATE_PATTERNS against text, return first parseable hit."""
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            d = _parse_date(m.group())
            if d:
                return d
    return None


def fallback_date_from_html(html: str) -> tuple[datetime | None, str]:
    soup = BeautifulSoup(html, 'lxml')

    # 1. itemprop="datePublished"
    tag = soup.find(itemprop='datePublished')
    if tag:
        d = _parse_date(tag.get('content') or tag.get_text(strip=True))
        if d:
            return d, 'itemprop:datePublished'

    # 2. itemprop="dateModified"
    tag = soup.find(itemprop='dateModified')
    if tag:
        d = _parse_date(tag.get('content') or tag.get_text(strip=True))
        if d:
            return d, 'itemprop:dateModified'

    # 3. <meta> tags
    for prop in ['article:published_time', 'og:article:published_time',
                 'DC.date', 'pubdate', 'date', 'article:modified_time']:
        tag = (soup.find('meta', attrs={'property': prop}) or
               soup.find('meta', attrs={'name': prop}))
        if tag and tag.get('content'):
            d = _parse_date(tag['content'])
            if d:
                return d, f'meta:{prop}'

    # 4. JSON-LD structured data
    for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
        try:
            data = json.loads(script.string or '')
            items = data if isinstance(data, list) else [data]
            for item in items:
                for key in ('datePublished', 'dateCreated', 'dateModified'):
                    val = item.get(key)
                    if val:
                        d = _parse_date(val)
                        if d:
                            return d, f'json-ld:{key}'
        except Exception:
            pass

    # 5. Elements with date-related class names
    for el in soup.find_all(True, attrs={'class': re.compile(
            r'byline|dateline|timestamp|date|time|publish|posted|updated', re.I)}):
        d = _first_date_in(el.get_text(' ', strip=True))
        if d:
            return d, 'classed-element'

    # 6 & 7. Full visible-text scan — first 5000 chars only
    # Publish date is always in the article header, not deep in the body.
    full_text = soup.get_text(' ')
    head_text = full_text[:5000]

    # 6. Near a publish keyword
    for m in re.finditer(
        r'(?:published|updated|posted|date)[^\n]{0,60}',
        head_text, re.IGNORECASE
    ):
        d = _first_date_in(m.group())
        if d:
            return d, 'fullpage-keyword'

    # 7. Any date pattern in the first 5000 chars
    d = _first_date_in(head_text)
    if d:
        return d, 'fullpage-early'

    return None, 'not_found'


def extract_date(url: str, extractor) -> tuple[datetime | None, str, bool]:
    """
    Returns (datetime | None, strategy, is_valid).
    is_valid=False means no article text — mark as INVALID.
    """
    result = extractor.extract(url)

    # No text and no date — article is inaccessible/invalid
    if not result.get('full_text_extracted') and not result.get('publish_date'):
        # Still try a raw fetch to get the date via fallback, but flag text as missing
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SEC)
            resp.raise_for_status()
            if len(resp.text.strip()) < 500:
                return None, 'no_content', False
            dt, strategy = fallback_date_from_html(resp.text)
            # Has HTML but newspaper3k couldn't extract text — still invalid article
            return dt, strategy, False
        except Exception as e:
            return None, f'fetch_error:{str(e)[:80]}', False

    if result.get('publish_date'):
        return result['publish_date'], 'newspaper3k', True

    # Has text but no date — try fallback
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SEC)
        resp.raise_for_status()
        dt, strategy = fallback_date_from_html(resp.text)
        return dt, strategy, True
    except Exception as e:
        return None, f'fetch_error:{str(e)[:80]}', True


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat()
    return dt.astimezone(timezone.utc).isoformat()

# ── Run modes ─────────────────────────────────────────────────────────────────

def run(limit: int | None = 100):
    label = "ALL" if limit is None else f"first {limit}"
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        all_urls = [clean_url(row['url']) for row in csv.DictReader(f) if row.get('url')]

    seen = set()
    urls = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            urls.append(u)
    if limit:
        urls = urls[:limit]

    extractor = get_extractor()
    date_map, strategy_counts = {}, {}
    null_count = invalid_count = 0

    print(f"\n{'='*70}\nBUILD DATE MAP — {label} URLs\n{'='*70}\n")

    for i, url in enumerate(urls, 1):
        dt, strategy, is_valid = extract_date(url, extractor)
        if not is_valid:
            date_map[url] = 'INVALID'
            invalid_count += 1
            icon = '🚫'
        else:
            iso = to_iso(dt)
            date_map[url] = iso
            if iso is None:
                null_count += 1
            icon = '✅' if iso else '❌'

        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        print(f"  [{i:4d}/{len(urls)}] {icon} {strategy:30s} {url[:60]}")
        time.sleep(DELAY_SEC)

        # Save every 50 URLs so progress survives a crash
        if i % 50 == 0:
            with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                json.dump(date_map, f, indent=2, ensure_ascii=False)

    found = len(urls) - null_count - invalid_count
    print(f"\n{'='*70}\nRESULTS — {label}\n{'='*70}")
    print(f"  Total     : {len(urls)}")
    print(f"  Date found: {found}  ({found/len(urls)*100:.1f}%)")
    print(f"  Null date : {null_count}  ({null_count/len(urls)*100:.1f}%)  ← manually fill")
    print(f"  Invalid   : {invalid_count}  ({invalid_count/len(urls)*100:.1f}%)  ← no article text")
    print(f"\n  Strategy breakdown:")
    for s, c in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        print(f"    {c:4d}  {s}")
    print(f"{'='*70}\n")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(date_map, f, indent=2, ensure_ascii=False)
    print(f"  Saved → {OUTPUT_PATH}\n")


def retry_nulls():
    if not os.path.exists(OUTPUT_PATH):
        print("No dates.json found. Run without --retry-nulls first.")
        return

    with open(OUTPUT_PATH, encoding='utf-8') as f:
        date_map = json.load(f)

    nulls = [url for url, val in date_map.items() if val is None]
    print(f"\n{'='*70}\nRETRY NULLS — {len(nulls)} URLs\n{'='*70}\n")

    extractor = get_extractor()
    strategy_counts, recovered, newly_invalid = {}, 0, 0

    for i, url in enumerate(nulls, 1):
        dt, strategy, is_valid = extract_date(url, extractor)
        if not is_valid:
            date_map[url] = 'INVALID'
            newly_invalid += 1
            icon = '🚫'
        else:
            iso = to_iso(dt)
            if iso:
                date_map[url] = iso
                recovered += 1
            icon = '✅' if iso else '❌'

        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        print(f"  [{i:3d}/{len(nulls)}] {icon} {strategy:30s} {url[:60]}")
        time.sleep(DELAY_SEC)

    still_null = sum(1 for url in nulls if date_map[url] is None)
    print(f"\n{'='*70}")
    print(f"  Recovered     : {recovered}/{len(nulls)}")
    print(f"  Newly invalid : {newly_invalid}/{len(nulls)}")
    print(f"  Still null    : {still_null}/{len(nulls)}  ← manually fill")
    print(f"\n  Strategy breakdown:")
    for s, c in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        print(f"    {c:4d}  {s}")
    print(f"{'='*70}\n")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(date_map, f, indent=2, ensure_ascii=False)
    print(f"  Updated → {OUTPUT_PATH}\n")


if __name__ == '__main__':
    if '--retry-nulls' in sys.argv:
        retry_nulls()
    elif '--all' in sys.argv:
        run(limit=None)
    else:
        run(limit=100)
