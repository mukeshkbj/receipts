# Receipts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement task-by-task.

**Goal:** ship a working due-diligence agent + matrix UI + ≤3-min video + Devpost
submission before Oct 30, 2026 10:00am PDT.

**Architecture:** FastAPI backend owning a hand-rolled Nemotron agent loop and a
SQLite claims ledger; Next.js matrix UI; benchmarks/probes as Nebius Serverless
Jobs; Tavily for discovery + extraction. See `2026-10-24-receipts-design.md`.

**Tech stack:** Python 3.12, FastAPI, `openai` SDK (Token Factory base URL),
`tavily-python`, SQLite stdlib, Next.js + Tailwind, MIT license.

**Working rule:** commit at every green checkpoint. Thursday Oct 29 is
feature-frozen; Friday is buffer only.

## Day 0 — Sat Oct 24: accounts + spike (today)

1. Claim credits: Token Factory form w/ `NEBIUS-DEVPOST-GLOBAL26`; join Builders
   Program (adds $25 TF + $25 Tavily). Note: billing requires a bank card.
2. Get Tavily API key; create Nebius API key.
3. Repo: `git init`, MIT `LICENSE`, `.gitignore` (`.env`, `.next/`, `__pycache__/`),
   `README.md` stub.
4. **Spike A:** `openai` client → Token Factory → Nemotron 3 Ultra returns text.
   Success = one printed completion. File: `backend/spike.py`.
5. **Spike B:** Nebius Serverless Job hello-world (container runs, logs back).
   Success = job completes in console. If blocked >1h → fall back: benches run
   locally via Docker, README documents the intended Serverless path and the
   runtime inference calls still satisfy the gate.
6. Scaffold: `backend/` (FastAPI app, `/runs` POST + `/runs/{id}` GET stubs) and
   `web/` (`create-next-app` + Tailwind). Commit.

## Day 1 — Sun Oct 25: ledger + pipeline

1. `backend/db.py` + `schema.sql`: tables per design doc.
2. `backend/models.py`: Token Factory client; `reason()` → Ultra, `extract()` →
   Nano/Super. One env-var model map.
3. `backend/agent.py`: tool registry (`@tool` decorator → name/schema/fn) +
   `run_loop()` with tool calls, trace events appended to `runs.trace`.
4. `backend/tools/elicit.py`: brief → requirements model JSON.
5. `backend/tools/discover.py`: Tavily search → candidate list (top 5, with
   docs/status/pricing URLs).
6. `backend/tools/ingest.py`: Tavily extract → Nano → claim rows in ledger.
7. Checkpoint: CLI `python -m backend.run "we need a vector DB under $500/mo"`
   populates `candidates` + `claims`. Commit.

## Day 2 — Mon Oct 26: verification core

1. `checks/doc_audit.py`: fetch trust center/DPA/SLA/pricing; claim↔doc
   cross-check → evidence + verdict rows.
2. `checks/status_history.py`: status-page scrape → uptime table vs claim.
3. `checks/reputation.py`: sentiment + complaint patterns + viability signals.
4. `backend/verdicts.py`: evidence → verdict rules (CONTRADICTED outranks CITED;
   MEASURED outranks all; no evidence → UNVERIFIABLE).
5. Ultra-driven check selection: `plan_checks(candidate, claims)` tool.
6. Checkpoint: e-signature run yields verdicted claims. Commit.

## Day 3 — Tue Oct 27: execution + deliverables

1. `checks/live_benchmark.py` + `bench/vdbench/` (vector-DB harness: configurable
   dataset size + latency assertions; runs via Serverless Job, falls back to
   `docker run` locally for dev).
2. `checks/trial_probe.py`: scripted trial task (pick one free-tier SaaS for demo).
3. `tools/score.py` + `tools/negotiate.py`: weighted scorecard rows; outreach
   drafts with evidence-derived questions.
4. `tools/brief.py`: decision brief JSON → UI payload.
5. Checkpoint: vector-DB run end-to-end via CLI produces verdicts incl. ≥1
   MEASURED cell. Commit.

## Day 4 — Wed Oct 28: UI (Design sprint)

1. `/runs` POST form → run page.
2. Live trace pane: poll `/runs/{id}` → render tool-call stream.
3. Matrix: candidates × claims, verdict badges, evidence drawer on click.
4. Brief page: scorecard + outreach drafts.
5. Polish pass: typography, spacing, badge semantics. Commit.

## Day 5 — Thu Oct 29: hardening + submission (FEATURE FREEZE)

1. Two clean end-to-end runs (vector DB + e-signature). Fix blockers only.
2. Deploy demo (Vercel or local-tunnel URL that stays up through judging —
   a persistent deploy is safer).
3. README: setup, run, architecture diagram, "how Token Factory/Nemotron/Tavily
   were used" section, feedback writeup.
4. Record ≤3-min video: brief → trace → CONTRADICTED moment → matrix → brief →
   outreach drafts. Upload unlisted/public YouTube.
5. Submit on Devpost the same night. Keep Friday as buffer.

## Day 6 — Fri Oct 30: buffer only

- Re-submit fixes if Devpost flags anything. Hard stop 10:00am PDT.
