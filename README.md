# Receipts

**Claims in, verdicts out.** A due-diligence agent for any purchase — it verifies
what vendors claim instead of repeating it.

Deep research tools tell you what vendors *claim*. Procurement platforms tell you
what others *paid*. Receipts tells you what is actually **true**: every cell in
the decision matrix carries a verdict — `MEASURED`, `CITED`, `CONTRADICTED`, or
`UNVERIFIABLE` — with evidence behind it.

Built for the **Nebius x NVIDIA Global AI Hackathon** (Best Apps & Agents track).

## How it works

```
brief ─► elicit ─► discover ─► ingest ─► verify ─► score ─► negotiate ─► monitor
        (Ultra)    (Tavily)     (Nano)    (checks)  (Ultra)   (Ultra)    (job)
```

1. **Elicit** — brief → weighted requirements model (Nemotron 3 Ultra)
2. **Discover** — candidate discovery via Tavily, dedupe via Nemotron 3 Nano
3. **Ingest** — marketing claims extracted from vendor pages (Nano)
4. **Verify** — Ultra selects from a pluggable check registry per candidate:
   - `doc_audit` — claims vs the vendor's own trust center / DPA / SLA / pricing
   - `status_history` — real reliability reconstructed from public status pages
   - `reputation` — sentiment, complaint patterns, viability signals
   - `trial_probe` — probe of the public product surface
   - `live_benchmark` — real benchmark against runnable infra (see `bench/`)
   - `spec_independent` — spec sheets vs independent measured reviews (hardware)
5. **Verdicts** — per claim: CONTRADICTED > MEASURED > CITED > UNVERIFIABLE
6. **Score** — transparent weighted scorecard, every cell traceable to evidence
7. **Negotiate** — outreach drafts armed with the weak/contradicted claims
8. **Monitor** — scheduled re-checks (roadmap)

## NVIDIA + Nebius usage

- **Nemotron 3 Ultra 550B** (Token Factory, us-central1) — elicitation, check
  planning via tool-calling, scoring, briefs, outreach drafts
- **Nemotron 3 Nano 30B** (Token Factory, eu-north1) — bulk claim extraction and
  document auditing (cheap calls, high volume — deliberate model routing)
- **Tavily** — candidate discovery, page extraction, sentiment/incident search
- **Nebius AI Cloud Serverless Jobs** — the `live_benchmark` harness
  (`bench/vdbench.py`) is container-ready for Serverless Jobs; it also runs
  locally via Docker for development

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill NEBIUS_API_KEY and TAVILY_API_KEY
```

## Run

CLI end-to-end:

```bash
.venv/bin/python run.py "we need a managed vector database under \$500/mo for ~10M vectors, p99 < 50ms"
```

Web UI:

```bash
.venv/bin/uvicorn backend.app:app --port 8000
# open http://localhost:8000
```

Type a purchase brief → watch the agent trace stream → click any verdict cell
for its evidence → read the decision brief + drafted outreach.

## Deploy

The Dockerfile runs the full app (SQLite is embedded and self-initializing).
Set `NEBIUS_API_KEY` + `TAVILY_API_KEY` (and optional `BENCH_TARGETS`) as
env vars on any container host:

```bash
docker build -t receipts .
docker run -p 8000:8000 --env-file .env receipts
```

Google Cloud Run example:

```bash
gcloud run deploy receipts --source . --set-env-vars "NEBIUS_API_KEY=...,TAVILY_API_KEY=..." --allow-unauthenticated
```

## Live benchmarks

Point `BENCH_TARGETS` at a real target to get MEASURED verdicts:

```bash
# local Qdrant via docker
docker run -d -p 6333:6333 qdrant/qdrant
export BENCH_TARGETS='{"qdrant": {"type":"qdrant","url":"http://localhost:6333"}}'

# or a Qdrant Cloud free cluster
export BENCH_TARGETS='{"qdrant": {"type":"qdrant","url":"https://xxx.qdrant.io","api_key":"..."}}'

# or Chroma in-process — no server needed (pip install chromadb)
export BENCH_TARGETS='{"chroma": {"type":"chroma","n":20000,"dim":256}}'
```

`live_benchmark` matches the candidate name to a configured target and runs
the matching harness — `bench/vdbench.py` for Qdrant, `bench/chromabench.py`
for Chroma (in-process, ephemeral client) — attaching measured p50/p99/qps as
evidence and contradicting marketed latency claims when they fail at your
workload. `chromadb` is only needed for the chroma target.

Tip: name candidates in the brief (`explicitly evaluate: Chroma, Qdrant`) to
guarantee they are evaluated — the pipeline seeds brief-named candidates.

## Repo layout

```
backend/    FastAPI app, agent pipeline, check registry, SQLite claims ledger
  schema.sql   runs / candidates / claims / evidence / verdicts / scores / outreach
  pipeline.py  staged agent loop + trace
  checks.py    the six verification checks
  models.py    Token Factory client + model routing
web/        single-page UI (brief → live trace → verdict matrix → brief → outreach)
bench/      vector-DB benchmark harness (Serverless Job or local Docker)
docs/plans/ design doc + build plan
```

## Stack

Python 3.12+ · FastAPI · SQLite · `openai` SDK → Nebius Token Factory ·
`tavily-python` · Tailwind (CDN) · MIT license

## Notes for judges

- Every verdict cell in the UI opens its evidence drawer: source URL, excerpt,
  measured values, and whether the evidence supports or contradicts the claim.
- `CONTRADICTED` is the interesting column — it means Receipts caught the
  marketing lying (or failing at *your* workload).
- Feedback on Token Factory, Tavily, and Nebius tooling is in
  `docs/feedback.md`.
