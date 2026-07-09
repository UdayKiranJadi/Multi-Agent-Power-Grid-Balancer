# Multi-Agent Power Grid Balancer

A hierarchical multi-agent system that balances electricity supply and demand
across the US power grid. Individual grid operators report their supply/demand,
regional coordinators balance locally, and a national coordinator resolves what's
left — mirroring how the real grid is structured.

Built with **LangGraph** (orchestration) and **LangSmith** (observability), using
**live** hourly data from the U.S. Energy Information Administration (EIA), and
**validated against real grid interchange data**.

**[Live demo →](https://multi-agent-power-grid-balancer.vercel.app)** — an
interactive US map: scrub to any hour, or hit **Go Live** to follow the latest
published grid data.

---

## Headline result

Scored against what the US grid **actually did** (real EIA interchange data), the
agent achieves:

- **85% direction accuracy** — correctly identifies whether each region imports or
  exports power (11 of 13 regions)
- **0.82 magnitude correlation** — predicted net flows closely track reality

The two misses are hydro-heavy regions (e.g. the Northwest), where an instantaneous
`generation − demand` snapshot understates dispatchable hydro and storage — a
domain-level limitation, not a code bug.

---

## Architecture: a hierarchy of coordinators

Power flows **local → regional → national**, the way real transmission does:

```
                       national coordinator          <- LLM: match regional residuals
                      /          |          \
                   CAL          NW          MIDA      <- regional coordinators (local balancing)
                  /   \        /   \          |
              CISO   BANC   BPAT  PACW       PJM       <- individual operators (leaves)
```

1. **Operators** report their gap (`supply − demand`).
2. **Regional coordinators** balance operators *within* a region (neighbors trade),
   then escalate only the **leftover residual** upward (the subsidiarity principle).
3. The **national coordinator** matches the ~13 regional residuals with one LLM call.

This solves the scaling and topology problems of a flat design: most power moves
locally between neighbors, and the national level only ever sees 13 net numbers.

### Under the hood
- **State = channels + reducers.** Operator reports merge via an `operator.add`
  reducer so parallel writes append instead of overwriting.
- **Super-steps.** The region agents fire together (step 1), then coordination runs.
- **Structured output.** The national LLM call is constrained to a validated
  `Plan` schema via tool-calling.
- **Validation layer.** Plain-code checks reject invalid transfers (self-transfers,
  zero amounts, non-existent surplus) — the LLM reasons, code guarantees correctness.
- **Traced end-to-end.** `@traceable` wraps the hierarchy (local → national →
  routing), so a LangSmith trace shows the whole tree — not just the raw LLM call.

---

## Scale

Runs on **all ~67 real balancing authorities** across a **full month** of hourly
EIA data (~50,000 rows). Key engineering:

- **Pagination** through the EIA API (5,000-row cap per request).
- **Data cleaning** — drops missing values and filters aggregate regions to avoid
  double-counting.
- **Dynamic graph** — builds a node per region from the data, not a hardcoded list.
- **Bounded LLM input** — the coordinator sorts by magnitude and caps to the top-N
  most significant regions, so cost and reliability stay constant at any scale.

---

## Evaluation

Evals at every layer — cheap deterministic checks, LLM-decision scoring in
LangSmith, and validation against reality.

**Rule-based harness** (`evals/run_eval.py`) — scores a coordinator against an
answer key built from a trusted priority rule. Cases climb in difficulty: sanity
check → edge case → judgment call. An eval-driven fix: the LLM first scored
**67%**, caught even-splitting surplus instead of prioritizing the biggest
shortage; tightening the prompt with an explicit procedure and a worked example
took it to **100%**. The harness is proven to catch failures (a do-nothing
coordinator scores 0%).

**LangSmith eval** (`evals/langsmith_eval.py`) — scores the *production* national
coordinator (`match_residuals`) against a **versioned LangSmith dataset** of real
region cases via `langsmith.evaluate()`, so runs become comparable **experiments**
in the UI. Four evaluators, property-based rather than brittle exact-match:

- `exact_match` — did it produce the expected matches?
- `no_invalid_transfers` — distinct regions, positive amount, real surplus → real short.
- `respects_surplus` — no region sends more than it has.
- `covers_biggest_first` — the biggest shortage is covered before smaller ones (no even-splitting).

With no `LANGSMITH_API_KEY`, the same evaluators run locally and print a table —
so it works in CI with no upload.

**Ground-truth eval** (`evals/ground_truth_eval.py`) — scores the agent's regional
residuals against **real EIA interchange data** (what actually happened) for one
hour: **85% direction accuracy, 0.82 correlation**.

**Multi-hour eval** (`evals/multi_hour_eval.py`) — the same comparison batched over
the **whole month**. No LLM (residuals come from local balancing), so it's fast and
free; reports overall direction accuracy and per-region correlation.

**Calibrated eval** (`evals/calibrated_eval.py`) — learns a per-region bias offset
on a training split and *keeps it only if it helps* (guarded), then proves the
correction on a held-out test set — targeting the hydro-region bias.

---

## Production API

The balancer is exposed as a FastAPI service (`api.py`):

- `GET /balance/{timestamp}` — returns the full plan (local transfers, residuals,
  national transfers) as JSON.
- `GET /latest` — the most recent hour that can be served (drives the "Go Live" button).
- `GET /health` — liveness check (reports whether live data is available).
- **Live data.** Each hour is fetched **on demand from the EIA API** (`src/eia_client.py`),
  so any hour from EIA's history through the latest published one is queryable — not a
  frozen snapshot. Falls back to the static CSV if no `EIA_API_KEY` is set.
- **In-memory caching** — a given hour is computed once (one EIA call + one LLM call),
  then served instantly. (Swap for Redis in real production; the check-compute-store
  pattern is identical.)

Run: `uvicorn api:app --reload`, then open `http://localhost:8000/docs`.
(Set `EIA_API_KEY` for live data; the frontend points at the backend via `VITE_API_URL`.)

---

## Tech stack

- **LangGraph** — multi-agent orchestration
- **LangSmith** — tracing (`@traceable` over the full hierarchy) + dataset-driven evals
- **OpenAI** — the national coordinator's reasoning (structured output)
- **FastAPI** — the production API layer
- **EIA API** — real hourly demand, generation, and interchange data
- **pandas** — data loading and ETL

---

## Project structure

```
power-grid-balancer/
├── backend/
│   ├── api.py                      # FastAPI service (with caching)
│   ├── main.py                     # flat balancer entry point
│   ├── main_hierarchy.py           # hierarchical balancer entry point
│   ├── fetch_data.py               # ETL: demand + generation, all regions, a month
│   ├── fetch_interchange.py        # ETL: real interchange (ground truth)
│   ├── .env.example                # copy to .env and fill in keys
│   ├── src/
│   │   ├── state.py                # shared state (channels + reducers)
│   │   ├── data_loader.py          # load clean numbers; filter aggregates
│   │   ├── eia_client.py           # live EIA fetch: one hour on demand + latest hour
│   │   ├── region_agent.py         # read -> gap -> status -> report
│   │   ├── coordinator.py          # flat LLM coordinator (legacy; used by run_eval)
│   │   ├── graph.py                # dynamic fan-out/fan-in graph
│   │   ├── regions.py              # operator -> region map + grid topology
│   │   ├── routing.py              # multi-hop BFS over region adjacency
│   │   ├── local_coordinator.py    # balance within a region, return residual
│   │   ├── national_coordinator.py # match residuals (LLM) + multi-hop routing
│   │   └── hierarchy.py            # orchestrator: local -> regional -> national
│   ├── evals/
│   │   ├── test_cases.py           # rule-based cases (flat + national)
│   │   ├── run_eval.py             # rule-based harness (flat coordinator)
│   │   ├── langsmith_eval.py       # dataset + evaluate() on the national coordinator
│   │   ├── ground_truth_eval.py    # one hour vs real interchange
│   │   ├── multi_hour_eval.py      # whole month: direction + per-region correlation
│   │   └── calibrated_eval.py      # guarded per-region bias correction
│   └── data/                       # generated CSVs (gitignored; sample is checked in)
└── power-grid-dashboard/           # React + Vite map dashboard (frontend)
```

---

## Running it

1. Install: `cd backend && pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY`, `EIA_API_KEY`,
   `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`
3. (optional) Fetch a static dataset for the evals / offline fallback:
   `python fetch_data.py` and `python fetch_interchange.py` — the live API fetches
   on demand, so this is only needed for the eval scripts below.
4. Run the hierarchy: `python main_hierarchy.py`
5. Score the national coordinator: `python -m evals.langsmith_eval`
   (uploads a LangSmith experiment; prints a local table if no LangSmith key)
6. Score against ground truth: `python -m evals.ground_truth_eval`
7. Serve the API: `uvicorn api:app --reload` (live data needs `EIA_API_KEY`)
8. Run the dashboard against your local API:
   `cd ../power-grid-dashboard && npm install && VITE_API_URL=http://localhost:8000 npm run dev`

---

## Future work

- **Region adjacency** at the national level — restrict inter-region transfers to
  geographic neighbors (fixes the remaining long-distance residual match).
- **Redis caching** for a shared, persistent cache across server instances.
- **LLM-as-judge evaluators** — add a reasoning-quality judge in LangSmith
  alongside the property-based checks.
- **Storage/hydro modeling** — improve accuracy in hydro-dominated regions.

---

## Key design principles

- Establish the coordination model ("who's in charge?") up front.
- Don't use an LLM for what plain code does better — reserve it for judgment.
- Solve locally, escalate only the leftover (subsidiarity).
- Bound the LLM's input so cost stays constant as the system scales.
- The LLM reasons; plain-code validation guarantees correctness.
- Build an answer key from a trusted rule, then validate against real ground truth.
- An eval you never watch fail is worthless.