# Devpost submission — field-by-field copy

Everything below maps 1:1 to the Devpost form. Paste-ready.

---

## Project name

```
Receipts
```

## Tagline / short pitch

```
A due-diligence agent that verifies what vendors claim — claims in, verdicts out.
```

## Track

**Best Apps & Agents**

## Built with (tags — add in "Built With" field)

```
Nebius Token Factory, NVIDIA Nemotron, Tavily, FastAPI, Python, SQLite
```

## Try-it-out links

| Field | Value |
|---|---|
| Website / demo | `https://<deployed-or-tunnel-url>` ← update |
| GitHub repo | `https://github.com/mukeshkbj/receipts` |
| Video | `https://youtube.com/...` ← after recording |

## Prize opt-ins

- [x] **Best Use of Tavily** ($3,000) — Tavily is the discovery + extraction
  backbone: ~20 calls/run across candidate search, page extraction,
  reputation and status-history reconstruction. Opt in.
- [ ] City Winner Award — N/A unless you attended an IRL Builders & Brews event.
- [x] Most Valuable Feedback — `docs/feedback.md` is in the repo; also paste
  the feedback text below into their feedback field if the form has one.

## Story (Devpost "Story" section — their prompts, our answers)

### Inspiration

Every team buys software on trust. Deep-research tools *cite* vendor claims;
procurement platforms benchmark *price*. Nobody checks whether the claims
are true — "99.99% uptime", "p99 < 50ms", "SOC 2" go unverified until the
invoice is already paid. We wanted an agent that behaves like a real
diligence team: read the claims, then go prove or break them.

### What it does

Receipts runs a multi-step autonomous due-diligence pass on any purchase:

1. **Elicit** — a plain-English brief becomes a weighted requirements
   model, then the run *pauses* so the buyer can edit and confirm.
2. **Discover** — finds and dedupes candidate vendors, seeds an incumbent
   baseline ("we pay $700/mo for Pinecone"), and always honors candidates
   the buyer names.
3. **Ingest** — extracts verifiable claims from each vendor's own pages.
4. **Verify** — a planner selects from a six-check registry: doc/terms
   audit, status-page incident reconstruction, reputation triangulation,
   trial probing, spec-vs-independent sources, and **live benchmarking** —
   the agent runs a real workload against runnable candidates (our demo
   benchmarks Chroma at 20k vectors and attaches p50/p99/qps as evidence).
5. **Verdict** — every claim lands MEASURED, CITED, CONTRADICTED, or
   UNVERIFIABLE with its evidence attached.
6. **Score** — transparent weighted scorecard; the recommendation is
   anchored to the math.
7. **Negotiate** — drafts outreach with pointed questions the evidence
   generated ("your status page shows 7 incidents this quarter — what is
   your SLA credit process?").
8. **Persist** — pasted vendor replies re-audit claims; watch mode keeps
   checking after the decision.

Real catches from our runs: Pinecone's marketed 99.95% SLA vs ~99.1%
observed uptime; Chroma's latency claim **confirmed by a live benchmark** —
a MEASURED verdict, not a citation.

### How we built it

- **Nebius Token Factory** is the inference backbone — ~35 calls/run at
  ~$0.06/run:
  - **Nemotron 3 Ultra** — brief parsing, check planning (tool calling),
    scoring, negotiation drafts, decision briefs
  - **Nemotron 3 Nano** — bulk claim/document extraction (~65% of calls)
  - **Nemotron 3.5 Lightning** — fast utility steps
- Routing is deliberate and cost-aware: Nano where recall suffices, Ultra
  where reasoning pays. The UI reports per-model token usage per run.
- **Tavily** powers discovery + page extraction — the evidence pipeline
  feeding every check.
- FastAPI + SQLite claims ledger + background pipeline threads; a
  single-page UI streams the agent trace with per-step actor badges.
- The `live_benchmark` harness is container-ready for **Nebius Serverless
  Jobs** (`bench/`); our demo ran it locally against an in-process Chroma.

### Challenges we ran into

Nemotron 3 models are hybrid reasoners — hidden thinking silently consumed
the output token budget, returning truncated JSON, until we found
`enable_thinking` and the per-model regional endpoints (Ultra on
us-central1, Nano/Lightning on eu-north1). The other hard problem was
*verdict honesty*: we reserve MEASURED for real execution so a homepage
ping can never masquerade as a benchmark.

### Accomplishments that we're proud of

The claims ledger is honest by construction — a low score with an evidence
trail beats a confident wrong answer. It caught real contradictions on its
first runs (Pinecone SLA vs observed uptime), produced a genuine MEASURED
verdict from a live benchmark, and the whole run costs about six cents.

### What we learned

Small models are enough for structured extraction when thinking is off —
routing, not raw model size, drives both quality and cost. And "verify,
don't cite" is a discipline: every score needed an evidence trail or the
matrix was just prettier marketing.

### What's next for Receipts

Contract-upload analysis, inbound vendor email parsing, more benchmark
harnesses (Weaviate, Milvus self-hosted), and watch mode on Nebius
Serverless Jobs so the audit keeps running after the demo ends.

## Platform usage statement (the "highlight Nebius/NVIDIA usage" field)

Receipts makes ~35 runtime calls per analysis to **Nebius Token Factory**
(OpenAI-compatible API) across three NVIDIA open models:
**NVIDIA Nemotron 3 Ultra** (reasoning, planning, scoring),
**NVIDIA Nemotron 3 Nano** (bulk extraction), and
**Nemotron 3.5 Lightning** (utility steps). Ultra's tool-calling selects
verification checks per candidate; per-run token usage and cost are
persisted and shown in the UI. The benchmark harness is designed to run as
a **Nebius AI Cloud Serverless Job**. **Tavily** provides candidate
discovery and vendor-page extraction (~20 calls/run).

## Feedback field (if separate — also in repo docs/feedback.md)

Token Factory was genuinely drop-in via the OpenAI SDK. Two discoverability
issues cost us debugging cycles: (1) hybrid-reasoning models spend hidden
thinking tokens inside max_tokens — extraction calls returned truncated
JSON until we found `enable_thinking: false`; a `reasoning_effort` alias or
models-page callout would save every builder one failure. (2) Model
availability is per-region (Ultra us-central1, Nano eu-north1) and a 404
looks like a bad model name — the error could name the correct region.
Tavily `extract` handled 80–90% of vendor pages cleanly; JS-heavy sites
return nav skeletons — a per-URL content-length or confidence hint would
help callers decide to retry. Onboarding requiring a bank card for promo
credits reads like a paywall; a heads-up on the resources page would help.

## Pre-existing project statement

```
This project was created entirely during the Submission Period. The
repository history (github.com/mukeshkbj/receipts) shows initial commit
through final submission.
```

## Required checklist status

- [x] Working project on Token Factory + NVIDIA Nemotron models
- [x] Track: Best Apps & Agents
- [x] Project description (above)
- [ ] Demo URL — **needs permanent deploy or tunnel URL at submit time**
- [ ] ≤3-min YouTube video **with audio covering Token Factory + Nemotron
  usage** — narration required, captions alone do not satisfy
- [x] Public repo w/ MIT license + README setup — github.com/mukeshkbj/receipts
- [x] Feedback — docs/feedback.md + text above
- [x] New-project statement
