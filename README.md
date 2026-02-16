# RSS News Collector

Async service that polls RSS/Atom feeds (and optional APIs), normalizes items, checks duplicates, and logs results.

## Features
- RSS/Atom via `feedparser`; async fetch with `httpx` (10s timeout, 3 retries, 5MB cap, jittered backoff).
- Optional GNews API adapter (JSON).
- Normalization: strip HTML (regex), unescape entities, length caps, UTC dates, lowercase unique hashtags (<=20).
- Dedup by `(header, source_name)` (current backend stub is in-memory).
- File logging: `data/raw.jsonl` (raw feed/API entries), `data/processed.jsonl` (normalized + status stored/duplicate).

## Structure
```
news_collector_git/
  config/sources.yaml   # config in JSON syntax
  core/
    client_backend.py   # stub for check_if_news_exists / push_news_to_db
    file_sink.py        # writes raw.jsonl and processed.jsonl
    gnews_adapter.py    # GNews API adapter
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
    { "name": "bbc",        "rss_url": "https://feeds.bbci.co.uk/news/rss.xml",         "enabled": true },
    { "name": "lenta",      "rss_url": "https://lenta.ru/rss",                          "enabled": true },
    { "name": "rbc",        "rss_url": "https://rssexport.rbc.ru/rbcnews/news/20/full.rss", "enabled": false },
    { "name": "ria",        "rss_url": "https://ria.ru/export/rss2/index.xml",          "enabled": true },
    { "name": "tass",       "rss_url": "https://tass.ru/rss/v2.xml",                    "enabled": true },
    { "name": "interfax",   "rss_url": "https://www.interfax.ru/rss.asp",               "enabled": true },
    { "name": "meduza",     "rss_url": "https://meduza.io/rss/all",                     "enabled": true },
    { "name": "rt_ru",      "rss_url": "https://russian.rt.com/rss",                    "enabled": true },
    { "name": "habr",       "rss_url": "https://habr.com/ru/rss/all/all/?fl=ru",        "enabled": true },
    { "name": "village",    "rss_url": "https://www.the-village.ru/rss",                "enabled": true },
    { "name": "bbc_ru",     "rss_url": "http://feeds.bbci.co.uk/russian/rss.xml",       "enabled": true },
    { "name": "dw_ru",      "rss_url": "https://rss.dw.com/russian",                    "enabled": false },
    { "name": "reuters_top","rss_url": "https://feeds.reuters.com/reuters/topNews",     "enabled": false },
    { "name": "ap_top",     "rss_url": "https://feeds.apnews.com/apf-topnews",          "enabled": false },
    { "name": "nyt_world",  "rss_url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "enabled": true },
    { "name": "ars",        "rss_url": "http://feeds.arstechnica.com/arstechnica/index/",       "enabled": true },
    { "name": "hn_front",   "rss_url": "https://hnrss.org/frontpage",                   "enabled": false },
    {
      "name": "gnews_ru",
      "type": "gnews",
      "api_token": "YOUR_GNEWS_TOKEN",
      "enabled": false,
      "params": { "lang": "ru", "topic": "world", "max": 50 }
    }
  ]
}
```
To enable GNews: insert your token and set `"enabled": true`.

## Run
```
python -m news_collector_git.main
```
Logs go to stdout; data snapshots to `data/raw.jsonl` and `data/processed.jsonl`.

## Smoketest
```
python -m news_collector_git.smoke_test
```
Clears data files, resets in-memory dedup, polls sources until ≥10 new items, prints progress.

## Backend integration
Implement real storage in `core/client_backend.py` functions `check_if_news_exists` and `push_news_to_db` without changing signatures.

## Next steps
- Plug real backend/persistent dedup.
- Add rate-limit/semaphore if sources grow.
- Add metrics/healthcheck and unit tests for normalization, retries, dedup, and GNews API.
