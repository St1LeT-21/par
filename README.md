# News Parser

1) Цели и задачи проекта  
- Асинхронно собирает новости из RSS и GNews.  
- Отправляет каждую новость в внешний backend (`/test/save_news`).  
- Прекращает обработку конкретного источника только если backend отвечает HTTP 200 и `created=false` (дубликат на стороне сервера).  
- Все сетевые ошибки, таймауты и коды HTTP != 200 лишь логируются; разбор продолжается.

2) Основные функции и возможности  
- Загрузка RSS с `httpx` и экспоненциальным бэкоффом; лимит ленты 5 MB.  
- Парсинг через `feedparser`, нормализация текста/дат, добор полного текста страницы при пустом контенте (BeautifulSoup).  
- Поддержка GNews API (top-headlines), сбор по теме/запросу, нормализация в общий формат.  
- Транспорт в backend с трёхсоставным результатом: `True` (создано), `False` (`created=false` → стоп источника), `None` (любая сетевая/HTTP/JSON ошибка → лог и продолжение).  
- Периодический цикл: обходит все включённые источники, спит `SLEEP_SECONDS`, повторяет.

3) Зависимости  
- Python 3.10+.  
- Основные пакеты: `httpx`, `feedparser`, `beautifulsoup4`, `fastapi`/`uvicorn` (для тестового backend из репозитория), `pydantic`.  
- Установка: `pip install -r requirements.txt`.

4) Настройка программы  
- Конфиг источников: `config/sources.yaml`, пример:
  ```yaml
  sources:
    - name: bbc
      type: rss
      rss_url: https://feeds.bbci.co.uk/news/rss.xml
      enabled: true
    - name: gnews-top
      type: gnews
      params:
        topic: world
        api_token: YOUR_TOKEN
      enabled: true
  ```
  Поля `enabled: false` игнорируются.  
- Переменные окружения:  
  - `BACKEND_BASE_URL` (по умолчанию `http://localhost:8080`)  
  - `BACKEND_SAVE_NEWS_ENDPOINT` (по умолчанию `/test/save_news`)  
  - `SLEEP_SECONDS` (цикл ожидания, по умолчанию 300)  
  - `REQUEST_TIMEOUT` (секунд, по умолчанию 10)  
  - `MAX_RETRIES` (по умолчанию 3)  
  - `LOG_LEVEL` (например, `INFO`, `DEBUG`).

5) Запуск программы  
- (Опционально) создать виртуальное окружение и установить зависимости.  
- Запуск:  
  ```bash
  python main.py
  ```
  или  
  ```bash
  python -m main
  ```
  Перед запуском убедитесь, что тестовый backend поднят и принимает POST на `BACKEND_SAVE_NEWS_ENDPOINT`.

6) Пример работы  
```
2026-02-23 10:00:00 [INFO] root: Parser started
2026-02-23 10:00:00 [INFO] root: Processing source: bbc
2026-02-23 10:00:01 [INFO] root: Sent news to backend (source=bbc, created=True)
2026-02-23 10:00:02 [WARNING] root: Backend returned status 500, continuing parsing
2026-02-23 10:00:03 [INFO] root: Backend returned created=false, stopping source bbc
2026-02-23 10:00:03 [INFO] root: Sleeping for 300 seconds
```
Лента останавливается только на `created=false`; любые другие ошибки логируются и не прерывают разбор источника.
