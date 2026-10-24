# Receipts — Design Doc

**Track:** Best Apps & Agents — Nebius x NVIDIA Global AI Hackathon
**Deadline:** Oct 30, 2026, 10:00am PDT
**Decided:** Oct 24, 2026

## Pitch

A due-diligence agent for any purchase. Claims in, verdicts out.

Deep research tools tell you what vendors claim. Procurement platforms tell you what
others paid. Receipts tells you what is actually true: every cell in the decision
matrix carries a verdict — MEASURED, CITED, CONTRADICTED, UNVERIFIABLE — with its
evidence attached.

## Requirements mapping (the pass/fail gate)

- Runs on Nebius Token Factory: all inference (Nemotron 3 Ultra for reasoning,
  Nano/Super for bulk extraction) via the OpenAI-compatible API.
- Nebius AI Cloud: live benchmarks and trial probes run as Serverless Jobs.
- NVIDIA open source model: Nemotron family throughout.
- Tavily: candidate discovery + page extraction + citations ($3k bonus prize).
- Deliverables: working demo URL, ≤3-min YouTube video, public repo with MIT
  license + README, written tool feedback.

## Judging map (equal weight, 1–5)

| Criterion | How Receipts scores |
|---|---|
| Technological Implementation | Token Factory model routing + Serverless Jobs execution + Tavily backbone — structural, not cosmetic |
| Design | Claims-ledger matrix UI + live agent trace + evidence drawer. Not a chat box |
| Potential Impact | Anyone who buys anything; demo covers a dev tool and a business SaaS |
| Quality of Idea | Verification-by-execution is white space between deep research and procurement platforms |

## Architecture

```
brief ──► elicit ──► discover ──► ingest ──► verify ──► score ──► negotiate ──► monitor
          (Ultra)    (Tavily)     (Nano)     (checks)   (Ultra)   (Ultra)      (job)
                                              │
                          claims ledger (SQLite): candidates, claims,
                          evidence, verdicts, scores, outreach drafts
```

- **Backend:** Python + FastAPI. Agent loop is a hand-rolled tool-calling loop
  (~one file) using the `openai` SDK pointed at Token Factory. Full control of
  the trace stream for the UI and video.
- **Frontend:** Next.js + Tailwind. Design is 25% of the score — this is the
  surface where it is won or lost.
- **Store:** SQLite (`schema.sql`), no ORM layer beyond a thin helper.
- **Execution:** checks are plain Python functions registered as agent tools.
  `live_benchmark` and `trial_probe` dispatch to Nebius Serverless Jobs; the rest
  run in-process.

## Claims ledger (data model)

- `runs`: brief text, requirements model JSON, status, category
- `candidates`: name, vendor, homepage, docs/status/trust-center URLs
- `claims`: candidate_id, text, type (spec | price | sla | security | viability | sentiment)
- `evidence`: claim_id, kind (citation | doc | status_page | sentiment | measurement | probe), url, excerpt, measured_value, check_name
- `verdicts`: claim_id, verdict, confidence, rationale
- `scores`: candidate_id, requirement_key, score, weight, rationale
- `outreach`: candidate_id, draft_subject, draft_body, questions_json

## Check registry

Each check is a bounded tool. The agent picks which apply per candidate.

| Check | Category | Mechanism |
|---|---|---|
| `doc_audit` | any SaaS/service | Tavily-extract DPA/SLA/pricing/trust-center; Nano extracts terms; Ultra cross-checks claims (SOC2 real? auto-renewal? SLA credits? residency? hidden pricing) |
| `status_history` | any SaaS | pull public status-page incident history; reconstruct real uptime vs marketed |
| `reputation` | everything | G2/Capterra/HN/Reddit sentiment via Tavily; complaint-pattern extraction; funding/layoff viability signals |
| `trial_probe` | free-tier SaaS | scripted task against a real trial (import N records, hit API rate limit, exercise the claimed feature) — Nebius Serverless Job |
| `live_benchmark` | dev tools/infra | prebuilt harness runs user's workload against candidate (e.g. Qdrant at 10M vectors) — Nebius Serverless Job. The agent orchestrates; it does not write arbitrary benchmarks |
| `spec_independent` | hardware | spec-sheet claims vs independent bench databases/teardowns |

## Agent loop

1. **Elicit** (Ultra): brief (+ optional repo/site context) → weighted requirements
   model `{requirements: [{key, weight, must_have}]}`
2. **Discover** (Tavily): candidate long list → dedupe → top 5
3. **Ingest** (Nano/Super): per candidate, extract pages → structured claims rows
4. **Verify** (Ultra plans check selection): run checks → evidence rows →
   verdict per claim
5. **Score** (Ultra): weighted scorecard, every cell traceable to evidence
6. **Negotiate** (Ultra): outreach drafts with evidence-generated questions
7. **Monitor** (scheduled Serverless Job): re-run status/reputation checks;
   diff → alerts

## UI (single-page app)

- Brief input → live run view: streaming tool-call trace (the agent working)
- Matrix view: candidates × claims, verdict badges per cell
- Evidence drawer: click a cell → excerpts, URLs, measured traces
- Decision brief: ranked scorecard + recommendation + rationale
- Outreach tab: per-finalist draft emails with pointed questions

## Demo plan (the 3-minute video)

Two purchases, proving the engine generalizes:

1. **Managed vector DB** ("< $500/mo, ~10M vectors, p99 < 50ms") — live_benchmark
   fires; one marketed latency claim fails at the user's workload → cell flips
   CONTRADICTED with measured trace. The money moment.
2. **E-signature SaaS** — doc_audit + status_history + reputation + trial_probe
   fire; catches a "SOC2" marketing claim absent from the trust center and an
   auto-renewal clause.

## Scope cuts (agreed)

- No inbound email — vendor replies pasted into the UI.
- No private-contract upload analysis.
- Benchmark harness is prebuilt per category; agent picks configs only.
- Trial probes only where a free tier exists and the task is scriptable.
- Monitor stage ships if Day 5 has slack; otherwise README-roadmapped.

## Risks

| Risk | Mitigation |
|---|---|
| Credit/billing onboarding friction (bank card required) | Day 0 task; Discord support path known |
| Serverless Jobs API unfamiliarity | Day 0 spike: hello-world job before any design commitment |
| G2/review pages gated | Tavily covers HN/Reddit/GitHub issues as public sentiment sources |
| Scope creep kills the video | Thu is feature-frozen; Fri is buffer only |

## Free resources

- $25 Token Factory credit — code `NEBIUS-DEVPOST-GLOBAL26`
- +$25 via Nebius Builders Program (adds $25 Tavily, $100 LangSmith)
- Builders Program: https://dev.nebius.com/builders
