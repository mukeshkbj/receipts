import json
import os
import threading
import time
import uuid

from . import db, models
from .checks import CHECKS
from .util import trace, _cut

MAX_CLAIMS_PER_CANDIDATE = 14
MAX_CANDIDATES = 5


def tavily():
    from tavily import TavilyClient

    return TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


# ---------- stages ----------


def elicit(run_id, brief):
    """brief -> weighted requirements model (Ultra)."""
    trace(run_id, "elicit", "Parsing brief into a weighted requirements model")
    req = models.json_chat(
        "reason",
        "You are a procurement analyst. Turn a purchase brief into a structured requirements model.",
        f"""Brief: {brief}

Return JSON:
{{
  "category": "<short product category, e.g. 'managed vector database'>",
  "summary": "<one sentence restating the need>",
  "requirements": [
    {{"key": "<snake_key>", "label": "<human label>", "weight": <1-10>, "must_have": <true|false>, "detail": "<what good looks like>"}}
  ]
}}
4-8 requirements. Weights must sum to 10 roughly. Include budget if given.""",
        max_tokens=2048,
    )
    db.touch_run(run_id, requirements=json.dumps(req), category=req.get("category", ""))
    trace(run_id, "elicit", f"{len(req.get('requirements', []))} requirements", json.dumps(req.get("requirements", []))[:2000])
    return req


def discover(run_id, req):
    """Tavily candidate discovery -> dedupe -> candidate rows (Nano)."""
    category = req.get("category", "")
    trace(run_id, "discover", f"Searching for {category} vendors")
    queries = [
        f"best {category} tools comparison 2026",
        f"top {category} vendors alternatives",
        f"{category} pricing comparison",
    ]
    hits = []
    for q_ in queries:
        try:
            res = tavily().search(q_, max_results=6, search_depth="basic")
            hits += [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": _cut(r.get("content", ""), 600)} for r in res.get("results", [])]
        except Exception as e:
            trace(run_id, "discover", "search failed", str(e))
    trace(run_id, "discover", f"{len(hits)} raw hits, deduplicating")
    cands = models.json_chat(
        "extract",
        "You extract vendor candidates from search results. Only real purchasable products, not articles or resellers.",
        f"""Category: {category}
Search hits:
{json.dumps(hits, indent=1)[:20000]}

Return JSON: {{"candidates": [{{"name": "<product>", "vendor": "<company>", "homepage": "<https://...>", "notes": "<one-line positioning>"}}]}}
Pick the {MAX_CANDIDATES} most credible, distinct options. Prefer official homepages for the URL.""",
    )
    out = []
    for c in (cands.get("candidates") or [])[:MAX_CANDIDATES]:
        cid = db.ins(
            "INSERT INTO candidates(run_id,name,vendor,homepage,category,notes) VALUES(?,?,?,?,?,?)",
            (run_id, c.get("name", "?"), c.get("vendor", ""), c.get("homepage", ""), category, c.get("notes", "")),
        )
        out.append({"id": cid, **c})
    trace(run_id, "discover", f"{len(out)} candidates", ", ".join(c.get("name", "?") for c in out))
    return out


_LIKELY_PAGES = ["pricing", "docs", "security", "trust", "legal/sla", "sla"]


def ingest(run_id, cand):
    """Extract marketing claims from vendor pages (Tavily extract -> Nano)."""
    home = (cand.get("homepage") or "").rstrip("/")
    urls = [home] + [f"{home}/{p}" for p in _LIKELY_PAGES]
    pages = []
    try:
        res = tavily().extract(urls=urls, extract_depth="basic")
        for r in res.get("results", []):
            pages.append({"url": r.get("url", ""), "content": _cut(r.get("raw_content", ""), 9000)})
        for f in res.get("failed_results", []):
            pass
    except Exception as e:
        trace(run_id, "ingest", f"extract failed for {cand.get('name')}", str(e))
    # fall back to search snippets if extraction returned nothing
    if not pages:
        try:
            res = tavily().search(f"{cand.get('name')} {cand.get('vendor')} features pricing SLA", max_results=4)
            pages = [{"url": r.get("url", ""), "content": _cut(r.get("content", ""), 1500)} for r in res.get("results", [])]
        except Exception:
            pass
    blob = "\n\n".join(f"URL: {p['url']}\n{p['content']}" for p in pages)
    claims = models.json_chat(
        "extract",
        "You extract verifiable marketing claims from vendor web pages. A claim is a specific checkable assertion: numbers, certifications, SLAs, limits, prices, feature assertions. Skip vague adjectives.",
        f"""Vendor: {cand.get('name')} ({cand.get('vendor')})
Pages:
{blob[:30000]}

Return JSON: {{"claims": [{{"type": "spec|price|sla|security|viability|sentiment", "text": "<the claim, self-contained>", "source_url": "<page url>"}}]}}
Up to {MAX_CLAIMS_PER_CANDIDATE} claims, most checkable first.""",
        max_tokens=3000,
    )
    n = 0
    for cl in (claims.get("claims") or [])[:MAX_CLAIMS_PER_CANDIDATE]:
        db.ins(
            "INSERT INTO claims(run_id,candidate_id,type,text,source_url) VALUES(?,?,?,?,?)",
            (run_id, cand["id"], cl.get("type", "spec"), cl.get("text", "")[:500], cl.get("source_url", "")),
        )
        n += 1
    trace(run_id, "ingest", f"{cand.get('name')}: {n} claims extracted")
    return n


def plan_checks(run_id, cand, requirements):
    """Ultra picks which checks apply, via real tool calling; we execute them."""
    claims = db.q("SELECT type, COUNT(*) n FROM claims WHERE candidate_id=? GROUP BY type", (cand["id"],))
    tools = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
        for name, meta in CHECKS.items()
    ]
    prompt = (
        f"Candidate: {cand.get('name')} ({cand.get('vendor')}) — category: {cand.get('category')}\n"
        f"Homepage: {cand.get('homepage')}\n"
        f"Claim types found: {json.dumps(claims)}\n"
        f"Buyer requirements: {json.dumps(requirements.get('requirements', []))}\n\n"
        "Call every check that can verify or falsify claims for this candidate. Skip checks that cannot apply (e.g. live_benchmark needs runnable software, spec_independent is for hardware)."
    )
    ran = []
    try:
        msg = models.chat(
            "reason",
            [
                {"role": "system", "content": "You are a verification planner. Select checks by calling them as tools. Call each applicable check exactly once."},
                {"role": "user", "content": prompt},
            ],
            tools=tools,
            max_tokens=1024,
        )
        calls = msg.tool_calls or []
        for tc in calls:
            name = tc.function.name
            if name in CHECKS and name not in ran:
                ran.append(name)
    except Exception as e:
        trace(run_id, "plan", f"tool planning failed, falling back ({e})")
    if not ran:
        ran = ["doc_audit", "status_history", "reputation"]
    trace(run_id, "plan", f"{cand.get('name')}: checks selected", ", ".join(ran))
    return ran


def assign_verdicts(run_id):
    """Evidence -> verdict per claim. Contradicted > measured > cited > unverifiable."""
    claims = db.q(
        """SELECT c.*, (SELECT json_group_array(json_object('kind',e.kind,'supports',e.supports,'excerpt',e.excerpt,'measured_value',e.measured_value))
             FROM evidence e WHERE e.claim_id=c.id) ev
           FROM claims c WHERE c.run_id=?""",
        (run_id,),
    )
    n = {"measured": 0, "cited": 0, "contradicted": 0, "unverifiable": 0}
    for cl in claims:
        ev = json.loads(cl["ev"] or "[]")
        contra = any(e.get("supports") == -1 for e in ev)
        meas = any(e.get("kind") in ("measurement", "probe") and e.get("supports") != -1 for e in ev)
        cite = any(e.get("supports") == 1 for e in ev)
        if contra:
            v = "contradicted"
        elif meas:
            v = "measured"
        elif cite:
            v = "cited"
        else:
            v = "unverifiable"
        n[v] += 1
        db.ins("INSERT INTO verdicts(run_id,claim_id,verdict,confidence) VALUES(?,?,?,?)", (run_id, cl["id"], v, 0.8 if v != "unverifiable" else 0.4))
    trace(run_id, "verdicts", "Verdicts assigned", json.dumps(n))


def rationale_pass(run_id):
    """One Ultra call: rationales for every contradicted/unverifiable claim."""
    rows = db.q(
        """SELECT v.id vid, c.text, v.verdict,
                  (SELECT json_group_array(e.excerpt) FROM evidence e WHERE e.claim_id=c.id) ev
           FROM verdicts v JOIN claims c ON c.id=v.claim_id
           WHERE v.run_id=? AND v.verdict IN ('contradicted','unverifiable')""",
        (run_id,),
    )
    if not rows:
        return
    try:
        rs = models.json_chat(
            "reason",
            "Write one-sentence rationales for claim verdicts.",
            f"Claims and their evidence:\n{json.dumps(rows, indent=1)[:16000]}\n"
            'Return JSON: {"rationales": [{"vid": <id>, "rationale": "<one sentence>"}]}',
        )
        for r in rs.get("rationales", []):
            with db.conn() as c:
                c.execute("UPDATE verdicts SET rationale=? WHERE id=?", (r.get("rationale", "")[:500], r.get("vid")))
    except Exception as e:
        trace(run_id, "verdicts", "rationale pass failed", str(e))


def score(run_id, requirements, cands):
    """Weighted scorecard via Ultra."""
    summary = []
    for cand in cands:
        rows = db.q(
            """SELECT c.type, c.text, v.verdict FROM claims c
                 JOIN verdicts v ON v.claim_id=c.id
                 WHERE c.candidate_id=? AND c.run_id=?""",
            (cand["id"], run_id),
        )
        summary.append({"candidate_id": cand["id"], "name": cand["name"], "claims": rows})
    out = models.json_chat(
        "reason",
        "You are a procurement analyst scoring candidates against a requirements model. Contradicted claims hurt; measured claims earn trust; unverifiable claims earn neither.",
        f"""Requirements: {json.dumps(requirements.get("requirements", []))}
Candidates with verdicted claims:
{json.dumps(summary, indent=1)[:24000]}

Return JSON: {{"scores": [{{"candidate_id": <id>, "req_key": "<requirement key>", "score": <0-5>, "rationale": "<one sentence>"}}]}}
Score every candidate on every requirement.""",
        max_tokens=6000,
    )
    n = 0
    weights = {r["key"]: r.get("weight", 1) for r in requirements.get("requirements", [])}
    for s in out.get("scores", []):
        if s.get("req_key") in weights:
            db.ins(
                "INSERT INTO scores(run_id,candidate_id,req_key,score,weight,rationale) VALUES(?,?,?,?,?,?)",
                (run_id, s.get("candidate_id"), s["req_key"], float(s.get("score", 0)), weights[s["req_key"]], s.get("rationale", "")[:300]),
            )
            n += 1
    trace(run_id, "score", f"{n} score cells written")


def negotiate(run_id, cands, requirements):
    """Outreach drafts for the top 2 weighted candidates (Ultra)."""
    totals = {}
    for row in db.q("SELECT candidate_id, SUM(score*weight) t FROM scores WHERE run_id=? GROUP BY candidate_id", (run_id,)):
        totals[row["candidate_id"]] = row["t"]
    top = sorted(totals, key=totals.get, reverse=True)[:2]
    for cid in top:
        name = next((c["name"] for c in cands if c["id"] == cid), "?")
        weak = db.q(
            """SELECT c.text, v.verdict FROM claims c JOIN verdicts v ON v.claim_id=c.id
                 WHERE c.candidate_id=? AND v.verdict IN ('contradicted','unverifiable') LIMIT 8""",
            (cid,),
        )
        try:
            d = models.json_chat(
                "reason",
                "Draft a concise vendor-outreach email. Use the weak claims as pointed, specific questions — polite, professional, no fluff.",
                f"Vendor: {name}\nRequirements: {json.dumps(requirements.get('requirements', []))[:4000]}\nUnverified/contradicted claims:\n{json.dumps(weak, indent=1)}\n"
                'Return JSON: {"subject": "...", "body": "...", "questions": ["<pointed question>", ...]}',
            )
            db.ins(
                "INSERT INTO outreach(run_id,candidate_id,subject,body,questions) VALUES(?,?,?,?,?)",
                (run_id, cid, d.get("subject", ""), d.get("body", ""), json.dumps(d.get("questions", []))),
            )
            trace(run_id, "negotiate", f"Outreach drafted for {name}")
        except Exception as e:
            trace(run_id, "negotiate", f"draft failed for {name}", str(e))


def brief(run_id, requirements, cands):
    """Assemble the decision brief JSON."""
    totals = {}
    for row in db.q(
        "SELECT candidate_id, SUM(score*weight) t, SUM(weight) w FROM scores WHERE run_id=? GROUP BY candidate_id", (run_id,)
    ):
        totals[row["candidate_id"]] = (row["t"], row["w"] or 1)
    ranked = sorted(totals.items(), key=lambda kv: kv[1][0] / kv[1][1], reverse=True)
    per = []
    for cid, (t, w) in ranked:
        name = next((c["name"] for c in cands if c["id"] == cid), "?")
        vc = db.q(
            """SELECT v.verdict, COUNT(*) n FROM verdicts v JOIN claims c ON c.id=v.claim_id
                 WHERE c.candidate_id=? GROUP BY v.verdict""",
            (cid,),
        )
        per.append({"candidate_id": cid, "name": name, "weighted": round(t / w, 2), "verdicts": {r["verdict"]: r["n"] for r in vc}})
    winner = per[0]["name"] if per else None
    try:
        b = models.json_chat(
            "reason",
            "Write a decision brief. Direct, evidence-first, no filler.",
            f"Requirements: {json.dumps(requirements.get('requirements', []))}\nRanked candidates with verdict counts:\n{json.dumps(per, indent=1)}\n"
            'Return JSON: {"recommendation": "<name>", "summary": "<3 sentences max>", "watch_outs": ["<top risks>"]}',
        )
    except Exception:
        b = {"recommendation": winner or "", "summary": "", "watch_outs": []}
    b["ranked"] = per
    db.touch_run(run_id, brief_json=json.dumps(b))
    trace(run_id, "brief", f"Recommendation: {b.get('recommendation')}")
    return b


# ---------- orchestrator ----------


def run_pipeline(run_id, brief_text):
    try:
        requirements = elicit(run_id, brief_text)
        cands = discover(run_id, requirements)
        if not cands:
            raise RuntimeError("no candidates found")
        ctx = {"run_id": run_id, "requirements": requirements, "tavily": tavily()}
        for cand in cands:
            try:
                ingest(run_id, cand)
            except Exception as e:
                trace(run_id, "ingest", f"failed for {cand.get('name')}", str(e))
        for cand in cands:
            for name in plan_checks(run_id, cand, requirements):
                try:
                    trace(run_id, name, f"{cand['name']}: running")
                    CHECKS[name]["fn"](ctx, cand)
                except Exception as e:
                    trace(run_id, name, f"{cand.get('name')}: check failed", str(e))
        assign_verdicts(run_id)
        rationale_pass(run_id)
        score(run_id, requirements, cands)
        negotiate(run_id, cands, requirements)
        brief(run_id, requirements, cands)
        db.touch_run(run_id, status="done")
        trace(run_id, "done", "Run complete")
    except Exception as e:
        db.touch_run(run_id, status="error", error=str(e)[:2000])
        trace(run_id, "error", str(e)[:1000])


def start(brief_text):
    run_id = uuid.uuid4().hex[:12]
    db.ins(
        "INSERT INTO runs(id,brief,status,created_at,updated_at) VALUES(?,?,?,?,?)",
        (run_id, brief_text, "running", time.time(), time.time()),
    )
    t = threading.Thread(target=run_pipeline, args=(run_id, brief_text), daemon=True)
    t.start()
    return run_id
