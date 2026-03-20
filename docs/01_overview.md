# Project Overview

## What Is This?

This is a **Delhi Crime Data Collection System** — a full-stack application designed to aggregate, extract, and store crime-related news articles from multiple sources into a structured database. The data is intended for downstream analysis, crime mapping, and AI-based information extraction.

The system is not a consumer-facing app. It is a **data pipeline** with a web UI to control and monitor the extraction process.

---

## Goals

- Collect as many Delhi-focused crime news articles as possible from the open web
- Store them in a structured, deduplicated MongoDB database
- Extract structured crime information (type, location, date, victim, weapon) using LLMs
- Support YouTube news channel transcription as an additional data source

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│         Article Extractor UI + YouTube Extractor UI      │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (REST)
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI Backend                          │
│              backend/main.py (:8000)                     │
└──┬──────────────┬──────────────┬───────────────┬────────┘
   │              │              │               │
   ▼              ▼              ▼               ▼
Google News    Times of      NewsData.io    YouTube
Extractor      India          Extractor     Pipeline
               Extractor
   │              │              │               │
   └──────────────┴──────────────┘               │
                  │                              │
                  ▼                              ▼
         MongoDB (crime2)               MongoDB (crime2)
         └── articles2                 └── youtube
         └── articles
                  │
                  ▼
     Crime Extraction Service
     (Separate microservice)
     Cerebras LLM → Azure Cosmos DB
```

---

## Two Separate Services

### 1. Main Backend (`backend/`)
Handles all article collection. Runs on port `8000`.

### 2. Crime Extraction Service (`crime_extraction_service/`)
A separate FastAPI microservice that reads articles from MongoDB, uses an LLM to extract structured crime data, and stores results in Azure Cosmos DB. Runs independently on its own port.

---

## Data Flow Summary

1. User triggers extraction from the frontend UI
2. Backend calls one or more extractors (Google News, TOI, NewsData.io)
3. Each extractor fetches article URLs and passes them through the centralized `ArticleTextExtractor`
4. Full article text is extracted using `newspaper3k`
5. Articles are saved to MongoDB `crime2.articles2` with URL-based deduplication
6. Separately, the Crime Extraction Service reads those articles, sends them to Cerebras LLM, and stores structured crime records in Azure Cosmos DB

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| Delhi-only keywords | Focused dataset for a specific geographic scope |
| Unique index on `url` | Prevents duplicate articles at the database level |
| Centralized `ArticleTextExtractor` | Single source of truth for all text extraction logic |
| Progress file (`extraction_progress.json`) | Allows resuming interrupted extraction runs |
| NewsData.io credit tracking | Free tier has 200 credits/day; tracked locally to avoid waste |
| Cerebras + Ollama fallback | Fast cloud LLM with local fallback if rate-limited |
