"""Builds a portfolio video from the agent-only audio: title, captions, and a live waveform.

Usage: python make_video.py   (reads salma_only_new.wav, writes voice_agent_demo.mp4 next to it)

The input is the agent channel of a Vapi stereo recording (Vapi puts the caller on the left channel and
the agent on the right), so the caller's voice is never in the video. Edit CAPTIONS to match your call.
Needs: pip install numpy pillow imageio-ffmpeg
"""
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
AUDIO = HERE / "salma_only_new.wav"
OUT = HERE / "voice_agent_demo.mp4"
W, H, FPS = 1920, 1080, 25

BG, PANEL, TEXT, MUTED, ACCENT, GREEN = "#0f1117", "#1a1d27", "#f2f3f5", "#9aa0ac", "#5b8def", "#3ecf8e"
FONT, BOLD = "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"
def f(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

# (start, end, kind, lines) — times in seconds, from the call transcript
CAPTIONS = [
    (0.0, 6.5, "agent", ["\"Hello. Thank you for calling.", "I'm Salma, the travel assistant.\""]),
    (6.5, 10.0, "caller", ["\"What are your offers?\""]),
    (10.0, 14.0, "tool", ["Searching live trips in the database…", "list_destinations()"]),
    (14.0, 27.0, "result", ["Hammamet  from 780 DT", "Djerba  from 690 DT"]),
]
STYLE = {"agent": ("SALMA (AI AGENT)", ACCENT), "caller": ("CALLER", MUTED),
         "tool": ("TOOL CALL", "#f5a524"), "result": ("ANSWER FROM LIVE DATABASE", GREEN)}

with wave.open(str(AUDIO), "rb") as w:
    rate = w.getframerate()
    samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
duration = len(samples) / rate
# loudness per video frame, for the waveform
per = rate // FPS
levels = np.array([np.sqrt(np.mean(samples[i * per:(i + 1) * per] ** 2)) for i in range(int(duration * FPS))])
levels = levels / (np.percentile(levels, 99) or 1)


def frame(i):
    t = i / FPS
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # header
    d.text((120, 90), "AI Voice Agent for a Travel Agency", font=f(64, True), fill=TEXT)
    d.text((120, 175), "Answers phone calls from live PostgreSQL data  ·  Vapi · FastAPI · pgvector",
           font=f(34), fill=MUTED)

    # waveform: last 3 seconds, newest on the right
    n_bars, bar_w, gap, mid = 120, 10, 4, 470
    x0 = (W - n_bars * (bar_w + gap)) // 2
    for b in range(n_bars):
        k = i - (n_bars - 1 - b)
        lv = float(min(levels[k], 1.2)) if 0 <= k < len(levels) else 0.0
        h = max(4, int(lv * 150))
        color = ACCENT if b > n_bars - 8 else "#3a4766"
        d.rounded_rectangle([x0 + b * (bar_w + gap), mid - h, x0 + b * (bar_w + gap) + bar_w, mid + h], 4, fill=color)

    # caption card
    cap = next((c for c in CAPTIONS if c[0] <= t < c[1]), None)
    if cap:
        label, color = STYLE[cap[2]]
        d.rounded_rectangle([120, 690, W - 120, 940], 24, fill=PANEL, outline=color, width=3)
        d.text((170, 720), label, font=f(30, True), fill=color)
        size = 58 if cap[2] == "result" else 46
        for li, line in enumerate(cap[3]):
            d.text((170, 775 + li * (size + 18)), line, font=f(size, cap[2] == "result"), fill=TEXT)

    # progress bar
    d.rectangle([0, H - 8, int(W * t / duration), H], fill=ACCENT)
    return img


tmp = Path(tempfile.mkdtemp())
try:
    for i in range(len(levels)):
        frame(i).save(tmp / f"{i:05d}.png")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "%05d.png"),
                    "-i", str(AUDIO), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", str(OUT)], check=True)
finally:
    shutil.rmtree(tmp)
print(f"saved {OUT.name} ({OUT.stat().st_size / 1024 / 1024:.1f} MB, {duration:.0f}s)")
