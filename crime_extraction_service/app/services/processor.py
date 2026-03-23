"""
Orchestrates the full pipeline:
  MongoDB article → LLM extraction → geocoding → Cosmos DB storage
"""
from typing import Dict
from app.services.llm_extractor import extract_crime_info
from app.services.validator import build_crime_record
from app.services.geocoder import normalize_location, geocode
from app.db.mongodb import mongodb_client
from app.db.cosmosdb import cosmosdb_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def process_batch(limit: int = 10, reprocess: bool = False) -> Dict:
    """
    Fetch up to `limit` articles from MongoDB, extract crime info, geocode, store in Cosmos DB.
    If reprocess=False, skips articles already marked processed=True.
    """
    stats = {"processed": 0, "successful": 0, "failed": 0, "skipped": 0, "errors": []}

    articles = await mongodb_client.fetch_unprocessed_articles(limit, reprocess=reprocess)
    if not articles:
        logger.warning("no_articles_to_process")
        return stats

    stats["processed"] = len(articles)

    for article in articles:
        url = article.get("url", "")
        article_text = article.get("full_text") or article.get("text") or ""
        article_id = str(article.get("_id", ""))

        # Pull publish date from DB — try common field names, normalize to ISO string
        raw_date = article.get("published_date") or article.get("date") or article.get("scraped_at")
        article_date = None
        if raw_date:
            try:
                if hasattr(raw_date, "isoformat"):
                    article_date = raw_date.date().isoformat()
                else:
                    # string — strip time portion if present
                    article_date = str(raw_date)[:10]
            except Exception:
                article_date = None

        if not url:
            logger.warning("article_missing_url", article_id=article_id)
            stats["skipped"] += 1
            continue

        if not article_text.strip():
            logger.warning("article_empty_text", url=url[:60])
            stats["skipped"] += 1
            continue

        try:
            # 1. LLM extraction — pass article publish date as anchor
            llm_data = extract_crime_info(article_text, article_date)
            if not llm_data:
                logger.warning("llm_extraction_failed", url=url[:60])
                stats["failed"] += 1
                stats["errors"].append(f"LLM failed: {url[:80]}")
                continue

            # 2. Geocoding — exact first, broad as fallback
            loc_exact = llm_data.get("location_exact")
            loc_broad = llm_data.get("location_broad")
            coords = geocode(loc_exact, loc_broad)

            # Track which location string was actually resolved
            loc_exact_norm = normalize_location(loc_exact) if loc_exact else None
            loc_broad_norm = normalize_location(loc_broad) if loc_broad else None
            location_used = loc_exact_norm or loc_broad_norm

            # 3. Build record
            record = build_crime_record(url, llm_data, location_used, coords)
            if not record:
                stats["failed"] += 1
                continue

            # 4. Store in Cosmos DB
            success = await cosmosdb_client.upsert_crime_record(record)
            if success:
                stats["successful"] += 1
                await mongodb_client.mark_article_processed(article_id)
            else:
                stats["failed"] += 1
                stats["errors"].append(f"Cosmos insert failed: {url[:80]}")

        except Exception as e:
            logger.error("article_processing_error", url=url[:60], error=str(e))
            stats["failed"] += 1
            stats["errors"].append(f"Error ({url[:60]}): {str(e)}")

    logger.info(
        "batch_done",
        processed=stats["processed"],
        successful=stats["successful"],
        failed=stats["failed"],
        skipped=stats["skipped"],
    )
    return stats
