

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




