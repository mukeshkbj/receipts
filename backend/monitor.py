"""Watch v0: deterministic post-decision monitoring.

No LLM — re-probes public surface on an interval and diffs a snapshot:
homepage reachability, homepage content hash (catches pricing-page edits),
and statuspage incident count (catches new outages).
Set WATCH_INTERVAL_SEC (default 6h; use e.g. 120 for demos).
"""
import hashlib
import json
import os
import threading
import time
import urllib.parse

import httpx

from . import db
from .checks import _statuspage_incidents, _domain
from .util import trace

INTERVAL = int(os.environ.get("WATCH_INTERVAL_SEC", 6 * 3600))


def add_watch(run_id):
    if db.one("SELECT id FROM watches WHERE run_id=?", (run_id,)):
        return None
    wid = db.ins("INSERT INTO watches(run_id,created_at,last_check) VALUES(?,?,?)", (run_id, time.time(), 0))
    trace(run_id, "monitor", "Watching started — periodic status/incident/page-change checks", actor="check")
    return wid


def _probe(cand):
    home = (cand.get("homepage") or "").rstrip("/")
    out = {"home_status": None, "home_hash": None, "incidents_90d": None}
    if home:
        try:
            r = httpx.get(home, timeout=15, follow_redirects=True)
            out["home_status"] = r.status_code
            out["home_hash"] = hashlib.sha256(r.text.encode()) .hexdigest()[:16]
        except Exception:
            out["home_status"] = 0
        dom = _domain(home)
        for u in (f"{home}/status", f"https://status.{dom}", f"https://{dom.split('.')[0]}.statuspage.io"):
            inc = _statuspage_incidents(u)
            if inc is not None:
                cutoff = time.time() - 90 * 86400
                n = 0
                for i in inc:
                    try:
                        if time.mktime(time.strptime(i.get("created_at", "")[:19], "%Y-%m-%dT%H:%M:%S")) >= cutoff:
                            n += 1
                    except Exception:
                        pass
                out["incidents_90d"] = n
                break
    return out


def check_watches():
    now = time.time()
    for w in db.q("SELECT * FROM watches WHERE last_check < ?", (now - INTERVAL,)):
        run_id = w["run_id"]
        snap = json.loads(w["snapshot"] or "{}")
        new_snap = {}
        for cand in db.q("SELECT * FROM candidates WHERE run_id=?", (run_id,)):
            cur = _probe(cand)
            prev = snap.get(str(cand["id"]))
            if prev:
                if prev.get("home_status") and cur["home_status"] and cur["home_status"] != prev["home_status"]:
                    _alert(w["id"], run_id, "home", f"{cand['name']}: homepage status {prev['home_status']} → {cur['home_status']}")
                if prev.get("home_hash") and cur["home_hash"] and cur["home_hash"] != prev["home_hash"]:
                    _alert(w["id"], run_id, "home", f"{cand['name']}: homepage content changed (possible pricing/feature update)")
                if prev.get("incidents_90d") is not None and cur["incidents_90d"] is not None and cur["incidents_90d"] > prev["incidents_90d"]:
                    _alert(w["id"], run_id, "status_page", f"{cand['name']}: {cur['incidents_90d']-prev['incidents_90d']} new incidents (90d total {cur['incidents_90d']})")
            new_snap[str(cand["id"])] = cur
        with db.conn() as c:
            c.execute("UPDATE watches SET snapshot=?, last_check=? WHERE id=?", (json.dumps(new_snap), now, w["id"]))
        if snap:
            trace(run_id, "monitor", "Watch check complete", actor="check")


def _alert(watch_id, run_id, check, summary):
    db.ins("INSERT INTO alerts(watch_id,run_id,ts,check_name,summary) VALUES(?,?,?,?,?)", (watch_id, run_id, time.time(), check, summary))
    trace(run_id, "monitor", f"ALERT: {summary}", actor="check")


def scheduler():
    def loop():
        while True:
            try:
                check_watches()
            except Exception:
                pass
            time.sleep(min(INTERVAL, 60))
    threading.Thread(target=loop, daemon=True).start()
