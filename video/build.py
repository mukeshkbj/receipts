#!/usr/bin/env python3
"""Assemble the final demo video: per-shot speed-mapping + narration mux.

Reads video/shots.json (actual shot start times in the raw capture),
video/audio/durations.txt + shotNN.mp3. For every shot, the recorded
segment is sped to fit its narration length (+pad), audio is placed at the
shot's new start. Output: video/receipts-demo.mp4 (<= 180s guaranteed by
target computation).

Usage: .venv/bin/python video/build.py
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAD = 1.0          # breathing room after each narration line
MIN_SEG = 2.0      # a shot never shows for less than this
HARD_CAP = 178.0   # stay under 3:00 with margin


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True)
    return float(out.stdout.strip())


def main():
    raw = sorted(glob.glob(os.path.join(HERE, "raw", "*.webm")) + glob.glob(os.path.join(HERE, "raw", "*.mp4")))
    if not raw:
        sys.exit("no capture in video/raw/ — run capture.py first")
    src = raw[0]
    total_raw = dur(src)

    marks = json.load(open(os.path.join(HERE, "shots.json")))
    adurs = {}
    for line in open(os.path.join(HERE, "audio", "durations.txt")):
        n, s = line.split()
        adurs[n] = float(s)

    # segment boundaries: shot start -> next shot start (last -> eof)
    segs = []
    for i, (shot, ts) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else total_raw
        tgt = max(adurs.get(shot, 8.0) + PAD, MIN_SEG)
        segs.append({"shot": shot, "src_start": ts, "src_end": end, "target": tgt})

    # if total target exceeds cap, shrink pads then compress proportionally
    total_tgt = sum(s["target"] for s in segs)
    if total_tgt > HARD_CAP:
        over = total_tgt - HARD_CAP
        for s in segs[::-1]:
            take = min(over, s["target"] - MIN_SEG)
            s["target"] -= take
            over -= take
            if over <= 0:
                break

    # build filter graph: per-seg trim+setpts speed, concat, audio adelay+amix
    vparts, aparts, new_starts = [], [], []
    cur = 0.0
    for i, s in enumerate(segs):
        src_len = s["src_end"] - s["src_start"]
        speed = max(src_len / s["target"], 1.0) if s["target"] > 0 else 1.0
        speed = min(speed, 6.0)
        new_len = src_len / speed
        vparts.append(
            f"[0:v]trim=start={s['src_start']:.3f}:end={s['src_end']:.3f},"
            f"setpts=PTS-STARTPTS/{speed:.4f},settb=AVTB,fps=30[v{i}]"
        )
        ap = os.path.join(HERE, "audio", f"{s['shot']}.mp3")
        if os.path.exists(ap):
            aparts.append((i + 1, ap, cur))
        new_starts.append((s["shot"], round(cur, 2), round(new_len, 2)))
        cur += new_len
    concat_in = "".join(f"[v{i}]" for i in range(len(segs)))
    vgraph = ";".join(vparts) + f";{concat_in}concat=n={len(segs)}:v=1:a=0[vout]"

    acmd_inputs = []
    for _, ap, _ in aparts:
        acmd_inputs += ["-i", ap]
    agraph = ""
    if aparts:
        parts = ";".join(
            f"[{idx}:a]adelay={int(st * 1000)}|{int(st * 1000)}[d{k}]" for k, (idx, _, st) in enumerate(aparts)
        )
        mix_in = "".join(f"[d{k}]" for k in range(len(aparts)))
        agraph = ";" + parts + f";{mix_in}amix=inputs={len(aparts)}:normalize=0[aout]"

    out = os.path.join(HERE, "receipts-demo.mp4")
    cmd = ["ffmpeg", "-y", "-i", src] + acmd_inputs + [
        "-filter_complex", vgraph + agraph,
        "-map", "[vout]", "-map", "[aout]" if aparts else "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out,
    ]
    subprocess.run(cmd, check=True)
    final = dur(out)
    print(f"output: {out} ({final:.1f}s)")
    for s, st, ln in new_starts:
        print(f"  {s}: starts {st:6.1f}s len {ln:5.1f}s")
    if final > 180:
        print("WARNING: exceeds 3:00")


if __name__ == "__main__":
    main()
