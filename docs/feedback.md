# Tool feedback — Token Factory, Tavily, Nebius

Real notes from building Receipts (a multi-agent due-diligence pipeline:
~35 LLM calls + ~20 Tavily calls per run, three Nemotron model sizes).

## Nebius Token Factory

**What worked well**

- OpenAI-compatible API worked first try with the stock `openai` SDK —
  base_url + api_key was the entire integration.
- Model routing across sizes is the product. Routing planning/scoring to
  Nemotron 3 Ultra and bulk extraction to Nano 30B cut our per-run cost to
  ~$0.05–0.07 while keeping reasoning quality where it matters.
- `chat_template_kwargs.enable_thinking` works and is *necessary* for
  extraction use cases (see below).

**Friction we hit**

- **Hybrid-reasoning defaults surprise.** All three Nemotron 3 models spend
  hidden thinking tokens inside `max_tokens`. With thinking on, a 3000-token
  extraction call returned `"\n{\n"` — the budget went to reasoning, not the
  answer. Took us a debugging cycle to find `enable_thinking: false`. A
  `reasoning_effort` alias (we tried it; returned `content: null`) or a
  doc callout on the models page would save every builder one failure.
- **Region is per-model and undocumented on the models page.** Ultra/Super
  only respond on `us-central1`, Nano/Lightning on `eu-north1`. A 404 on the
  wrong region looks like a bad model name, not a wrong endpoint — the error
  could name the correct region.
- Tool calling on Ultra worked but needed `tool_choice: "auto"` plus a
  "call each applicable tool once" system prompt, or it either called zero
  tools or narrated instead. Fine once learned; a cookbook example for
  "select-and-run N tools" would help.
- Onboarding required a bank card even to redeem promo credits — worth a
  heads-up on the hackathon resources page, it reads like a paywall on first
  pass.

## Tavily

**What worked well**

- `extract` on vendor pages (pricing/security/trust paths) returned clean
  markdown 80–90% of the time — good enough to feed a small extraction model.
- `failed_results` reporting which URLs failed let us degrade gracefully
  without try/except per URL.
- Search snippets were good enough to reconstruct outage histories and
  sentiment where no structured API exists.

**Friction**

- `extract` depth "basic" truncates long docs unpredictably on JS-heavy
  vendor sites (SPAs return nav skeletons). An "advanced" depth or reader
  mode helps; partial failure is silent-ish — a per-URL confidence or
  content-length hint would let callers decide whether to retry.
- Search occasionally returns listicles SEO-spammed for the category;
  we filter by instructing the dedupe model, but a domain-allowlist for
  "official sites only" intent would tighten candidate discovery.

## Nebius AI Cloud (Serverless Jobs)

- The benchmark harness (`bench/vdbench.py`) is container-ready for
  Serverless Jobs; for the demo we ran it against local Docker Qdrant.
  A minimal "submit this container as a job" example in the hackathon
  resources — the console path exists but a five-line SDK/CLI snippet —
  would have made it the default path instead of a fallback.

## Overall

The platform requirement (runtime call to Token Factory) was the easy part —
the API is genuinely drop-in. The two things that cost us time were both
discoverability: thinking-mode budgets and per-model regions. Both are
one-line doc fixes.
