"""
Simple visual UI to view and add RSS sources.
Run: python ui.py
Opens a small FastAPI app on http://127.0.0.1:9000
"""

import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
import uvicorn

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "sources.yaml"

app = FastAPI(title="RSS Sources UI", version="1.0")


class SourceIn(BaseModel):
    name: str
    rss_url: HttpUrl
    enabled: bool = True


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.get("/api/sources")
async def list_sources():
    cfg = load_config()
    return cfg.get("sources", [])


@app.post("/api/sources")
async def add_source(src: SourceIn):
    cfg = load_config()
    sources: List[dict] = cfg.get("sources", [])
    # uniqueness by name
    if any(s.get("name") == src.name for s in sources):
        raise HTTPException(status_code=400, detail="Source with this name already exists")
    sources.append(
        {
            "name": src.name,
            "rss_url": str(src.rss_url),
            "enabled": src.enabled,
            "type": "rss",
        }
    )
    cfg["sources"] = sources
    save_config(cfg)
    return {"status": "ok", "count": len(sources)}


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>RSS Sources</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 960px; margin: 40px auto; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border: 1px solid #ddd; padding: 8px; }
    th { background: #f2f2f2; text-align: left; }
    .status { margin-top: 12px; color: #006400; }
    .error { color: #b22222; }
  </style>
</head>
<body>
  <h2>Configured RSS Sources</h2>
  <div id="status" class="status"></div>
  <table id="sources">
    <thead>
      <tr><th>Name</th><th>URL</th><th>Enabled</th><th>Type</th></tr>
    </thead>
    <tbody></tbody>
  </table>

  <h3>Add new source</h3>
  <form id="add-form">
    <label>Name <input required name="name"></label><br><br>
    <label>RSS URL <input required name="rss_url" style="width:400px"></label><br><br>
    <label><input type="checkbox" name="enabled" checked> Enabled</label><br><br>
    <button type="submit">Add</button>
  </form>

  <script>
    async function loadSources() {
      const res = await fetch('/api/sources');
      const data = await res.json();
      const tbody = document.querySelector('#sources tbody');
      tbody.innerHTML = '';
      data.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${s.name}</td><td><a href="${s.rss_url}" target="_blank">${s.rss_url}</a></td><td>${s.enabled}</td><td>${s.type || 'rss'}</td>`;
        tbody.appendChild(tr);
      });
      document.getElementById('status').textContent = `Loaded ${data.length} source(s)`;
    }

    document.getElementById('add-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = new FormData(e.target);
      const payload = {
        name: form.get('name'),
        rss_url: form.get('rss_url'),
        enabled: form.get('enabled') === 'on'
      };
      const status = document.getElementById('status');
      status.textContent = 'Saving...';
      status.className = 'status';
      try {
        const res = await fetch('/api/sources', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || res.statusText);
        }
        status.textContent = 'Saved. Reloading list...';
        e.target.reset();
        await loadSources();
      } catch (err) {
        status.textContent = 'Error: ' + err.message;
        status.className = 'status error';
      }
    });

    loadSources();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    uvicorn.run("ui:app", host="127.0.0.1", port=9000, reload=False)
