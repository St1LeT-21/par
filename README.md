# RSS News Collector

Minimal async service that polls RSS/Atom feeds, normalizes items, checks duplicates, and logs results.

## Features
- Supports RSS 2.0, RSS 1.0/RDF, Atom via `feedparser`.
- Async fetching with httpx: 10s timeout, 3 retries, 5 MB cap, exponential backoff + jitter.
- Normalization: strip HTML (regex), unescape entities, length caps, UTC dates, lowercase unique hashtags (max 20).
- Deduplication by `(header, source_name)` (backend stub uses in-memory set).
- File logging: raw feed entries and processed items.

## Structure
```
news_collector_git/
  config/sources.yaml   # config in JSON syntax
  core/
    client_backend.py   # stub for check_if_news_exists / push_news_to_db
    file_sink.py        # writes raw.jsonl and processed.jsonl
    models.py
    normalizer.py
    rss_adapter.py
    scheduler.py
  data/                 # generated logs (ignored by git)
  main.py               # infinite polling loop
  smoke_test.py         # quick test runner
```

## Requirements
Python 3.10+ and:
```
pip install feedparser httpx
```

## Config
`config/sources.yaml` (JSON subset):
```json
{
  "poll_interval_seconds": 300,
  "sources": [
    { "name": "bbc",  "rss_url": "https://feeds.bbci.co.uk/news/rss.xml", "enabled": true },
    { "name": "lenta","rss_url": "https://lenta.ru/rss",                  "enabled": true },
    { "name": "ria",  "rss_url": "https://ria.ru/export/rss2/index.xml",  "enabled": true },
    { "name": "rbc",  "rss_url": "https://rssexport.rbc.ru/rbcnews/news/20/full.rss", "enabled": false }
  ]
}
```

## Run
```
python -m news_collector_git.main
```
Logs go to stdout; data snapshots to `data/raw.jsonl` (raw feed entries) and `data/processed.jsonl` (normalized items with status stored/duplicate).

## Smoketest
```
python -m news_collector_git.smoke_test
```
Clears data files, resets in-memory dedup, polls sources until >=10 new items (usually one pass), prints progress.

## Integrate backend
Implement real storage in `core/client_backend.py` functions `check_if_news_exists` and `push_news_to_db` without changing signatures.

## Next steps
- Replace stub backend with DB/HTTP service.
- Add rate-limit/semaphore if many sources.
- Add metrics/healthcheck and unit tests for normalization, retries, and dedup.
