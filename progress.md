# Progress — Receipts (Nebius x NVIDIA Global AI Hackathon)

Deadline: **Oct 30, 2026, 10:00am PDT** · Track: Best Apps & Agents

## Done

- Hackathon recon: rules, tracks, judging (Tech Impl / Design / Impact / Idea,
  equal 1–5), prizes, credits (`NEBIUS-DEVPOST-GLOBAL26` + Builders Program).
- Concept chosen: **Receipts** — due-diligence agent; claims in, verdicts out
  (MEASURED / CITED / CONTRADICTED / UNVERIFIABLE). Broadened beyond dev tools;
  verification = pluggable check registry.
- Design doc: `docs/plans/2026-10-24-receipts-design.md`
- Build plan: `docs/plans/2026-10-24-receipts-implementation.md`

## Remaining (per plan)

- Day 0 (today): credits/keys → `backend/spike.py` Token Factory call →
  Serverless Job hello-world → scaffold + commit.
- Days 1–5 per implementation plan; video + submission Thu Oct 29 night.

## Open questions

- Serverless Jobs Python API surface — confirm in Day-0 spike; fallback is
  local Docker benches (inference gate still satisfied via Token Factory).
- Which vector DBs to benchmark (suggest Qdrant + Weaviate + pgvector vs one
  managed SaaS) — decide at Day 3.

## Evidence

- Design/plan files committed alongside this file. Spikes pending.
