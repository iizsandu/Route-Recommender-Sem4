"""
Test: Generic HTML fallback date extraction for sources where newspaper3k returns None.

Strategy (in order):
  1. itemprop="datePublished"  — schema.org, used by most modern news sites
  2. itemprop="dateModified"   — schema.org fallback (ANI uses this)
  3. <meta> tags               — og:article:published_time, article:published_time, DC.date
  4. Byline text regex         — plain date strings in byline divs (TOI uses this)

This covers TOI and ANI without any per-source code, and will work for
most other sources that follow schema.org conventions.

Usage:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python ../tests/test_date_fallback.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser
from datetime import datetime
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# The 2 URLs that failed newspaper3k date extraction
FAILING_URLS = [
    {
        'url': 'https://timesofindia.indiatimes.com/city/delhi/rape-pocso-convict-who-jumped-bail-in-2022-held-by-delhi-crime-branch/articleshow/127631461.cms',
        'source': 'Times of India',
        # From manual inspection: date lives in <div class="xf8Pm byline">TNN / <span>Jan 27, 2026, 20:39 IST</span></div>
    },
    {
        'url': 'https://www.aninews.in/news/national/general-news/delhi-man-released-from-jail-shot-dead-in-rohini20260214215235',
        'source': 'ANI News',
        # From manual inspection: <span itemprop="dateModified">...<span class="first">Feb</span> 14, 2026 21:52</span>
    },
]

# ── Fallback extractor ────────────────────────────────────────────────────────

def extract_date_from_html(html: str, source: str = '') -> datetime | None:
    """
    Generic fallback date extractor. Tries 4 strategies in order.
    No per-source logic — works on schema.org conventions + common patterns.
    """
    soup = BeautifulSoup(html, 'lxml')

    # Strategy 1: itemprop="datePublished" (schema.org standard)
    tag = soup.find(itemprop='datePublished')
    if tag:
        raw = tag.get('content') or tag.get_text(strip=True)
        date = _parse(raw)
        if date:
            return date, 'itemprop=datePublished'

    # Strategy 2: itemprop="dateModified" (ANI uses this)
    tag = soup.find(itemprop='dateModified')
    if tag:
        raw = tag.get('content') or tag.get_text(strip=True)
        date = _parse(raw)
        if date:
            return date, 'itemprop=dateModified'

    # Strategy 3: <meta> tags
    meta_props = [
        'article:published_time',
        'og:article:published_time',
        'DC.date',
        'pubdate',
        'date',
    ]
    for prop in meta_props:
        tag = soup.find('meta', attrs={'property': prop}) or \
              soup.find('meta', attrs={'name': prop})
        if tag and tag.get('content'):
            date = _parse(tag['content'])
            if date:
                return date, f'meta:{prop}'

    # Strategy 4: Byline text regex — elements with date-related class names (TOI)
    date_pattern = re.compile(
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
        r'\s+\d{1,2},?\s+\d{4}(?:[,\s]+\d{1,2}:\d{2}(?:\s*[AP]M)?(?:\s*IST)?)?\b',
        re.IGNORECASE
    )
    for el in soup.find_all(True, attrs={'class': re.compile(
            r'byline|dateline|timestamp|date|time|publish', re.I)}):
        text = el.get_text(' ', strip=True)
        match = date_pattern.search(text)
        if match:
            date = _parse(match.group())
            if date:
                return date, f'byline-regex ({el.name}.{el.get("class", [""])[0]})'

    # Strategy 5: Full-page text regex — catches classless elements like Filmfare's
    #   <div><span>Published on </span> Feb 5, 2026, 16:44 IST</div>
    full_text = soup.get_text(' ')
    for m in re.finditer(
        r'(?:published|updated|posted)[^\n]{0,40}?' + date_pattern.pattern,
        full_text, re.IGNORECASE
    ):
        date = _parse(m.group())
        if date:
            return date, 'fullpage-regex'

    return None, 'not found'


def _parse(raw: str) -> datetime | None:
    """Parse a date string with dateutil, return None on failure."""
    if not raw:
        return None
    try:
        # Strip IST suffix — dateutil doesn't know IST
        cleaned = re.sub(r'\s*IST\s*$', '', raw.strip(), flags=re.IGNORECASE)
        return dateutil_parser.parse(cleaned, fuzzy=True)
    except Exception:
        return None


# ── Run test ──────────────────────────────────────────────────────────────────

def run():
    print(f"\n{'='*70}")
    print("FALLBACK DATE EXTRACTION TEST")
    print(f"{'='*70}\n")

    results = []

    for entry in FAILING_URLS:
        url, source = entry['url'], entry['source']
        print(f"  [{source}]")
        print(f"  {url}\n")

        # Fetch raw HTML
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            html = resp.text
            print(f"  HTML fetched: {len(html):,} chars")
        except Exception as e:
            print(f"  ❌ Fetch failed: {e}\n")
            results.append({'source': source, 'success': False, 'date': None, 'strategy': 'fetch failed'})
            continue

        date, strategy = extract_date_from_html(html, source)

        if date:
            print(f"  ✅ Date found  : {date}")
            print(f"  Strategy used  : {strategy}")
            results.append({'source': source, 'success': True, 'date': date, 'strategy': strategy})
        else:
            print(f"  ❌ Date NOT found — all 4 strategies failed")
            print(f"  → Inspect the HTML manually to find the date element")
            results.append({'source': source, 'success': False, 'date': None, 'strategy': strategy})

        print()

    # Summary
    print(f"{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    success = sum(1 for r in results if r['success'])
    for r in results:
        icon = '✅' if r['success'] else '❌'
        print(f"  {icon} {r['source']:20s} | {str(r['date'])[:30]:30s} | via: {r['strategy']}")
    print(f"\n  {success}/{len(results)} sources now have dates via fallback")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    run()
