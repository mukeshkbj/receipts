import json
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import db, pipeline

app = FastAPI(title="Receipts")
db.init()

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class RunIn(BaseModel):
    brief: str


@app.post("/api/runs")
def create_run(inp: RunIn):
    brief = inp.brief.strip()
    if len(brief) < 10:
        return {"error": "brief too short"}
    return {"run_id": pipeline.start(brief)}


@app.get("/api/runs")
def list_runs():
    return db.q("SELECT id,brief,category,status,created_at FROM runs ORDER BY created_at DESC LIMIT 20")


@app.get("/api/runs/{run_id}")
def get_run(run_id: str, since: int = 0):
    run = db.one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        return {"error": "not found"}
    trace = db.q("SELECT id,ts,stage,event,detail FROM trace WHERE run_id=? AND id>? ORDER BY id", (run_id, since))
    return {"run": run, "trace": trace}


@app.get("/api/runs/{run_id}/result")
def get_result(run_id: str):
    run = db.one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        return {"error": "not found"}
    cands = db.q("SELECT * FROM candidates WHERE run_id=?", (run_id,))
    for c in cands:
        c["claims"] = db.q(
            """SELECT c.*, v.verdict, v.confidence, v.rationale FROM claims c
                 LEFT JOIN verdicts v ON v.claim_id=c.id
                 WHERE c.candidate_id=? ORDER BY c.id""",
            (c["id"],),
        )
        for cl in c["claims"]:
            cl["evidence"] = db.q("SELECT * FROM evidence WHERE claim_id=?", (cl["id"],))
        c["scores"] = db.q("SELECT * FROM scores WHERE candidate_id=?", (c["id"],))
        t = db.one("SELECT SUM(score*weight) t, SUM(weight) w FROM scores WHERE candidate_id=?", (c["id"],))
        c["weighted"] = round((t["t"] or 0) / (t["w"] or 1), 2)
    outreach = db.q("SELECT * FROM outreach WHERE run_id=?", (run_id,))
    return {
        "run": run,
        "requirements": json.loads(run["requirements"] or "{}"),
        "brief": json.loads(run["brief_json"] or "{}"),
        "candidates": cands,
        "outreach": outreach,
    }


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))
