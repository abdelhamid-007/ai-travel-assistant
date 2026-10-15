# AI Generater Bot — automatic video creation + scheduled posting

Two agents and a Telegram bot that turn a **topic** into a **captioned vertical video**
(1080x1920) and post it at the **best time** for each platform.

```
Telegram chat ──► Agent 1: Video Producer ──► queue (SQLite) ──► Agent 2: Publisher ──► Telegram channel
 "/video topic"   script → scenes → voice →                      captions + best-time     / TikTok, Instagram,
                  frames → ffmpeg MP4                            slots + retries          YouTube (via webhook)
```

| File | Role |
|---|---|
| `producer.py` | **Agent 1.** LLM writes the script, Pillow renders each scene, optional TTS voice-over, ffmpeg builds the MP4 |
| `publisher.py` | **Agent 2.** Platform-specific captions/hashtags, picks the next free best-hour slot, posts when due, retries 3x |
| `telegram_bot.py` | Chat interface: `/video`, `/schedule`, `/queue` |
| `telegram_api.py` | Tiny Telegram client (no extra packages) |
| `test_agents.py` | 6 offline tests (real MP4 render, slot logic, retry/failure handling) |

## Run it

Requirements: Python 3.12+, `ffmpeg`, and optionally Ollama (any OpenAI-compatible LLM) and `espeak-ng` (voice-over).

```bash
cd ai-generater-bot
pip install -r requirements.txt
cp .env.example .env && set -a && . ./.env && set +a

python producer.py "3 tips to save money while travelling"   # makes output/<id>/video.mp4
python publisher.py schedule --platforms telegram,tiktok     # captions + best-time slots
python publisher.py run                                      # post what is due (run from cron every 5 min)
python telegram_bot.py                                       # control it all from Telegram
python -m unittest -v                                        # tests, no internet needed
```

## Behaviour worth knowing

- **No LLM? It still works.** If the model is unreachable or returns bad JSON, a template script/caption is used and the result says `script_source: fallback`.
- **No TTS installed?** The video is silent with timed captions. With `espeak-ng`, scene length follows the voice.
- **Safe by default.** Without `TELEGRAM_CHANNEL_ID` / `WEBHOOK_URL`, the Publisher does a *dry run* and only logs what it would post.
- **Best times** are starting-point hours per platform in `BEST_HOURS` (local to `TZ_OFFSET_HOURS`); replace with your own analytics. Slots never collide and never repeat a post.
- **TikTok / Instagram / YouTube** are posted through a webhook (n8n, Make, Postiz) that holds those platforms' API credentials; the payload is `platform, video_path, title, caption, publish_at`.
- Lock the bot with `TELEGRAM_ALLOWED_USERS` so strangers can't use your compute.

## Limits (honest)

- Visuals are **text-on-gradient slides**, not generative AI footage. The script, captions and scheduling are AI-driven; the renderer in `build_video()` is the single place to swap in a generative video/image API (Runway, Luma, Replicate, HeyGen...).
- The Telegram path was tested through its logic and mocks only; it needs a real bot token to run end to end. Bots can upload videos up to 50 MB.
