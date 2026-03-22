"""
Quick test: extract 2 articles from each new source and verify text is extracted.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from hindu_extractor import HinduExtractor
from ndtv_extractor import NDTVExtractor
from indian_express_extractor import IndianExpressExtractor

LIMIT = 2  # articles per source

results = {}

for cls, name in [
    (HinduExtractor,        'The Hindu'),
    (NDTVExtractor,         'NDTV'),
    (IndianExpressExtractor,'Indian Express'),
]:
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    extractor = cls()
    articles = extractor.extract(max_articles=LIMIT)
    success = sum(1 for a in articles if a.get('full_text_extracted'))
    results[name] = {'total': len(articles), 'success': success}

    for a in articles:
        status = '✅' if a.get('full_text_extracted') else '❌'
        print(f"  {status} {a['title'][:65]}")
        print(f"     chars={len(a.get('text',''))} | url={a['url'][:70]}")

# ── Final summary ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for name, r in results.items():
    print(f"  {name:20s}: {r['success']}/{r['total']} text extracted")
print(f"{'='*60}")
