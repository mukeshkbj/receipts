import json
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from . import db, models, monitor, pipeline

app = FastAPI(title="Receipts")
db.init()
monitor.scheduler()

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class RunIn(BaseModel):
    brief: str
    auto: bool = False


class ReqsIn(BaseModel):
    requirements: dict


class ReplyIn(BaseModel):
    candidate_id: int
    text: str


@app.post("/api/runs")
def create_run(inp: RunIn):
    brief = inp.brief.strip()
    if len(brief) < 10:
        return {"error": "brief too short"}
    return {"run_id": pipeline.start(brief, auto=inp.auto)}


@app.get("/api/runs")
def list_runs():
    return db.q("SELECT id,brief,category,status,created_at FROM runs ORDER BY created_at DESC LIMIT 20")


@app.get("/api/runs/{run_id}")
def get_run(run_id: str, since: int = 0):
    run = db.one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        return {"error": "not found"}
    trace = db.q("SELECT id,ts,stage,event,detail,actor FROM trace WHERE run_id=? AND id>? ORDER BY id", (run_id, since))
    return {"run": run, "trace": trace}


@app.post("/api/runs/{run_id}/requirements")
def set_requirements(run_id: str, inp: ReqsIn):
    run = db.one("SELECT status FROM runs WHERE id=?", (run_id,))
    if not run:
        return {"error": "not found"}
    if run["status"] != "awaiting_requirements":
        return {"error": f"run is {run['status']}"}
    pipeline.resume(run_id, inp.requirements)
    return {"ok": True}


@app.post("/api/runs/{run_id}/replies")
def ingest_reply(run_id: str, inp: ReplyIn):
    if not inp.text.strip():
        return {"error": "empty reply"}
    n = pipeline.ingest_reply(run_id, inp.candidate_id, inp.text)
    return {"updated": n}


@app.post("/api/runs/{run_id}/watch")
def watch(run_id: str):
    wid = monitor.add_watch(run_id)
    return {"watch_id": wid, "interval_sec": monitor.INTERVAL}


@app.get("/api/runs/{run_id}/usage")
def usage(run_id: str):
    rows = db.q(
        "SELECT model, purpose, COUNT(*) n, SUM(in_tok) i, SUM(out_tok) o FROM usage WHERE run_id=? GROUP BY model, purpose",
        (run_id,),
    )
    by_model, tot_in, tot_out, cost = {}, 0, 0, 0.0
    for r in rows:
        m = by_model.setdefault(r["model"], {"calls": 0, "in_tok": 0, "out_tok": 0})
        m["calls"] += r["n"]
        m["in_tok"] += r["i"] or 0
        m["out_tok"] += r["o"] or 0
        tot_in += r["i"] or 0
        tot_out += r["o"] or 0
        cost += models.cost_usd(r["model"], r["i"] or 0, r["o"] or 0)
    return {"by_model": by_model, "total_in": tot_in, "total_out": tot_out, "cost_usd": round(cost, 4)}


@app.get("/api/runs/{run_id}/export", response_class=PlainTextResponse)
def export(run_id: str):
    d = get_result(run_id)
    if "error" in d:
        return "not found"
    b, req = d["brief"], d["requirements"]
    lines = [f"# Decision brief — {d['run']['brief'][:80]}", ""]
    lines.append(f"**Recommendation: {b.get('recommendation','')}**")
    if b.get("summary"):
        lines += ["", b["summary"]]
    for w in b.get("watch_outs", []):
        lines.append(f"- ⚠ {w}")
    lines.append("\n## Scorecard\n")
    for c in d["candidates"]:
        lines.append(f"### {c['name']} — {c['weighted']}/5")
        vc = {}
        for cl in c["claims"]:
            vc[cl.get("verdict") or "unverifiable"] = vc.get(cl.get("verdict") or "unverifiable", 0) + 1
        lines.append(f"verdicts: {vc}")
        for cl in c["claims"]:
            if cl.get("verdict") in ("contradicted", "unverifiable"):
                lines.append(f"- [{cl['verdict'].upper()}] {cl['text']}")
        lines.append("")
    return "\n".join(lines)


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
    watch = db.one("SELECT id, last_check FROM watches WHERE run_id=?", (run_id,))
    alerts = db.q("SELECT * FROM alerts WHERE run_id=? ORDER BY ts DESC LIMIT 20", (run_id,))
    return {
        "run": run,
        "requirements": json.loads(run["requirements"] or "{}"),
        "brief": json.loads(run["brief_json"] or "{}"),
        "candidates": cands,
        "outreach": outreach,
        "watch": watch,
        "alerts": alerts,
        "usage": usage(run_id),
    }


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))
