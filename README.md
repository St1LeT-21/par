# News Parser (Spec Implementation)

Парсер RSS, который отправляет каждую новость в внешний backend `/test/save_news` и сразу останавливается, если backend говорит, что новость уже существует.

## Ключевые правила (из ТЗ)
- Источник уникальности — только backend (ответ `created`).
- Новости обрабатываются от новых к старым.
- На `created == false` — немедленно прекращаем обработку текущей ленты.
- После прохода спим 300 секунд и повторяем цикл.
- Никакого локального кеша/дедупа.

## Что в коде
- `main.py` — главный цикл: загружает источники, парсит RSS, шлёт в backend, sleep 300 c.
- `rss_parser.py` — загрузка RSS (httpx, 3 ретрая, 5 MB лимит), парсинг `feedparser`, нормализация.
- `backend_client.py` — POST `/test/save_news` (base url берётся из `BACKEND_BASE_URL` или `http://localhost:8000`).
- `config_loader.py` — читает `config/sources.yaml` (JSON) и отдаёт включённые RSS-источники.
- `core/models.py` — `SourceConfig`, `NewsItem`.
- `core/normalizer.py` — чистка HTML, unescape, усечения, UTC даты, хэштеги.

## Конфиг источников
`config/sources.yaml` (JSON):
```json
{
  "sources": [
    { "name": "bbc", "rss_url": "https://feeds.bbci.co.uk/news/rss.xml", "enabled": true },
    { "name": "lenta", "rss_url": "https://lenta.ru/rss", "enabled": true },
    { "name": "ria", "rss_url": "https://ria.ru/export/rss2/index.xml", "enabled": true }
  ]
}
```
Все `type != "rss"` или `enabled: false` игнорируются.

## Запуск
```
python -m news_collector_git.main
```
Переменная `BACKEND_BASE_URL` (опц.) указывает на работающий backend (Docker из TestApp-main.zip).

## Формат отправки
```json
{
  "title": "string",
  "body": "string",
  "source": "string",
  "hash_tags": ["string"],
  "published_at": "ISO-8601 datetime"
}
```
Ожидаемый ответ backend:
```
{ "news_id": number, "cluster_id": number, "created": boolean }
```
`created=false` → стоп обработки текущей ленты до следующего цикла.

## Зависимости
Python 3.10+, `feedparser`, `httpx`.
