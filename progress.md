# Progress — Receipts (Nebius x NVIDIA Global AI Hackathon)

Deadline: **Oct 30, 2026, 10:00am PDT** · Track: Best Apps & Agents

## Done

- Concept: **Receipts** — due-diligence agent; claims in, verdicts out
  (MEASURED / CITED / CONTRADICTED / UNVERIFIABLE).
- Working end-to-end app committed: FastAPI + SQLite claims ledger +
  single-page verdict-matrix UI + Qdrant bench harness + CLI runner.
- Live verified run (run `1ea977fb0d3e`): vector-DB brief → 5 candidates,
  70 claims, 15 measured / 29 cited / 4 contradicted / 36 unverifiable,
  weighted scorecard (Weaviate 3.0 recommended), outreach drafts, decision
  brief. Real catch: Pinecone 99.95% SLA claim contradicted by ~99.1%
  observed status-page uptime.
- UI visually verified via headless browser screenshot.
- Design + plan docs under `docs/plans/`.

## Gotchas learned (don't relearn)

- Token Factory Nemotron 3 models are hybrid reasoners — hidden thinking
  eats the completion budget. `enable_thinking: false` via
  `chat_template_kwargs` for extraction; big `max_tokens` for reasoning.
- Model regions differ: Ultra/Super = us-central1, Nano/Lightning =
  eu-north1. `backend/models.py` routes per-model.
- `json_chat` may return a bare list; `_d()` normalizes.
- Keys live in `.env` (gitignored) — never in `.env.example`.

## Remaining

- Second demo run (e-signature brief) to prove generalization on camera.
- Optional: BENCH_TARGETS for a real MEASURED latency cell
  (`docker run -d -p 6333:6333 qdrant/qdrant` + env).
- Deploy for a public demo URL (Vercel/tunnel or any host).
- README demo notes done; record ≤3-min video; write tool feedback;
  submit on Devpost.

## Commands

- Server: `.venv/bin/uvicorn backend.app:app --port 8000`
- CLI run: `.venv/bin/python run.py "<brief>"`
- Run artifacts: `receipts.db` (SQLite)
