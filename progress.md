# Progress — Receipts (Nebius x NVIDIA Global AI Hackathon)

Deadline: **Oct 30, 2026, 10:00am PDT** · Track: Best Apps & Agents

## Done

- Concept: **Receipts** — due-diligence agent; claims in, verdicts out
  (MEASURED / CITED / CONTRADICTED / UNVERIFIABLE).
- Working product: FastAPI + SQLite claims ledger + single-page UI +
  Qdrant bench harness + CLI runner.
- High-ROI features (commit ed1452c → latest):
  - requirements gate (pause/edit/confirm), incumbent baseline,
    reply ingestion, watch/alerts, telemetry, actor badges,
    coverage grid, filters, markdown export, probe-honesty rule.
- Verified end-to-end: 3 categories (vector DB, e-signature, PM),
  requirements-gate API flow, UI screenshots.
- Real catches: Pinecone 99.95% SLA vs ~99.1% observed; PandaDoc
  ~98.9% observed uptime; DocuSign/Adobe negative sentiment.
- Run cost: ~$0.05–0.07/run; ~65% of calls on Nano.

## Gotchas learned

- Token Factory Nemotron 3 = hybrid reasoners; `enable_thinking: false`
  for extraction, big max_tokens for reasoning.
- Model regions: Ultra/Super us-central1, Nano/Lightning eu-north1.
- `json_chat` may return bare lists; `_d()` normalizes.
- Keys in `.env` (gitignored), never `.env.example`.

## Remaining (submission checklist)

- Deploy public demo URL (any host or tunnel; must stay up to ~Jan).
- BENCH_TARGETS for a MEASURED latency cell in the video
  (`docker run -d -p 6333:6333 qdrant/qdrant` + env line).
- Record ≤3-min video: brief → requirements editor → live trace →
  CONTRADICTED cell → coverage grid → outreach → paste-reply update.
- Write `docs/feedback.md` (Token Factory/Tavily/Nebius notes) —
  eligible for the $100 feedback prize.
- Submit on Devpost; keep Fri as buffer.

## Commands

- Server: `.venv/bin/uvicorn backend.app:app --port 8000`
- CLI: `.venv/bin/python run.py "<brief>"` (auto-skips the gate)
- Watch interval: `WATCH_INTERVAL_SEC` env (default 6h)
