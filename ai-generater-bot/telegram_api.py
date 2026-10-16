"""Minimal Telegram Bot API client (standard library only)."""
import json
import mimetypes
import os
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import common  # noqa: F401  (loads .env before TOKEN is read)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def _url(method: str, token: str | None = None) -> str:
    return f"https://api.telegram.org/bot{token or TOKEN}/{method}"


def call(method: str, params: dict | None = None, token: str | None = None, timeout=60):
    data = urllib.parse.urlencode(params or {}).encode()
    with urllib.request.urlopen(_url(method, token), data=data, timeout=timeout) as r:
        out = json.load(r)
    if not out.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {out}")
    return out["result"]


def send_message(chat_id, text: str, token: str | None = None):
    return call("sendMessage", {"chat_id": chat_id, "text": text}, token)


def send_video(chat_id, video_path: str, caption: str = "", token: str | None = None):
    """Upload an MP4 with multipart/form-data (limit: 50 MB for bots)."""
    boundary = uuid.uuid4().hex
    path = Path(video_path)
    parts = []
    for k, v in {"chat_id": str(chat_id), "caption": caption[:1024],
                 "supports_streaming": "true"}.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"'
                     f"\r\n\r\n{v}\r\n".encode())
    ctype = mimetypes.guess_type(path.name)[0] or "video/mp4"
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="video"; '
                 f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode())
    parts.append(path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        _url("sendVideo", token), data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)
    if not out.get("ok"):
        raise RuntimeError(f"Telegram sendVideo failed: {out}")
    return out["result"]


def get_updates(offset: int | None, timeout: int = 30):
    params = {"timeout": timeout, "allowed_updates": json.dumps(["message"])}
    if offset is not None:
        params["offset"] = offset
    return call("getUpdates", params, timeout=timeout + 10)
