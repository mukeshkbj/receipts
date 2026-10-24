# Progress — Receipts (Nebius x NVIDIA Global AI Hackathon)

Deadline: **Oct 30, 2026, 10:00am PDT** · Track: Best Apps & Agents

## Done

- Concept: **Receipts** — due-diligence agent; claims in, verdicts out
  (MEASURED / CITED / CONTRADICTED / UNVERIFIABLE).
- Working product: FastAPI + SQLite claims ledger + single-page UI +
  bench harnesses (Qdrant REST + Chroma in-process) + CLI runner.
- High-ROI features (commit ed1452c → latest):
  - requirements gate (pause/edit/confirm), incumbent baseline,
    reply ingestion, watch/alerts, telemetry, actor badges,
    coverage grid, filters, markdown export, probe-honesty rule.
- Verified end-to-end: 3 categories (vector DB, e-signature, PM),
  requirements-gate API flow, UI screenshots.
- Real catches: Pinecone 99.95% SLA vs ~99.1% observed; PandaDoc
  ~98.9% observed uptime; DocuSign/Adobe negative sentiment.
- Run cost: ~$0.05–0.07/run; ~65% of calls on Nano.
- Review pass (commit 258fde0):
  - `ingest_reply` verified — fake Qdrant reply flipped 2 claims
    UNVERIFIABLE → CITED with reply evidence.
  - `watch` verified — baseline snapshot captured, diff-alerts armed.
  - Fixed: reputation viability false-positives (was scanning
    complaints for "layoff"); status_history "~None incidents" display.
  - `docs/feedback.md` written (real Token Factory/Tavily friction).
- Post-review hardening (latest commit):
  - `bench/chromabench.py` — real in-process Chroma benchmark,
    no Docker needed. p50=0.4ms @ 2k vectors verified.
  - `live_benchmark` dispatches qdrant→vdbench.py, chroma→chromabench.py.
  - `BENCH_TARGETS={"chroma":{"type":"chroma","n":20000,"dim":256}}` in `.env`.
  - Thin-evidence display: score cells show "—" (not 0) when the
    rationale says insufficient/no evidence; headline weighted score
    shows "—" when >half of claims are unverifiable.
- **Public URL live**: cloudflared tunnel in front of :8000
  (see /tmp/cf.log for the trycloudflare.com address; regenerated
  each restart — ephemeral, fine for video, not for judging).

## Gotchas learned

- Token Factory Nemotron 3 = hybrid reasoners; `enable_thinking: false`
  for extraction, big max_tokens for reasoning.
- Model regions: Ultra/Super us-central1, Nano/Lightning eu-north1.
- `json_chat` may return bare lists; `_d()` normalizes.
- Keys in `.env` (gitignored), never `.env.example`.
- No Docker on this machine — Chroma ephemeral client replaces the
  Qdrant path for a local MEASURED cell; Qdrant path stays for
  BENCH_URL targets (cloud/Docker/Serverless Job).
- ngrok needs an authtoken; cloudflared `--url` quick-tunnels don't.

## Remaining (submission checklist)

- **Persistent deploy** — tunnel dies with the laptop; judging runs
  Dec 1–15. Best story: Nebius AI Cloud VM/container (also deepens
  the platform requirement). Alternative: free-tier host.
- Rotate the Nebius + Tavily keys (values appeared in transcript).
- Push repo public (GitHub) — LICENSE + README already in place.
- Record ≤3-min video: brief w/ incumbent → requirements editor →
  live trace w/ actor badges → CONTRADICTED + MEASURED cells →
  coverage grid → outreach → paste-reply re-verdict → telemetry.
- Submit on Devpost; keep Fri as buffer.

## Commands

- Server: `.venv/bin/uvicorn backend.app:app --port 8000`
- Tunnel: `cloudflared tunnel --url http://localhost:8000`
- CLI: `.venv/bin/python run.py "<brief>"` (auto-skips the gate)
- Watch interval: `WATCH_INTERVAL_SEC` env (default 6h)
- Chroma bench: `.venv/bin/python bench/chromabench.py --n 20000 --dim 256`
