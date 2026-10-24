#!/usr/bin/env python3
"""Generate narration audio per shot via ElevenLabs -> video/audio/shotNN.mp3

Usage: ELEVENLABS_API_KEY=xi_... .venv/bin/python video/tts.py [voice_id]
Default voice: Brian (deep, clear — good for product demos).
Writes audio/durations.txt: shotNN <seconds>
"""
import json
import os
import sys
import urllib.request

import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio")
KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE = sys.argv[1] if len(sys.argv) > 1 else "nPczCjzI2devNBz1zQrb"  # Brian
MODEL = "eleven_multilingual_v2"


def tts(text, out_path):
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128",
        data=json.dumps({
            "text": text,
            "model_id": MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True},
        }).encode(),
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        open(out_path, "wb").write(r.read())


def dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def main():
    if not KEY:
        sys.exit("set ELEVENLABS_API_KEY")
    os.makedirs(AUDIO, exist_ok=True)
    total = 0.0
    lines = [l.split("|", 1) for l in open(os.path.join(HERE, "narration.txt")) if "|" in l]
    with open(os.path.join(AUDIO, "durations.txt"), "w") as df:
        for name, text in lines:
            p = os.path.join(AUDIO, f"{name}.mp3")
            tts(text.strip(), p)
            d = dur(p)
            total += d
            df.write(f"{name} {d:.2f}\n")
            print(f"{name}: {d:.1f}s — {text.strip()[:60]}")
    print(f"total narration: {total:.1f}s")


if __name__ == "__main__":
    main()
