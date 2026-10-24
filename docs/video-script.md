# Video script — Receipts demo (target 2:45, hard cap 3:00)

Record at 1440p or 1080p, browser fullscreen, zoom 125%. Use the
**prepared run `85269d0858e8`** (Chroma MEASURED) for the result scenes and a
**live fresh run** for the trace scene — or use the recorded run's trace
replay if a live run is too slow. Voiceover optional but recommended;
captions must carry the story either way.

## Shots

| # | Time | Shot | VO / caption |
|---|------|------|--------------|
| 1 | 0:00–0:10 | Landing page, title card | "Receipts — a due-diligence agent. Claims in, verdicts out." |
| 2 | 0:10–0:25 | Paste brief (incumbent + named candidates), hit run | "Describe the purchase. It can name candidates and an incumbent." |
| 3 | 0:25–0:45 | Requirements editor appears — edit one weight, confirm | "It pauses for your weighted requirements — human in the loop before it spends your API budget." |
| 4 | 0:45–1:15 | Live trace stream — point at actor badges (U / nano / tavily / check) | "Watch it plan and verify — Nemotron Ultra reasons, Nano extracts, Tavily gathers, checks measure." |
| 5 | 1:15–1:35 | Open Chroma's MEASURED claim → evidence drawer shows real bench numbers | "It actually ran the product — real p50/p99 from a 20k-vector benchmark." |
| 6 | 1:35–1:50 | Open a CONTRADICTED claim (Pinecone 99.95% SLA vs observed uptime) | "And it catches marketing that isn't true — Pinecone's SLA versus its real incident history." |
| 7 | 1:50–2:05 | Coverage grid + verdict filters (click 'contradicted') | "Every cell traceable to evidence." |
| 8 | 2:05–2:20 | Outreach draft scroll | "It drafts the pointed questions to send the finalists." |
| 9 | 2:20–2:35 | Paste fake vendor reply → ingest → claim flips verdict | "Vendor replies re-verify the ledger — the audit stays alive." |
| 10 | 2:35–2:45 | Telemetry strip + watch button + end card | "35 model calls, six cents. Then it keeps watching after you buy." |

## Prep checklist before recording

- [ ] Server + tunnel running, URL loads cold
- [ ] Recent-runs list trimmed to good runs (optional: fresh receipts.db + 1 staged run)
- [ ] The staged reply text in clipboard: `"Chroma's free tier is permanent — here's the docs link and a quote from our CTO confirming no credit card is required."`
- [ ] Browser: hide bookmarks bar, close other tabs, dark OS theme
- [ ] QuickTime screen recording (Cmd+Shift+5) at 1080p+

## Fallback if live run is flaky

Screen-record the completed run `85269d0858e8` — trace pane still replays
stage-by-stage history, all evidence intact.
