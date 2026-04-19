"""
UI для управления источниками:
- просмотр всех источников
- выбор источников для парсинга (enabled=true)
- добавление новых RSS/GNews источников
Запуск: py -3 ui.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, HttpUrl, model_validator

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "sources.yaml"

app = FastAPI(title="UI источников новостей", version="2.0")


class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: Literal["rss", "gnews"] = "rss"
    rss_url: Optional[HttpUrl] = None
    enabled: bool = True
    api_token: Optional[str] = Field(default=None, max_length=256)
    topic: Optional[str] = Field(default=None, max_length=80)
    query: Optional[str] = Field(default=None, max_length=120)
    lang: Optional[str] = Field(default=None, min_length=2, max_length=5)
    max_items: Optional[int] = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def validate_source(self) -> "SourceIn":
        if self.type == "rss" and self.rss_url is None:
            raise ValueError("Для RSS-источника поле rss_url обязательно")
        return self


class EnabledSourcesIn(BaseModel):
    enabled_names: list[str] = Field(default_factory=list)


def clean_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"poll_interval_seconds": 300, "sources": []}
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        raw = file.read().strip()
    if not raw:
        return {"poll_interval_seconds": 300, "sources": []}

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Корневой элемент конфига должен быть объектом")
    sources = data.get("sources")
    if sources is None:
        data["sources"] = []
    elif not isinstance(sources, list):
        raise ValueError("Поле config.sources должно быть списком")
    return data


def save_config(data: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_config_or_500() -> dict[str, Any]:
    try:
        return load_config()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось прочитать конфиг: {exc}") from exc


def save_config_or_500(data: dict[str, Any]) -> None:
    try:
        save_config(data)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить конфиг: {exc}") from exc


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return HTML_PAGE


@app.get("/api/sources")
async def list_sources() -> list[dict[str, Any]]:
    cfg = load_config_or_500()
    return cfg.get("sources", [])


@app.put("/api/sources/enabled")
async def update_enabled_sources(payload: EnabledSourcesIn) -> dict[str, Any]:
    cfg = load_config_or_500()
    sources = cfg.get("sources", [])
    enabled_set = {name.strip().casefold() for name in payload.enabled_names if name.strip()}

    for source in sources:
        name = str(source.get("name", "")).strip().casefold()
        source["enabled"] = name in enabled_set

    cfg["sources"] = sources
    save_config_or_500(cfg)

    enabled_count = sum(1 for source in sources if source.get("enabled", False))
    return {"status": "ok", "enabled_count": enabled_count, "total": len(sources)}


@app.post("/api/sources")
async def add_source(src: SourceIn) -> dict[str, Any]:
    cfg = load_config_or_500()
    sources: list[dict[str, Any]] = cfg.get("sources", [])

    source_name = clean_str(src.name)
    if source_name is None:
        raise HTTPException(status_code=400, detail="Имя источника обязательно")

    if any(str(item.get("name", "")).strip().casefold() == source_name.casefold() for item in sources):
        raise HTTPException(status_code=400, detail="Источник с таким именем уже существует")

    source: dict[str, Any] = {
        "name": source_name,
        "type": src.type,
        "enabled": src.enabled,
    }
    if src.rss_url is not None:
        source["rss_url"] = str(src.rss_url)

    params: dict[str, Any] = {}
    for key, value in {"topic": src.topic, "query": src.query, "lang": src.lang}.items():
        cleaned = clean_str(value)
        if cleaned is not None:
            params[key] = cleaned
    if src.max_items is not None:
        params["max"] = src.max_items
    if params:
        source["params"] = params

    api_token = clean_str(src.api_token)
    if src.type == "gnews" and api_token is not None:
        source["api_token"] = api_token

    sources.append(source)
    cfg["sources"] = sources
    save_config_or_500(cfg)
    return {"status": "ok", "count": len(sources)}


HTML_PAGE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Управление источниками новостей</title>
  <style>
    :root {
      --bg-1: #f7fbff;
      --bg-2: #dff2ff;
      --accent: #0073c8;
      --accent-strong: #005792;
      --line: #d3e6f7;
      --text: #102334;
      --muted: #567188;
      --ok: #0f8c62;
      --error: #b42318;
      --card: rgba(255, 255, 255, 0.92);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Segoe UI Variable", "Trebuchet MS", "Gill Sans", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 20% 20%, rgba(0, 115, 200, 0.12) 0, transparent 36%),
        radial-gradient(circle at 80% 10%, rgba(15, 140, 98, 0.14) 0, transparent 30%),
        linear-gradient(130deg, var(--bg-1), var(--bg-2));
      min-height: 100vh;
      padding: 28px 14px;
    }

    .layout {
      width: min(1200px, 96vw);
      margin: 0 auto;
      display: grid;
      gap: 18px;
      animation: appear 360ms ease-out;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: 0 8px 30px rgba(0, 38, 66, 0.08);
      padding: 18px;
    }

    h1 {
      margin: 0 0 6px;
      font-size: clamp(1.4rem, 1.2rem + 1vw, 2rem);
      letter-spacing: 0.02em;
    }

    .sub {
      margin: 0;
      color: var(--muted);
      font-size: 0.98rem;
    }

    .toolbar {
      margin-top: 12px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    button {
      border: 0;
      border-radius: 9px;
      padding: 10px 14px;
      font-weight: 700;
      letter-spacing: 0.01em;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease;
    }

    button:hover { transform: translateY(-1px); }

    .btn-primary {
      background: linear-gradient(120deg, var(--accent), #0b95ed);
      color: white;
      box-shadow: 0 8px 22px rgba(0, 115, 200, 0.25);
    }

    .btn-secondary {
      background: white;
      color: var(--accent-strong);
      border: 1px solid var(--line);
    }

    .status {
      min-height: 1.3em;
      margin: 0;
      font-weight: 600;
      color: var(--muted);
    }

    .status.ok { color: var(--ok); }
    .status.error { color: var(--error); }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 10px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
    }

    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid #e8f0f6;
      text-align: left;
      vertical-align: top;
      font-size: 0.95rem;
    }

    thead th {
      background: #f2f8fd;
      color: #214055;
      font-size: 0.83rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    tbody tr:hover { background: #f9fcff; }

    .params {
      font-family: "Consolas", "Cascadia Mono", monospace;
      font-size: 0.8rem;
      color: #2a4f65;
      word-break: break-word;
      max-width: 360px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(160px, 1fr));
      gap: 10px;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .field.wide {
      grid-column: 1 / -1;
    }

    label {
      font-size: 0.85rem;
      font-weight: 700;
      color: #2f4a5d;
    }

    input, select {
      width: 100%;
      border: 1px solid #c9dceb;
      border-radius: 8px;
      padding: 9px 10px;
      font-size: 0.96rem;
      background: #fff;
    }

    input[type="checkbox"] {
      width: auto;
      transform: scale(1.1);
      accent-color: var(--accent);
    }

    .inline {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 2px;
    }

    .muted {
      color: var(--muted);
      font-size: 0.84rem;
      margin: 0;
    }

    @keyframes appear {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 880px) {
      .grid { grid-template-columns: 1fr; }
      th, td { padding: 9px 10px; font-size: 0.9rem; }
      button { width: 100%; }
      .toolbar { align-items: stretch; }
    }
  </style>
</head>
<body>
  <main class="layout">
    <section class="card">
      <h1>Панель управления источниками</h1>
      <p class="sub">Выбирайте источники для парсинга и управляйте списком.</p>
      <div class="toolbar">
        <button class="btn-primary" id="save-selection">Сохранить выбор для парсинга</button>
        <button class="btn-secondary" id="reload-list">Обновить</button>
      </div>
      <p id="status" class="status"></p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Парсить</th>
              <th>Имя</th>
              <th>Тип</th>
              <th>URL</th>
              <th>Параметры</th>
            </tr>
          </thead>
          <tbody id="sources-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Добавить новый источник</h2>
      <form id="add-form" class="grid">
        <div class="field">
          <label for="name">Имя</label>
          <input id="name" name="name" required maxlength="80" />
        </div>
        <div class="field">
          <label for="type">Тип</label>
          <select id="type" name="type">
            <option value="rss">rss</option>
            <option value="gnews">gnews</option>
          </select>
        </div>
        <div class="field wide">
          <label for="rss_url">RSS URL (обязательно для типа rss)</label>
          <input id="rss_url" name="rss_url" type="url" required placeholder="https://example.com/rss.xml" />
        </div>
        <div class="field">
          <label for="topic">Тема GNews</label>
          <input id="topic" name="topic" placeholder="world" maxlength="80" />
        </div>
        <div class="field">
          <label for="query">Запрос GNews</label>
          <input id="query" name="query" maxlength="120" />
        </div>
        <div class="field">
          <label for="lang">Язык</label>
          <input id="lang" name="lang" maxlength="5" placeholder="ru" />
        </div>
        <div class="field">
          <label for="max_items">Макс. новостей</label>
          <input id="max_items" name="max_items" type="number" min="1" max="100" placeholder="50" />
        </div>
        <div class="field wide">
          <label for="api_token">GNews API token (необязательно)</label>
          <input id="api_token" name="api_token" />
        </div>
        <div class="field wide">
          <label class="inline">
            <input id="enabled" type="checkbox" name="enabled" checked />
            <span>Включить сразу</span>
          </label>
          <p class="muted">Для выбора источников к парсингу отмечайте чекбоксы в таблице и нажимайте «Сохранить выбор для парсинга».</p>
        </div>
        <div class="field wide">
          <button class="btn-primary" type="submit">Добавить источник</button>
        </div>
      </form>
      <p id="add-status" class="status"></p>
    </section>
  </main>

  <script>
    const statusEl = document.getElementById('status');
    const addStatusEl = document.getElementById('add-status');
    const bodyEl = document.getElementById('sources-body');
    const typeEl = document.getElementById('type');
    const rssUrlEl = document.getElementById('rss_url');

    function showStatus(message, kind = 'info') {
      statusEl.textContent = message;
      statusEl.className = 'status' + (kind === 'ok' ? ' ok' : kind === 'error' ? ' error' : '');
    }

    function showAddStatus(message, kind = 'info') {
      addStatusEl.textContent = message;
      addStatusEl.className = 'status' + (kind === 'ok' ? ' ok' : kind === 'error' ? ' error' : '');
    }

    function setRssRequired() {
      const isRss = typeEl.value === 'rss';
      rssUrlEl.required = isRss;
      rssUrlEl.placeholder = isRss ? 'https://example.com/rss.xml' : 'необязательно для gnews';
    }

    function paramsToText(params) {
      if (!params || typeof params !== 'object') {
        return '-';
      }
      const entries = Object.entries(params);
      if (!entries.length) {
        return '-';
      }
      return entries.map(([k, v]) => `${k}=${v}`).join(', ');
    }

    function renderSources(sources) {
      bodyEl.innerHTML = '';
      for (const source of sources) {
        const tr = document.createElement('tr');

        const tdEnabled = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'enabled-toggle';
        checkbox.dataset.name = String(source.name || '');
        checkbox.checked = Boolean(source.enabled);
        tdEnabled.appendChild(checkbox);

        const tdName = document.createElement('td');
        tdName.textContent = String(source.name || '');

        const tdType = document.createElement('td');
        tdType.textContent = String(source.type || 'rss');

        const tdUrl = document.createElement('td');
        if (source.rss_url) {
          const link = document.createElement('a');
          link.href = String(source.rss_url);
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = String(source.rss_url);
          tdUrl.appendChild(link);
        } else {
          tdUrl.textContent = '-';
        }

        const tdParams = document.createElement('td');
        tdParams.className = 'params';
        tdParams.textContent = paramsToText(source.params);

        tr.append(tdEnabled, tdName, tdType, tdUrl, tdParams);
        bodyEl.appendChild(tr);
      }
    }

    async function loadSources() {
      showStatus('Загрузка источников...');
      try {
        const res = await fetch('/api/sources');
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || res.statusText);
        }
        renderSources(data);
        const enabled = data.filter(item => item.enabled).length;
        showStatus(`Загружено источников: ${data.length}, включено для парсинга: ${enabled}.`, 'ok');
      } catch (err) {
        showStatus('Ошибка: ' + err.message, 'error');
      }
    }

    async function saveSelection() {
      const enabledNames = Array.from(document.querySelectorAll('.enabled-toggle'))
        .filter(box => box.checked)
        .map(box => box.dataset.name)
        .filter(Boolean);

      showStatus('Сохранение выбранных источников...');
      try {
        const res = await fetch('/api/sources/enabled', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled_names: enabledNames })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || res.statusText);
        }
        showStatus(`Сохранено: включено ${data.enabled_count} из ${data.total}.`, 'ok');
        await loadSources();
      } catch (err) {
        showStatus('Ошибка: ' + err.message, 'error');
      }
    }

    async function submitAddForm(event) {
      event.preventDefault();
      const form = new FormData(event.target);
      const payload = {
        name: String(form.get('name') || '').trim(),
        type: String(form.get('type') || 'rss'),
        enabled: form.get('enabled') === 'on'
      };

      const rssUrl = String(form.get('rss_url') || '').trim();
      if (rssUrl) {
        payload.rss_url = rssUrl;
      }
      const apiToken = String(form.get('api_token') || '').trim();
      if (apiToken) {
        payload.api_token = apiToken;
      }
      const topic = String(form.get('topic') || '').trim();
      if (topic) {
        payload.topic = topic;
      }
      const query = String(form.get('query') || '').trim();
      if (query) {
        payload.query = query;
      }
      const lang = String(form.get('lang') || '').trim();
      if (lang) {
        payload.lang = lang;
      }
      const maxItems = String(form.get('max_items') || '').trim();
      if (maxItems) {
        payload.max_items = Number(maxItems);
      }

      showAddStatus('Добавление источника...');
      try {
        const res = await fetch('/api/sources', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || res.statusText);
        }
        showAddStatus(`Источник добавлен. Всего источников: ${data.count}.`, 'ok');
        event.target.reset();
        document.getElementById('enabled').checked = true;
        setRssRequired();
        await loadSources();
      } catch (err) {
        showAddStatus('Ошибка: ' + err.message, 'error');
      }
    }

    document.getElementById('reload-list').addEventListener('click', loadSources);
    document.getElementById('save-selection').addEventListener('click', saveSelection);
    document.getElementById('add-form').addEventListener('submit', submitAddForm);
    typeEl.addEventListener('change', setRssRequired);

    setRssRequired();
    loadSources();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    uvicorn.run("ui:app", host="127.0.0.1", port=9000, reload=False)
