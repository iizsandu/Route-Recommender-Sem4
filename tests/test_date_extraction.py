"""
Test: Date extraction from article URLs using the current ArticleTextExtractor.

Purpose:
    3250 articles were stored in MongoDB with no publish_date (date=None).
    This test verifies whether the current extractor still fails to extract dates
    from a representative sample of URLs across all news sources.

Why date matters:
    Crime articles often use relative dates ("this Wednesday", "last Sunday").
    Without a publish_date as reference, exact crime dates cannot be resolved.

Usage:
    cd backend
    python ../tests/test_date_extraction.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from article_text_extractor import get_extractor
from datetime import datetime

# ── Representative sample URLs across sources ─────────────────────────────────
# Mix of sources known to have date extraction issues.
# These are real URLs from files/urls.csv (tracking params intentionally left on
# some to verify clean_url() strips them correctly).
TEST_URLS = [
    # Times of India
    {
        'url': 'https://timesofindia.indiatimes.com/city/delhi/rape-pocso-convict-who-jumped-bail-in-2022-held-by-delhi-crime-branch/articleshow/127631461.cms&ved=2ahUKEwjN4I2FkuaSAxWpR2wGHXlWEYw4ChDF9AF6BAgDEAI&usg=AOvVaw1H1Zfhg0bazLP_EA6piCXx',
        'source': 'Times of India',
    },
    # Indian Express
    {
        'url': 'https://indianexpress.com/article/legal-news/why-delhi-high-court-wants-more-judges-to-handle-organised-crime-cases-immediately-10540387/&ved=2ahUKEwjOsd34keaSAxWLT2wGHZRZDC0QxfQBegQIChAC&usg=AOvVaw2BeEO1xWn69nFHEqQudsYn',
        'source': 'Indian Express',
    },
    # Hindustan Times
    {
        'url': 'https://www.hindustantimes.com/cities/delhi-news/7-yrs-on-the-run-gangster-bobby-kabootar-arrested-101771438229939.html&ved=2ahUKEwjOsd34keaSAxWLT2wGHZRZDC0QxfQBegQIBxAC&usg=AOvVaw3wO8Ztus0EW57HV80o6kn8',
        'source': 'Hindustan Times',
    },
    # Siasat
    {
        'url': 'https://www.siasat.com/delhi-mohammed-umardeen-shot-dead-while-trying-to-rescue-son-3371864/&ved=2ahUKEwjOsd34keaSAxWLT2wGHZRZDC0QxfQBegQIARAC&usg=AOvVaw389uyiIy_zzBbA3PtK4LRA',
        'source': 'Siasat',
    },
    # ANI News
    {
        'url': 'https://www.aninews.in/news/national/general-news/delhi-man-released-from-jail-shot-dead-in-rohini20260214215235&ved=2ahUKEwjN4I2FkuaSAxWpR2wGHXlWEYw4ChDF9AF6BAgKEAI&usg=AOvVaw0hTtHME-gJ5YIlJK8BF9G3',
        'source': 'ANI News',
    },
    # India TV News (date in URL slug — good test for URL-based fallback)
    {
        'url': 'https://www.indiatvnews.com/delhi/delhi-crime-report-2025-murder-rape-robbery-cases-drop-sharply-police-claim-improved-law-and-order-check-details-here-2026-01-21-1026792&ved=2ahUKEwiC47OLkuaSAxV5g2MGHRdLCrc4FBDF9AF6BAgJEAI&usg=AOvVaw1qnn_VCJVao0Zg9OG4WgNY',
        'source': 'India TV News',
    },
    # Livemint
    {
        'url': 'https://www.livemint.com/focus/aap-seeks-meeting-with-delhi-police-commissioner-flags-concerns-over-violent-crime-11771500160194.html&ved=2ahUKEwjOsd34keaSAxWLT2wGHZRZDC0QxfQBegQICRAC&usg=AOvVaw1YCAL6OUb9dbsXuUn1R4mn',
        'source': 'Livemint',
    },
    # OmmCom News
    {
        'url': 'https://ommcomnews.com/india-news/delhi-crime-numbers-show-downward-trend-in-2025/&ved=2ahUKEwiC47OLkuaSAxV5g2MGHRdLCrc4FBDF9AF6BAgDEAI&usg=AOvVaw2IKyUac5NCXcjUTUQKPyiT',
        'source': 'OmmCom News',
    },
]

# ── Run extraction ─────────────────────────────────────────────────────────────

def run_test():
    extractor = get_extractor()
    results = []

    print(f"\n{'='*70}")
    print("DATE EXTRACTION TEST — using ArticleTextExtractor (newspaper3k)")
    print(f"{'='*70}")
    print(f"Testing {len(TEST_URLS)} URLs across {len(set(u['source'] for u in TEST_URLS))} sources\n")

    for entry in TEST_URLS:
        url = entry['url']
        source = entry['source']

        print(f"  [{source}]")
        print(f"  URL: {url[:80]}...")

        result = extractor.extract(url, source=source)

        cleaned_url = result['url']
        publish_date = result['publish_date']
        full_text = result['full_text_extracted']
        error = result.get('error')

        # Check if URL was cleaned correctly (tracking params stripped)
        url_cleaned = cleaned_url != url
        date_extracted = publish_date is not None

        status_date = '✅' if date_extracted else '❌'
        status_text = '✅' if full_text else '❌'
        status_url  = '✅' if url_cleaned else '⚠️ '

        print(f"  {status_url} URL cleaned : {cleaned_url[:80]}")
        print(f"  {status_text} Text        : {'extracted' if full_text else 'FAILED'} | chars={result.get('text_length', 0)}")
        print(f"  {status_date} Date        : {publish_date if date_extracted else 'NOT EXTRACTED (None)'}")
        if error:
            print(f"  ⚠️  Error      : {error[:100]}")
        print()

        results.append({
            'source': source,
            'url': url,
            'cleaned_url': cleaned_url,
            'url_cleaned': url_cleaned,
            'date_extracted': date_extracted,
            'publish_date': publish_date,
            'full_text_extracted': full_text,
            'error': error,
        })

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(results)
    dates_found    = sum(1 for r in results if r['date_extracted'])
    text_found     = sum(1 for r in results if r['full_text_extracted'])
    urls_cleaned   = sum(1 for r in results if r['url_cleaned'])
    dates_missing  = total - dates_found

    print(f"{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Total URLs tested   : {total}")
    print(f"  URL cleaned         : {urls_cleaned}/{total}")
    print(f"  Text extracted      : {text_found}/{total}")
    print(f"  Date extracted      : {dates_found}/{total}")
    print(f"  Date MISSING (None) : {dates_missing}/{total}  ← root cause of the 3250 issue")
    print(f"{'='*70}")

    if dates_missing > 0:
        print("\n  ⚠️  DIAGNOSIS: newspaper3k failed to extract publish_date for some URLs.")
        print("  Possible causes:")
        print("    1. Site uses JS-rendered date (newspaper3k is static HTML only)")
        print("    2. Date is in a non-standard meta tag newspaper3k doesn't recognise")
        print("    3. Date is embedded in the URL slug (e.g. /2026-01-21/) — not parsed")
        print("    4. Tracking params in URL caused a redirect that broke parsing")
        print("\n  NEXT STEP: Run test_date_extraction_debug.py to inspect raw HTML")
        print("             and identify which meta tags carry the date on each site.")
    else:
        print("\n  ✅ All dates extracted successfully — issue may be resolved.")

    print(f"{'='*70}\n")
    return results


if __name__ == '__main__':
    run_test()
