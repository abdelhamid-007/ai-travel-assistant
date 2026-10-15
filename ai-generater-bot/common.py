"""Shared config, SQLite queue and LLM helper for both video agents."""
import json
import os
import sqlite3
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ROOT / "output"))
DB_PATH = Path(os.getenv("QUEUE_DB", ROOT / "output" / "queue.sqlite"))

# Any OpenAI-compatible server works: Ollama (default), OpenAI, LM Studio...
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id          TEXT PRIMARY KEY,
    topic       TEXT NOT NULL,
    title       TEXT NOT NULL,
    script      TEXT NOT NULL,          -- JSON: scenes
    path        TEXT NOT NULL,
    duration    REAL NOT NULL,
    status      TEXT NOT NULL DEFAULT 'ready',   -- ready | scheduled | done
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL REFERENCES videos(id),
    platform    TEXT NOT NULL,
    caption     TEXT NOT NULL,
    hashtags    TEXT NOT NULL,
    publish_at  TEXT NOT NULL,          -- ISO 8601 UTC
    status      TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled | posted | failed
    attempts    INTEGER NOT NULL DEFAULT 0,
    result      TEXT,
    UNIQUE(video_id, platform)
);
"""


def connect(db_path=None):
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def llm_json(system: str, user: str, timeout: int = 120):
    """Ask the LLM for a JSON object. Returns None if the model is unreachable
    or the answer is not valid JSON, so callers can use a fallback."""
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(
        f"{LLM_BASE_URL}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {LLM_API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = json.load(r)["choices"][0]["message"]["content"]
        return json.loads(text)
    except Exception:
        return None
