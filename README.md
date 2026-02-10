

## Структура
```
news_collector/
  config/
    sources.yaml      # источники и интервал опроса
  core/
    client_backend.py # заглушка бекенда: check_if_news_exists, push_news_to_db
    models.py         # модели NewsItem, SourceConfig
    normalizer.py     # правила нормализации
    rss_adapter.py    # загрузка+парсинг RSS/Atom с ретраями и лимитами
    scheduler.py      # основной цикл опроса
  main.py             # точка входа: запускает бесконечный опрос
```

## Требования
Python 3.10+ и зависимости:
```
pip install feedparser httpx PyYAML beautifulsoup4
```


## Запуск
1) Настройте источники в `config/sources.yaml` (ключ `poll_interval_seconds`, список `sources` с полями `name`, `rss_url`, `enabled`).
2) Запустите:
```
python -m news_collector.main
```
Логирование по умолчанию пишет в stdout.


