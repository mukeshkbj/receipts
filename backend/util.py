import time

from . import db


def trace(run_id, stage, event, detail="", actor="system"):
    db.ins(
        "INSERT INTO trace(run_id,ts,stage,event,detail,actor) VALUES(?,?,?,?,?,?)",
        (run_id, time.time(), stage, event, str(detail)[:4000], actor),
    )


def _cut(s, n=12000):
    return s[:n] if isinstance(s, str) else ""
