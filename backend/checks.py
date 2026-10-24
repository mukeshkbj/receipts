import json
import os
import re
import subprocess
import time
import urllib.parse

import httpx

from . import db, models
from .util import trace, _cut


def _claims(cand_id, types=None):
    rows = db.q("SELECT * FROM claims WHERE candidate_id=?", (cand_id,))
    return [r for r in rows if types is None or r["type"] in types]


def _add_ev(run_id, claim_id, check, kind, url="", excerpt="", measured="", supports=0):
    db.ins(
        "INSERT INTO evidence(run_id,claim_id,check_name,kind,url,excerpt,measured_value,supports) VALUES(?,?,?,?,?,?,?,?)",
        (run_id, claim_id, check, kind, url, _cut(excerpt, 1500), str(measured)[:500], supports),
    )


def _add_claim(run_id, cand_id, type_, text, source="observed"):
    return db.ins(
        "INSERT INTO claims(run_id,candidate_id,type,text,source_url) VALUES(?,?,?,?,?)",
        (run_id, cand_id, type_, text[:500], source),
    )


def _domain(home):
    try:
        return urllib.parse.urlparse(home).netloc.replace("www.", "")
    except Exception:
        return ""


def _extract_pages(ctx, urls):
    pages = []
    try:
        res = ctx["tavily"].extract(urls=urls, extract_depth="basic")
        for r in res.get("results", []):
            pages.append({"url": r.get("url", ""), "content": _cut(r.get("raw_content", ""), 8000)})
    except Exception:
        pass
    return pages


# ---------- doc_audit ----------

_DOC_PATHS = ["pricing", "security", "trust", "legal", "legal/sla", "sla", "dpa", "terms"]


def doc_audit(ctx, cand):
    """Cross-check security/price/sla claims against the vendor's own legal+trust pages."""
    run_id, home = ctx["run_id"], (cand.get("homepage") or "").rstrip("/")
    urls = [f"{home}/{p}" for p in _DOC_PATHS]
    pages = _extract_pages(ctx, urls)
    if not pages:
        try:
            res = ctx["tavily"].search(f"{cand['name']} SOC2 SLA terms pricing", max_results=4)
            pages = [{"url": r.get("url", ""), "content": _cut(r.get("content", ""), 2000)} for r in res.get("results", [])]
        except Exception:
            pass
    if not pages:
        trace(run_id, "doc_audit", f"{cand['name']}: no doc pages found")
        return
    blob = "\n\n".join(f"URL: {p['url']}\n{p['content']}" for p in pages)[:28000]
    targets = _claims(cand["id"], {"security", "price", "sla"})
    if not targets:
        trace(run_id, "doc_audit", f"{cand['name']}: no security/price/sla claims to audit")
        return
    verdicts = models.json_chat(
        "extract",
        "You audit marketing claims against the vendor's own legal/trust/pricing documents. "
        "For each claim decide: 'supports' (document confirms it), 'contradicts' (document affirmatively conflicts "
        "— for certifications, absence from the trust/security page that must list them counts as contradict), "
        "or 'absent' (not mentioned either way).",
        f"Vendor: {cand['name']}\nDocuments:\n{blob}\n\nClaims:\n{json.dumps([{'id': c['id'], 'text': c['text']} for c in targets], indent=1)}\n"
        'Return JSON: {"results": [{"id": <claim id>, "verdict": "supports|contradicts|absent", "evidence": "<short quote or observation>", "url": "<doc url>"}]}',
        max_tokens=4000,
    )
    n = 0
    sup = {"supports": 1, "contradicts": -1, "absent": 0}
    if isinstance(verdicts, list):
        verdicts = {"results": verdicts}
    for r in verdicts.get("results", []):
        if r.get("id") in {c["id"] for c in targets}:
            _add_ev(run_id, r["id"], "doc_audit", "doc", r.get("url", ""), r.get("evidence", ""), "", sup.get(r.get("verdict"), 0))
            n += 1
    trace(run_id, "doc_audit", f"{cand['name']}: {n} claims audited against {len(pages)} doc pages")


# ---------- status_history ----------


def _statuspage_incidents(status_url):
    base = status_url.rstrip("/")
    try:
        r = httpx.get(f"{base}/api/v2/incidents.json", params={"per_page": 100}, timeout=15, follow_redirects=True)
        if r.status_code == 200 and "incidents" in r.text[:2000]:
            return r.json().get("incidents", [])
    except Exception:
        pass
    return None


def status_history(ctx, cand):
    """Reconstruct real reliability from the public status page vs marketed uptime."""
    run_id = ctx["run_id"]
    home = (cand.get("homepage") or "").rstrip("/")
    dom = _domain(home)
    guesses = [f"{home}/status", f"https://status.{dom}", f"https://{dom.split('.')[0]}.statuspage.io"]
    incidents, status_url = None, None
    for u in guesses:
        incidents = _statuspage_incidents(u)
        if incidents is not None:
            status_url = u
            break
    now = time.time()
    if incidents is None:
        try:
            res = ctx["tavily"].search(f"{cand['name']} outage incident downtime status", max_results=5)
            txt = "\n".join(f"{r.get('title','')}: {_cut(r.get('content',''),400)}" for r in res.get("results", []))
            est = models.json_chat(
                "extract",
                "Summarize the vendor's recent outage history from search results.",
                f"Vendor: {cand['name']}\n{txt}\n"
                'Return JSON: {"incidents_90d": <int or null>, "summary": "<one sentence>", "major": "<worst incident or null>"}',
            )
            est = est if isinstance(est, dict) else {}
            info = f"~{est.get('incidents_90d')} incidents/90d. {est.get('summary','')} {est.get('major') or ''}"
        except Exception as e:
            trace(run_id, "status_history", f"{cand['name']}: failed", str(e))
            return
        kind, measured = "citation", {"source": "search", "incidents_90d": est.get("incidents_90d")}
        url = ""
    else:
        cutoff = now - 90 * 86400
        recent, minutes = [], 0.0
        for inc in incidents:
            try:
                created = time.mktime(time.strptime(inc.get("created_at", "")[:19], "%Y-%m-%dT%H:%M:%S"))
                if created < cutoff:
                    continue
                recent.append(inc)
                dur = inc.get("duration") or 0
                if not dur:
                    ups = inc.get("incident_updates", [])
                    if len(ups) >= 2:
                        try:
                            t0 = time.mktime(time.strptime(ups[-1]["created_at"][:19], "%Y-%m-%dT%H:%M:%S"))
                            t1 = time.mktime(time.strptime(ups[0]["created_at"][:19], "%Y-%m-%dT%H:%M:%S"))
                            dur = max(0, (t1 - t0) / 60)
                        except Exception:
                            dur = 0
                minutes += dur or 15  # assume >=15min impact per incident when no duration
            except Exception:
                continue
        kind = "status_page"
        measured = {"incidents_90d": len(recent), "est_downtime_min": round(minutes), "observed_uptime_pct": round(100 - minutes / (90 * 24 * 60) * 100, 3)}
        info = f"{len(recent)} incidents/90d, ~{round(minutes)}min est. downtime (~{measured['observed_uptime_pct']}% observed)"
        url = status_url
    sla_claims = [c for c in _claims(cand["id"], {"sla", "spec"}) if re.search(r"9\d(\.\d+)?\s*%|uptime|availab|reliab", c["text"], re.I)]
    if not sla_claims:
        cid = _add_claim(run_id, cand["id"], "sla", f"Observed reliability: {info}", url or "status page")
        _add_ev(run_id, cid, "status_history", kind, url, info, json.dumps(measured), 1)
        trace(run_id, "status_history", f"{cand['name']}: {info}")
        return
    for c in sla_claims:
        m = re.search(r"(9\d(?:\.\d+)?)\s*%", c["text"])
        sup = 0
        if m and kind == "status_page":
            allowed = (100 - float(m.group(1))) / 100 * 90 * 24 * 60
            sup = -1 if measured["est_downtime_min"] > allowed * 1.5 else 1
        elif m:
            sup = 0
        _add_ev(run_id, c["id"], "status_history", kind, url, info, json.dumps(measured), sup)
    trace(run_id, "status_history", f"{cand['name']}: {info} vs {len(sla_claims)} uptime claims")


# ---------- reputation ----------


def reputation(ctx, cand):
    """Community sentiment + complaint patterns + vendor viability signals."""
    run_id = ctx["run_id"]
    queries = [
        f"{cand['name']} {cand.get('vendor','')} review complaints reddit",
        f"{cand['name']} pricing increase renewal support problem",
        f"{cand.get('vendor') or cand['name']} layoffs funding acquired news",
    ]
    blob = ""
    for q_ in queries:
        try:
            res = ctx["tavily"].search(q_, max_results=4)
            blob += "\n".join(f"{r.get('title','')} ({r.get('url','')}): {_cut(r.get('content',''),500)}" for r in res.get("results", [])) + "\n\n"
        except Exception:
            pass
    if not blob.strip():
        trace(run_id, "reputation", f"{cand['name']}: no results")
        return
    out = models.json_chat(
        "extract",
        "Summarize community sentiment about a product. Report complaint *patterns* (recurring themes), not one-off grumbling.",
        f"Product: {cand['name']} ({cand.get('vendor','')})\nResults:\n{blob[:24000]}\n"
        'Return JSON: {"sentiment": <-1.0..1.0>, "complaints": ["<pattern>"], "viability": "<funding/layoffs/acquisition signal, one sentence>", "sources": ["<url>"]}',
    )
    out = out if isinstance(out, dict) else {"sentiment": 0}
    sent = out.get("sentiment", 0) or 0
    sup = 1 if sent > 0.15 else (-1 if sent < -0.15 else 0)
    summary = f"sentiment {sent:+.2f}; complaints: {'; '.join(out.get('complaints', [])[:4]) or 'none major'}; viability: {out.get('viability','')}"
    src = (out.get("sources") or [""])[0]
    targets = _claims(cand["id"], {"sentiment", "viability"})
    if not targets:
        cid = _add_claim(run_id, cand["id"], "sentiment", "Users report a positive overall experience", "community")
        targets = [{"id": cid, "type": "sentiment"}]
        cid2 = _add_claim(run_id, cand["id"], "viability", "Vendor appears stable and viable", "community")
        targets.append({"id": cid2, "type": "viability"})
    for t in targets:
        s = sup if t["type"] == "sentiment" else (1 if "layoff" not in summary.lower() else -1)
        _add_ev(run_id, t["id"], "reputation", "sentiment", src, summary, "", s)
    trace(run_id, "reputation", f"{cand['name']}: sentiment {sent:+.2f}, {len(out.get('complaints', []))} complaint patterns")


# ---------- live_benchmark ----------


def _bench_targets():
    raw = os.environ.get("BENCH_TARGETS", "")
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def live_benchmark(ctx, cand):
    """Run the prebuilt benchmark harness against a configured candidate target."""
    run_id = ctx["run_id"]
    targets = _bench_targets()
    key = next((k for k in targets if k.lower() in (cand.get("name") or "").lower() or k.lower() in (cand.get("vendor") or "").lower()), None)
    if not key:
        trace(run_id, "live_benchmark", f"{cand['name']}: no bench target configured (BENCH_TARGETS)")
        return
    t = targets[key]
    trace(run_id, "live_benchmark", f"{cand['name']}: benchmarking via {t.get('type')} target")
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bench", "vdbench.py")
    try:
        env = dict(os.environ, BENCH_URL=t["url"], BENCH_KEY=t.get("api_key", ""))
        proc = subprocess.run(
            ["python3", script, "--n", str(t.get("n", 10000)), "--dim", str(t.get("dim", 128))],
            capture_output=True, text=True, timeout=300, env=env,
        )
        m = None
        for line in proc.stdout.splitlines()[::-1]:
            line = line.strip()
            if line.startswith("{") and "p99" in line:
                m = json.loads(line)
                break
        if m is None:
            trace(run_id, "live_benchmark", f"{cand['name']}: bench failed", proc.stderr[-500:])
            return
    except Exception as e:
        trace(run_id, "live_benchmark", f"{cand['name']}: bench error", str(e))
        return
    info = f"measured: p50={m.get('p50_ms')}ms p99={m.get('p99_ms')}ms qps={m.get('qps')} n={m.get('n')}"
    spec_claims = [c for c in _claims(cand["id"], {"spec", "sla"}) if re.search(r"latenc|p\d{2}|ms\b|qps|throughput|speed|fast", c["text"], re.I)]
    if not spec_claims:
        cid = _add_claim(run_id, cand["id"], "spec", f"Observed query latency under test workload: {info}", "benchmark")
        _add_ev(run_id, cid, "live_benchmark", "measurement", "", info, json.dumps(m), 1)
        trace(run_id, "live_benchmark", f"{cand['name']}: {info}")
        return
    for c in spec_claims:
        sup = 1
        mm = re.search(r"<\s*(\d+)\s*ms|p99[^\d]{0,20}(\d+)\s*ms|(\d+)\s*ms", c["text"], re.I)
        if mm:
            claimed = next((float(g) for g in mm.groups() if g), None)
            if claimed and m.get("p99_ms") and m["p99_ms"] > claimed * 1.2:
                sup = -1
        _add_ev(run_id, c["id"], "live_benchmark", "measurement", "", info, json.dumps(m), sup)
    trace(run_id, "live_benchmark", f"{cand['name']}: {info} applied to {len(spec_claims)} claims")


# ---------- trial_probe ----------


def trial_probe(ctx, cand):
    """Probe public surface: page latency, free-tier existence, docs API availability."""
    run_id = ctx["run_id"]
    home = (cand.get("homepage") or "").rstrip("/")
    if not home:
        return
    out = {}
    try:
        t0 = time.time()
        r = httpx.get(home, timeout=15, follow_redirects=True)
        out["home_http_ms"] = round((time.time() - t0) * 1000)
        out["home_status"] = r.status_code
        body = r.text.lower()
        out["free_tier_signals"] = any(k in body for k in ["free tier", "free plan", "free forever", "start free", "$0"])
    except Exception as e:
        trace(run_id, "trial_probe", f"{cand['name']}: probe failed", str(e))
        return
    try:
        r2 = ctx["tavily"].search(f"{cand['name']} free tier free plan limits", max_results=3)
        out["free_tier_evidence"] = "; ".join(_cut(x.get("content", ""), 200) for x in r2.get("results", []))[:600]
    except Exception:
        out["free_tier_evidence"] = ""
    info = f"probe: home {out.get('home_status')} in {out.get('home_http_ms')}ms; free-tier signals: {out.get('free_tier_signals')}"
    price_claims = [c for c in _claims(cand["id"], {"price"}) if re.search(r"free|trial|\$0", c["text"], re.I)]
    for c in price_claims:
        _add_ev(run_id, c["id"], "trial_probe", "probe", home, f"{info}. {out.get('free_tier_evidence','')}", json.dumps(out), 1 if out.get("free_tier_signals") else 0)
    if not price_claims:
        cid = _add_claim(run_id, cand["id"], "spec", f"Observed public surface: {info}", home)
        _add_ev(run_id, cid, "trial_probe", "probe", home, info, json.dumps(out), 1)
    trace(run_id, "trial_probe", f"{cand['name']}: {info}")


# ---------- spec_independent ----------


def spec_independent(ctx, cand):
    """Hardware/specs: vendor spec sheet vs independent measurements."""
    run_id = ctx["run_id"]
    spec_claims = _claims(cand["id"], {"spec"})
    if not spec_claims:
        trace(run_id, "spec_independent", f"{cand['name']}: no spec claims")
        return
    try:
        res = ctx["tavily"].search(f"{cand['name']} independent benchmark measured review test", max_results=5)
        blob = "\n".join(f"{r.get('title','')} ({r.get('url','')}): {_cut(r.get('content',''),600)}" for r in res.get("results", []))
    except Exception as e:
        trace(run_id, "spec_independent", f"{cand['name']}: search failed", str(e))
        return
    out = models.json_chat(
        "extract",
        "Compare vendor spec claims to independent measurements found in reviews.",
        f"Product: {cand['name']}\nIndependent sources:\n{blob[:20000]}\n\nClaims:\n{json.dumps([{'id': c['id'], 'text': c['text']} for c in spec_claims], indent=1)}\n"
        'Return JSON: {"results": [{"id": <claim id>, "verdict": "supports|contradicts|absent", "evidence": "<measured/observed figure>", "url": "<source>"}]}',
        max_tokens=4000,
    )
    sup = {"supports": 1, "contradicts": -1, "absent": 0}
    if isinstance(out, list):
        out = {"results": out}
    n = 0
    for r in out.get("results", []):
        if r.get("id") in {c["id"] for c in spec_claims}:
            _add_ev(run_id, r["id"], "spec_independent", "citation", r.get("url", ""), r.get("evidence", ""), "", sup.get(r.get("verdict"), 0))
            n += 1
    trace(run_id, "spec_independent", f"{cand['name']}: {n} claims vs independent sources")


# ---------- registry ----------

CHECKS = {
    "doc_audit": {
        "fn": doc_audit,
        "description": "Audit security/price/SLA claims against the vendor's own trust-center, legal, and pricing documents.",
    },
    "status_history": {
        "fn": status_history,
        "description": "Reconstruct real reliability from the public status page and compare to marketed uptime. For SaaS/online services.",
    },
    "reputation": {
        "fn": reputation,
        "description": "Community sentiment, complaint patterns, and vendor viability (funding/layoffs) from public sources.",
    },
    "live_benchmark": {
        "fn": live_benchmark,
        "description": "Run a real benchmark against the product. Only for runnable dev tools/infra with a configured target.",
    },
    "trial_probe": {
        "fn": trial_probe,
        "description": "Probe the public product surface: page latency, free-tier existence. For SaaS with a public site.",
    },
    "spec_independent": {
        "fn": spec_independent,
        "description": "Compare spec-sheet claims to independent measured reviews. For hardware/physical products.",
    },
}
