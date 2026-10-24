#!/usr/bin/env python3
"""CLI runner: python run.py "we need a managed vector DB under $500/mo, 10M vectors, p99<50ms" """
import sys
import time

import backend  # noqa: F401  (loads .env)
from backend import db, pipeline


def main():
    brief_text = " ".join(sys.argv[1:]) or "we need a managed vector database under $500/mo for ~10M vectors, p99 query latency under 50ms"
    db.init()
    run_id = pipeline.start(brief_text, auto=True)
    print(f"run {run_id}")
    seen = 0
    while True:
        rows = db.q("SELECT id,stage,event,detail FROM trace WHERE run_id=? AND id>? ORDER BY id", (run_id, seen))
        for r in rows:
            print(f"  [{r['stage']}] {r['event']}" + (f" — {r['detail'][:140]}" if r["detail"] else ""))
            seen = r["id"]
        run = db.one("SELECT status,error FROM runs WHERE id=?", (run_id,))
        if run["status"] != "running":
            print(f"status: {run['status']}" + (f" error: {run['error']}" if run.get("error") else ""))
            break
        time.sleep(2)


if __name__ == "__main__":
    main()
