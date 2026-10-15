"""Telegram front-end for the video agents (long polling, no extra packages).

    /video <topic>       generate a video and send it back
    /schedule <topic>    generate it and queue it for the Publisher agent
    /queue               show upcoming posts

Set TELEGRAM_ALLOWED_USERS=123,456 to restrict who can spend your compute.
"""
import os
import threading
import time

import common
import producer
import publisher
import telegram_api as tg

ALLOWED = {u.strip() for u in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()}
HELP = ("Send /video <topic> and I will make a short vertical video.\n"
        "/schedule <topic> queues it for posting.\n/queue shows what is scheduled.")
_busy = threading.Lock()       # one render at a time keeps the CPU usable


def handle(chat_id, user_id, text: str) -> None:
    if ALLOWED and str(user_id) not in ALLOWED:
        tg.send_message(chat_id, "Sorry, you are not allowed to use this bot.")
        return
    cmd, _, arg = text.strip().partition(" ")
    cmd, arg = cmd.split("@")[0].lower(), arg.strip()
    if cmd in ("/start", "/help"):
        tg.send_message(chat_id, HELP)
    elif cmd in ("/video", "/schedule"):
        if not arg:
            tg.send_message(chat_id, f"Usage: {cmd} <topic>")
        elif not _busy.acquire(blocking=False):
            tg.send_message(chat_id, "Still rendering another video, try again in a minute.")
        else:
            try:
                tg.send_message(chat_id, "Working on it...")
                info = producer.produce(arg)
                tg.send_video(chat_id, info["path"], info["title"])
                if cmd == "/schedule":
                    plan = publisher.schedule(["telegram"])
                    tg.send_message(chat_id, "Scheduled: " + ", ".join(
                        f"{p['platform']} at {p['publish_at'][:16]} UTC" for p in plan))
            except Exception as e:                              # noqa: BLE001
                tg.send_message(chat_id, f"Something went wrong: {e}")
            finally:
                _busy.release()
    elif cmd == "/queue":
        rows = common.connect().execute(
            "SELECT platform, publish_at, status FROM posts ORDER BY publish_at DESC LIMIT 10").fetchall()
        tg.send_message(chat_id, "\n".join(
            f"{r['publish_at'][:16]} {r['platform']} {r['status']}" for r in rows) or "Queue is empty.")
    else:
        tg.send_message(chat_id, HELP)


def main():
    if not tg.TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (create one with @BotFather).")
    offset = None
    print("Bot running. Ctrl+C to stop.")
    while True:
        try:
            for upd in tg.get_updates(offset):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                if msg.get("text"):
                    threading.Thread(target=handle, daemon=True, args=(
                        msg["chat"]["id"], msg["from"]["id"], msg["text"])).start()
        except Exception as e:                                  # noqa: BLE001
            print("poll error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
