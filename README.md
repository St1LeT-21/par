# RSS News Collector

Минималистичный сервис для периодического сбора новостей из RSS/Atom, нормализации полей и передачи новых записей в бекенд.

## Возможности
- Поддержка RSS 2.0, RSS 1.0/RDF, Atom через `feedparser`.
- Асинхронный опрос источников с ретраями, тайм-аутом 10 c и лимитом 5 MB на ленту.
- Нормализация заголовка/текста/даты/тегов по заданным правилам, даты приводятся к UTC.
- Дедуп по `(header, source_name)` с остановкой обработки источника при первом дубле.
- Простая конфигурация в `config/sources.yaml`.

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
`beautifulsoup4` опционален, но улучшает очистку HTML в тексте.

## Запуск
1) Настройте источники в `config/sources.yaml` (ключ `poll_interval_seconds`, список `sources` с полями `name`, `rss_url`, `enabled`).
2) Запустите:
```
python -m news_collector.main
```
Логирование по умолчанию пишет в stdout.

## Интеграция с бекендом
`core/client_backend.py` сейчас хранит состояния в памяти. Замените реализации `check_if_news_exists` и `push_news_to_db` на реальные HTTP/DB вызовы. Интерфейс оставляйте прежним.

## Расширение
Базовый класс `SourceAdapter` позволяет добавить другие типы источников (HTML scraping, REST API, Telegram). Создайте адаптер с методом `fetch() -> list[NewsItem]` и подключите его в планировщике.

## Что улучшить дальше
- Подключить реальный бекенд и постоянное хранилище для дедупа.
- Ограничить число одновременных задач или добавить семафор, если источников много.
- Добавить метрики/healthcheck и тесты для нормализации, ретраев и дедупа.
- Настроить graceful shutdown с отменой задач.
