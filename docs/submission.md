# Devpost submission — draft copy

**Project name:** Receipts
**Track:** Best Apps & Agents
**Tagline:** Claims in, verdicts out — a due-diligence agent that verifies what vendors claim instead of repeating it.

## Description (~paste-ready)

### The problem

Buying software means trusting vendor marketing. Deep-research tools cite
claims; procurement platforms benchmark prices. Nobody checks whether the
claims are *true* — "99.99% uptime", "p99 < 50ms", "SOC 2" go unverified
until after you buy.

### What it does

Receipts is a multi-step autonomous agent that runs a real due-diligence
pass on any purchase over a threshold:

1. **Elicit** — parses a plain-English brief into a weighted requirements
   model, then *pauses* for the buyer to edit and confirm.
2. **Discover** — finds and dedupes candidate vendors; seeds an incumbent
   baseline ("we pay $700/mo for Pinecone") and any candidates the buyer
   names.
3. **Ingest** — extracts verifiable claims from each vendor's own pages.
4. **Verify** — an LLM planner picks from a six-check registry: doc/terms
   audit, status-page incident reconstruction, reputation triangulation,
   trial probing, spec-vs-independent, and **live benchmarking** — the agent
   runs a real workload against runnable candidates (our demo measures
   Chroma at 20k vectors and attaches p50/p99/qps as evidence).
5. **Verdict** — every claim lands as MEASURED, CITED, CONTRADICTED, or
   UNVERIFIABLE, each with its evidence behind it.
6. **Score** — a transparent weighted scorecard; the recommendation is
   anchored to the math, not the model's opinion.
7. **Negotiate** — drafts outreach with the pointed questions the evidence
   generated ("Your status page shows 7 incidents this quarter — what is
   your SLA credit process?").
8. **Stay alive** — paste vendor replies to re-audit claims; watches keep
   checking after the decision.

Real catches from our runs: Pinecone's marketed 99.95% SLA versus ~99.1%
observed uptime; a Chroma latency claim *confirmed* by live benchmark.

### How we built it

- **Nebius Token Factory** is the inference backbone — ~35 calls/run,
  ~$0.06/run:
  - **Nemotron 3 Ultra** — brief parsing, check planning (via tool
    calling), evidence→verdict scoring, negotiation, brief writing
  - **Nemotron 3 Nano** — bulk claim/document extraction (~65% of calls)
  - **Nemotron 3.5 Lightning** — fast utility steps
  - Cost-aware routing is deliberate: cheap models where recall suffices,
    Ultra only where reasoning pays. The UI reports per-model token usage.
- **Tavily** — candidate discovery and page extraction; the evidence
  pipeline that feeds the checks.
- FastAPI + SQLite claims ledger + background pipeline threads; single-page
  UI shows the live trace with per-step actor badges.

### Challenges

Nemotron 3 models are hybrid reasoners — hidden thinking silently consumed
the output budget until we found `enable_thinking` and per-model regional
endpoints. Verdict honesty was the other hard part: we reserve MEASURED for
real execution so a homepage ping can't masquerade as a benchmark.

### What we're proud of

The claims ledger is honest by construction — a bad score with an evidence
trail beats a confident wrong answer. It caught real contradictions in a
first run, and the live benchmark produced a MEASURED verdict, not a
mocked one.

### What's next

Contract-upload analysis, inbound vendor email, more benchmark harnesses
(Milvus, Weaviate self-hosted), and Nebius Serverless Jobs for scheduled
watch runs.

## Required fields

- **Demo URL:** (tunnel URL while staging; swap to deployed URL)
- **Video URL:** (YouTube link after recording)
- **Repo:** https://github.com/mukeshkbj/receipts
- **Feedback:** see `docs/feedback.md` in the repo — real Token Factory /
  Tavily friction notes (thinking budgets, per-model regions, extract depth).
