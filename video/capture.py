#!/usr/bin/env python3
"""Record the Receipts demo walkthrough with playwright video capture.

Drives the real UI, holds each shot for at least its narration length,
logs actual per-shot start times to video/shots.json for the build step.

Usage: .venv/bin/python video/capture.py [--url http://localhost:8000]
"""
import argparse
import json
import os
import time

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PREPARED_RUN = "85269d0858e8"  # Chroma MEASURED run
BRIEF = ("we need a vector database for ~10M vectors, p99 query latency under 30ms, "
         "cosine similarity, under $400/mo. explicitly evaluate: Pinecone, Weaviate, Chroma, Qdrant. "
         "we currently pay $700/mo for Pinecone")
REPLY = ("Thanks for your interest — happy to confirm details for your diligence. "
         "Chroma's free tier is permanent, no credit card required — here's the docs link. "
         "On uptime: Chroma Cloud targets 99.9% and our status history is public. "
         "Re SOC 2 — our report is available under NDA through the trust center.")


def shot_durations():
    durs = {}
    p = os.path.join(HERE, "audio", "durations.txt")
    if os.path.exists(p):
        for line in open(p):
            n, s = line.split()
            durs[n] = float(s)
    return durs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    a = ap.parse_args()
    durs = shot_durations()
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)

    t0 = time.time()
    marks = []

    def hold(shot, extra=1.0):
        """Hold until the shot's narration duration + padding has elapsed."""
        target = durs.get(shot, 8.0) + extra
        start = marks[-1][1]
        wait = target - ((time.time() - t0) - start)
        if wait > 0:
            time.sleep(wait)

    def mark(shot):
        marks.append([shot, time.time() - t0])
        print(f"[{time.time()-t0:6.1f}s] {shot}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = browser.new_context(
            viewport={"width": 1600, "height": 900},
            record_video_dir=os.path.join(HERE, "raw"),
            record_video_size={"width": 1600, "height": 900},
        )
        page = ctx.new_page()
        page.goto(a.url, wait_until="networkidle")
        mark("shot01")
        hold("shot01")

        # shot02 — type the brief, run
        page.fill("#brief", "")
        page.type("#brief", BRIEF, delay=12)
        mark("shot02")
        hold("shot02", 0.5)
        page.click("#run-btn")

        # shot03 — requirements gate: wait, tweak a weight, confirm
        mark("shot03")
        try:
            page.wait_for_selector("#req-gate:not(.hidden)", timeout=120000)
            ws = page.query_selector_all(".req-w")
            if len(ws) > 1:
                ws[1].fill("")
                ws[1].type("5", delay=60)
            time.sleep(0.8)
        except Exception as e:
            print("gate wait failed:", e)
        hold("shot03")
        try:
            page.click("#req-confirm")
        except Exception:
            pass

        # shot04/05 — live trace (stays for its audio, real pipeline ticks)
        mark("shot04")
        hold("shot04")
        mark("shot05")
        hold("shot05")

        # switch to the prepared completed run for the result scenes
        page.click(f'.run-link[data-id="{PREPARED_RUN}"]')
        page.wait_for_timeout(1500)

        # shot06 — open a MEASURED claim (Chroma), evidence drawer
        mark("shot06")
        page.click('.chip[data-f="measured"]')
        page.wait_for_timeout(600)
        row = page.query_selector('.claim-row[data-verdict="measured"]')
        if row:
            row.click()
            page.wait_for_timeout(800)
        hold("shot06")
        page.click("#drawer-close")

        # shot07 — contradicted claim evidence
        mark("shot07")
        page.click('.chip[data-f="contradicted"]')
        page.wait_for_timeout(600)
        row = page.query_selector('.claim-row[data-verdict="contradicted"]')
        if row:
            row.click()
            page.wait_for_timeout(800)
        hold("shot07")
        page.click("#drawer-close")
        page.click('.chip[data-f="all"]')

        # shot08 — coverage grid: scroll to top of result
        mark("shot08")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(600)
        hold("shot08")

        # shot09 — scroll to outreach drafts
        mark("shot09")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(700)
        hold("shot09")

        # shot10 — paste vendor reply, ingest (live mutation on prepared run)
        mark("shot10")
        try:
            sums = page.query_selector_all("details summary")
            for s in sums:
                if "reply" in (s.inner_text() or ""):
                    s.click()
                    break
            tb = page.query_selector(".reply-text")
            if tb:
                tb.fill(REPLY)
                page.wait_for_timeout(500)
                page.query_selector(".reply-btn").click()
        except Exception as e:
            print("reply shot failed:", e)
        hold("shot10")

        # shot11 — telemetry + end card
        mark("shot11")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(800)
        hold("shot11", 2.0)

        ctx.close()
        browser.close()

    json.dump(marks, open(os.path.join(HERE, "shots.json"), "w"), indent=1)
    print("total:", round(time.time() - t0, 1), "s — video in video/raw/")


if __name__ == "__main__":
    main()
