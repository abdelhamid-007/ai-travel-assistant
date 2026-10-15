"""Agent 1 - Video Producer.

topic -> script (LLM) -> scenes -> captioned frames -> voice-over -> MP4
Output is vertical 1080x1920 (TikTok / Reels / Shorts). The finished video is
registered in the queue as `ready` for the Publisher agent.

    python producer.py "3 tips to save money while travelling"
"""
import argparse
import json
import re
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import common

W, H, FPS = 1080, 1920, 30
WORDS_PER_SECOND = 2.6          # speaking pace used when there is no voice track
PALETTES = [((15, 32, 68), (46, 134, 193)), ((60, 20, 80), (200, 80, 120)),
            ((10, 60, 50), (60, 180, 140)), ((70, 40, 10), (230, 150, 50))]
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
]

SYSTEM = ("You write scripts for 30-45 second vertical social videos. "
          'Reply with JSON only: {"title": str, "scenes": [{"text": str}]}. '
          "4 to 6 scenes, each 1-2 short spoken sentences, strong hook first, "
          "call to action last. No emojis.")


# ---------------------------------------------------------------- script ----
def clean_scenes(raw) -> list[dict]:
    scenes = []
    for s in (raw or []):
        text = (s.get("text") if isinstance(s, dict) else str(s) or "").strip()
        if text:
            scenes.append({"text": text})
    return scenes[:8]


def fallback_script(topic: str) -> dict:
    """Template script used when no LLM is reachable (keeps the pipeline alive)."""
    return {"title": topic.strip().capitalize(), "scenes": [
        {"text": f"Want to know about {topic}? Watch this."},
        {"text": "Start with the one thing that matters most."},
        {"text": "Then keep it simple and do it consistently."},
        {"text": "Small steps beat perfect plans every time."},
        {"text": "Follow for more, and share this with a friend."}]}


def write_script(topic: str) -> tuple[dict, str]:
    data = common.llm_json(SYSTEM, f"Topic: {topic}")
    scenes = clean_scenes(data.get("scenes")) if isinstance(data, dict) else []
    if len(scenes) >= 3:
        return {"title": str(data.get("title") or topic)[:100], "scenes": scenes}, "llm"
    return fallback_script(topic), "fallback"


# ----------------------------------------------------------------- voice ----
def synthesize(text: str, out_wav: Path) -> bool:
    """Voice-over with a local TTS engine if installed. Returns False if none."""
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        return False
    r = subprocess.run([exe, "-s", "165", "-w", str(out_wav), text],
                       capture_output=True)
    return r.returncode == 0 and out_wav.exists()


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip())


# ---------------------------------------------------------------- frames ----
def _font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def gradient(top, bottom) -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(
            int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def render_frame(text: str, index: int, total: int, title: str, path: Path):
    top, bottom = PALETTES[index % len(PALETTES)]
    img = gradient(top, bottom)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 150), title, font=_font(46), fill=(255, 255, 255, 200), anchor="mm")
    font = _font(78)
    lines = textwrap.wrap(text, width=18)
    line_h = 100
    y = H // 2 - (len(lines) * line_h) // 2
    for line in lines:
        d.text((W // 2 + 3, y + 3), line, font=font, fill=(0, 0, 0), anchor="mm")
        d.text((W // 2, y), line, font=font, fill=(255, 255, 255), anchor="mm")
        y += line_h
    bar_w = W - 160                      # progress bar
    d.rectangle([80, H - 140, 80 + bar_w, H - 126], fill=(255, 255, 255, 60))
    d.rectangle([80, H - 140, 80 + int(bar_w * (index + 1) / total), H - 126],
                fill=(255, 255, 255))
    img.save(path)


# -------------------------------------------------------------- assemble ----
def build_video(script: dict, workdir: Path) -> tuple[Path, float]:
    scenes = script["scenes"]
    clips, has_voice = [], shutil.which("espeak-ng") or shutil.which("espeak")
    for i, scene in enumerate(scenes):
        frame = workdir / f"scene{i}.png"
        render_frame(scene["text"], i, len(scenes), script["title"], frame)
        wav = workdir / f"scene{i}.wav"
        voiced = synthesize(scene["text"], wav)
        if voiced:
            dur = probe_duration(wav) + 0.4
        else:
            dur = max(2.5, len(scene["text"].split()) / WORDS_PER_SECOND + 0.6)
        clip = workdir / f"scene{i}.mp4"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", f"{dur:.2f}",
               "-i", str(frame)]
        cmd += ["-i", str(wav)] if voiced else \
               ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=44100:cl=mono"]
        cmd += ["-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
                "-ar", "44100", "-ac", "1", "-shortest", str(clip)]
        subprocess.run(cmd, check=True)
        clips.append(clip)
    listing = workdir / "clips.txt"
    listing.write_text("".join(f"file '{c.name}'\n" for c in clips))
    out = workdir / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", "-movflags", "+faststart",
                    str(out)], check=True)
    return out, probe_duration(out)


def produce(topic: str, db_path=None) -> dict:
    """Full pipeline for one topic. Returns the queue row as a dict."""
    script, source = write_script(topic)
    vid = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:30] + "-" + uuid.uuid4().hex[:6]
    workdir = common.OUTPUT_DIR / vid
    workdir.mkdir(parents=True, exist_ok=True)
    video, duration = build_video(script, workdir)
    for tmp in list(workdir.glob("scene*")) + [workdir / "clips.txt"]:
        tmp.unlink(missing_ok=True)
    (workdir / "script.json").write_text(json.dumps(script, indent=2))
    con = common.connect(db_path)
    with con:
        con.execute("INSERT INTO videos (id, topic, title, script, path, duration) "
                    "VALUES (?,?,?,?,?,?)",
                    (vid, topic, script["title"], json.dumps(script), str(video), duration))
    return {"id": vid, "title": script["title"], "path": str(video),
            "duration": round(duration, 1), "script_source": source}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("topic", nargs="+", help="one or more video topics")
    for t in ap.parse_args().topic:
        print(json.dumps(produce(t), indent=2))
