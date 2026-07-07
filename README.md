# Multi-Agent Power Grid Balancer

A hierarchical multi-agent system that balances electricity supply and demand
across the US power grid. Individual grid operators report their supply/demand,
regional coordinators balance locally, and a national coordinator resolves what's
left — mirroring how the real grid is structured.

Built with **LangGraph** (orchestration) and **LangSmith** (observability), using
real hourly data from the U.S. Energy Information Administration (EIA), and
**validated against real grid interchange data**.

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

Two layers of evals:

**1. Rule-based harness** (`evals/run_eval.py`) — scores the coordinator against an
answer key built from a trusted priority rule. Test cases climb in difficulty:
sanity check → edge case → judgment call.

An eval-driven fix: the LLM first scored **67%**, caught even-splitting surplus
instead of prioritizing the biggest shortage. Tightening the prompt with an explicit
procedure and a worked example took it to **100%**. The harness is proven to catch
failures (a do-nothing coordinator scores 0%).

**2. Ground-truth eval** (`evals/ground_truth_eval.py`) — scores the agent's
regional residuals against **real EIA interchange data** (what actually happened):
85% direction accuracy, 0.82 correlation.

---

## Production API

The balancer is exposed as a FastAPI service (`api.py`):

- `GET /balance/{timestamp}` — returns the full plan (local transfers, residuals,
  national transfers) as JSON.
- `GET /health` — liveness check.
- **In-memory caching** — identical requests skip the LLM call and return instantly.
  (Swap for Redis in real production; the check-compute-store pattern is identical.)

Run: `uvicorn api:app --reload`, then open `http://localhost:8000/docs`.

---

## Tech stack

- **LangGraph** — multi-agent orchestration
- **LangSmith** — tracing and observability
- **OpenAI** — the national coordinator's reasoning (structured output)
- **FastAPI** — the production API layer
- **EIA API** — real hourly demand, generation, and interchange data
- **pandas** — data loading and ETL

---

## Project structure

```
power-grid-balancer/
├── api.py                    # FastAPI service (with caching)
├── main.py                   # flat balancer entry point
├── main_hierarchy.py         # hierarchical balancer entry point
├── fetch_data.py             # ETL: demand + generation, all regions, a month
├── fetch_interchange.py      # ETL: real interchange (ground truth)
├── src/
│   ├── state.py              # shared state (channels + reducers)
│   ├── data_loader.py        # load clean numbers; filter aggregates
│   ├── region_agent.py       # read -> gap -> status -> report
│   ├── coordinator.py        # flat LLM coordinator (top-N cap, validation)
│   ├── graph.py              # dynamic fan-out/fan-in graph
│   ├── regions.py            # operator -> region mapping (hierarchy backbone)
│   ├── local_coordinator.py  # balance within a region, return residual
│   ├── national_coordinator.py # match regional residuals (the LLM call)
│   └── hierarchy.py          # orchestrator: local -> regional -> national
├── evals/
│   ├── test_cases.py         # rule-based test cases + answer key
│   ├── run_eval.py           # rule-based scoring harness
│   └── ground_truth_eval.py  # score vs real interchange data
└── data/                     # generated CSVs (gitignored)
```

---

## Running it

1. Install: `pip install -r requirements.txt`
2. Add keys to `.env`: `OPENAI_API_KEY`, `EIA_API_KEY`, `LANGSMITH_API_KEY`,
   `LANGSMITH_TRACING=true`
3. Fetch real data: `python fetch_data.py` and `python fetch_interchange.py`
4. Run the hierarchy: `python main_hierarchy.py`
5. Score against ground truth: `python -m evals.ground_truth_eval`
6. Serve the API: `uvicorn api:app --reload`

---

## Future work

- **Region adjacency** at the national level — restrict inter-region transfers to
  geographic neighbors (fixes the remaining long-distance residual match).
- **Redis caching** for a shared, persistent cache across server instances.
- **Multi-hour evaluation** — run the ground-truth eval across the full month to
  measure consistency, not just a single hour.
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