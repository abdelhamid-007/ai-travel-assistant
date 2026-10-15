"""Agent 2 - Publisher / Scheduler.

Takes `ready` videos from the queue, writes platform-specific captions, picks
the best free time slot per platform, then posts when each slot is due.

    python publisher.py schedule --platforms telegram,tiktok,instagram
    python publisher.py run            # post everything that is due (cron / loop)
    python publisher.py list
"""
import argparse
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import common
import telegram_api

# Local hours with historically strong engagement, per platform. Starting
# points only: replace them with your own analytics.
BEST_HOURS = {
    "tiktok": [(12, 0), (19, 0), (21, 0)],
    "instagram": [(11, 0), (13, 0), (19, 0)],
    "youtube": [(15, 0), (18, 0)],
    "telegram": [(9, 0), (13, 0), (20, 0)],
}
DEFAULT_HOURS = [(12, 0), (19, 0)]
MAX_ATTEMPTS = 3
TZ_OFFSET = float(os.getenv("TZ_OFFSET_HOURS", "0"))   # your audience's UTC offset

CAPTION_SYSTEM = ("You write social media captions. Reply with JSON only: "
                  '{"caption": str, "hashtags": [str]}. Caption: one hook line + '
                  "one value line, max 200 chars, no emojis. 4 to 6 hashtags without #.")
STYLE = {"tiktok": "punchy and casual", "instagram": "friendly and visual",
         "youtube": "clear and keyword-rich", "telegram": "short and direct"}


def utcnow():
    return datetime.now(timezone.utc)


# ------------------------------------------------------------- scheduling ----
def next_slot(platform: str, after: datetime, taken: set[str]) -> datetime:
    """Earliest best-hour slot strictly after `after` that nobody else uses."""
    tz = timezone(timedelta(hours=TZ_OFFSET))
    local_after = after.astimezone(tz)
    for day in range(0, 60):
        d = (local_after + timedelta(days=day)).date()
        for h, m in BEST_HOURS.get(platform, DEFAULT_HOURS):
            slot = datetime(d.year, d.month, d.day, h, m, tzinfo=tz).astimezone(timezone.utc)
            if slot > after and slot.isoformat() not in taken:
                return slot
    raise RuntimeError("no free slot in the next 60 days")


def make_caption(title: str, topic: str, platform: str) -> tuple[str, list[str]]:
    data = common.llm_json(CAPTION_SYSTEM,
                           f"Platform: {platform} ({STYLE.get(platform, 'neutral')}). "
                           f"Video title: {title}. Topic: {topic}.")
    if isinstance(data, dict) and data.get("caption"):
        tags = [str(t).lstrip("#").replace(" ", "") for t in data.get("hashtags", [])][:6]
        return str(data["caption"])[:220], tags
    words = [w for w in topic.lower().split() if len(w) > 3][:4]
    return f"{title}. Save this for later.", words or ["video"]


def schedule(platforms: list[str], db_path=None, now: datetime | None = None) -> list[dict]:
    con = common.connect(db_path)
    now = now or utcnow()
    created = []
    videos = con.execute("SELECT * FROM videos WHERE status='ready' ORDER BY created_at").fetchall()
    for v in videos:
        for p in platforms:
            taken = {r[0] for r in con.execute(
                "SELECT publish_at FROM posts WHERE platform=?", (p,))}
            slot = next_slot(p, now, taken)
            caption, tags = make_caption(v["title"], v["topic"], p)
            with con:
                con.execute("INSERT OR IGNORE INTO posts (video_id, platform, caption, "
                            "hashtags, publish_at) VALUES (?,?,?,?,?)",
                            (v["id"], p, caption, json.dumps(tags), slot.isoformat()))
            created.append({"video": v["id"], "platform": p, "publish_at": slot.isoformat()})
        with con:
            con.execute("UPDATE videos SET status='scheduled' WHERE id=?", (v["id"],))
    return created


# --------------------------------------------------------------- adapters ----
def _full_caption(post) -> str:
    tags = " ".join("#" + t for t in json.loads(post["hashtags"]))
    return f"{post['caption']}\n\n{tags}".strip()


def post_telegram(post, video):
    chat = os.getenv("TELEGRAM_CHANNEL_ID")
    if not chat:
        raise RuntimeError("TELEGRAM_CHANNEL_ID not set")
    res = telegram_api.send_video(chat, video["path"], _full_caption(post))
    return f"message_id={res['message_id']}"


def post_webhook(post, video):
    """Hand the post to n8n / Zapier / Make / Postiz, which owns the platform
    API credentials (TikTok, Instagram, YouTube...)."""
    url = os.environ["WEBHOOK_URL"]
    body = json.dumps({"platform": post["platform"], "video_path": video["path"],
                       "title": video["title"], "caption": _full_caption(post),
                       "publish_at": post["publish_at"]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return f"webhook {r.status}"


def post_dry_run(post, video):
    return f"DRY RUN: would post '{video['title']}' to {post['platform']}"


def pick_adapter(platform: str):
    if platform == "telegram" and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHANNEL_ID"):
        return post_telegram
    if platform != "telegram" and os.getenv("WEBHOOK_URL"):
        return post_webhook
    return post_dry_run


def run_due(db_path=None, now: datetime | None = None, adapters=None) -> list[dict]:
    """Post everything due. Failures are retried on the next run, up to 3 times."""
    con = common.connect(db_path)
    now = now or utcnow()
    due = con.execute("SELECT * FROM posts WHERE status='scheduled' AND publish_at<=? "
                      "ORDER BY publish_at", (now.isoformat(),)).fetchall()
    report = []
    for post in due:
        video = con.execute("SELECT * FROM videos WHERE id=?", (post["video_id"],)).fetchone()
        adapter = (adapters or {}).get(post["platform"]) or pick_adapter(post["platform"])
        try:
            result, status = adapter(post, video), "posted"
        except Exception as e:                                  # noqa: BLE001
            result = f"error: {e}"
            status = "failed" if post["attempts"] + 1 >= MAX_ATTEMPTS else "scheduled"
        with con:
            con.execute("UPDATE posts SET status=?, attempts=attempts+1, result=? WHERE id=?",
                        (status, result, post["id"]))
            if not con.execute("SELECT 1 FROM posts WHERE video_id=? AND status IN "
                               "('scheduled')", (post["video_id"],)).fetchone():
                con.execute("UPDATE videos SET status='done' WHERE id=?", (post["video_id"],))
        report.append({"post": post["id"], "platform": post["platform"],
                       "status": status, "result": result})
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("schedule")
    s.add_argument("--platforms", default="telegram", help="comma separated")
    sub.add_parser("run")
    sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "schedule":
        out = schedule([p.strip() for p in a.platforms.split(",") if p.strip()])
    elif a.cmd == "run":
        out = run_due()
    else:
        out = [dict(r) for r in common.connect().execute(
            "SELECT id, video_id, platform, publish_at, status, attempts FROM posts "
            "ORDER BY publish_at")]
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
