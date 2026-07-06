# Multi-Agent Power Grid Balancer

A multi-agent system that balances electricity supply and demand across grid regions.
Region agents watch their own supply/demand, and a coordinator agent reroutes power
from surplus regions to regions facing shortages — preventing blackouts.

Built with **LangGraph** (agent orchestration) and **LangSmith** (observability),
using real hourly demand data from the U.S. Energy Information Administration (EIA).

---

## What it does

Each hour:
1. **Region agents** read their supply and demand, compute their gap, and report
   whether they are `short`, `ok`, or `surplus`.
2. A **coordinator agent** collects all reports and decides power transfers to
   cover shortages — serving the biggest shortage first.

Example output:
```
Region reports:
  A: ok (+0 MW)
  B: short (-200 MW)
  C: surplus (+300 MW)

Reroute plan:
  C -> B: 200 MW
```

---

## Architecture

```
                 START
                   |
        (fan-out, in parallel)
        /          |          \
   region_A    region_B    region_C     <- each labels itself short/ok/surplus
        \          |          /
        (fan-in, reports merge)
                   |
              coordinator                 <- LLM makes the judgment call
                   |
                  END
```

- **Fan-out / fan-in:** all region agents run in parallel, then their reports
  converge into the coordinator.
- **Region agents are plain code** (threshold logic) — no LLM needed for simple
  gap classification.
- **The coordinator uses an LLM** only for the genuine judgment call: matching
  shortages to surplus under conflict.

### Under the hood
- **State = channels + reducers.** Region reports are merged with an `operator.add`
  reducer so parallel writes append instead of overwriting.
- **Super-steps.** The graph runs in two steps: regions fire together (step 1),
  then the coordinator fires (step 2).
- **Structured output.** The coordinator forces the LLM to return a validated
  `Plan` object via tool-calling, so decisions are always well-formed.

---

## Evaluation (the interesting part)

The project includes an eval harness that scores the coordinator against an
answer key built from a simple, trusted rule. Test cases climb in difficulty:
**sanity check -> edge case -> judgment call.**

### An eval-driven fix
On first run, the LLM scored **2/3 (67%)**. The eval caught it **even-splitting
surplus** on the hardest case instead of following the priority rule (serve the
biggest shortage first):

```
judgment_call   FAIL   got=[('C','A',200),('C','B',200)]   want=[('C','A',100),('C','B',300)]
```

The fix was prompt engineering driven by the eval: I tightened the coordinator's
system prompt with an explicit priority procedure and a worked example showing
the exact failure labeled as wrong. Re-running the eval:

```
Accuracy: 3/3 = 100%
```

This measure -> diagnose -> fix -> re-measure loop is the core workflow, and the
harness is proven to catch failures (a do-nothing coordinator scores 0/3).

---

## Tech stack

- **LangGraph** — multi-agent orchestration (nodes, edges, state)
- **LangSmith** — tracing and observability
- **OpenAI** — the coordinator's reasoning (structured output)
- **EIA API** — real hourly U.S. electricity demand data
- **pandas** — data loading and ETL

---

## Project structure

```
power-grid-balancer/
├── main.py              # entry point: run one balancing cycle
├── fetch_data.py        # ETL: pull real EIA data -> tidy CSV
├── src/
│   ├── state.py         # shared state (channels + reducers)
│   ├── data_loader.py   # load clean numbers for one hour
│   ├── region_agent.py  # read -> gap -> status -> report
│   ├── coordinator.py   # the LLM judgment call
│   └── graph.py         # wire nodes + edges, compile
├── evals/
│   ├── test_cases.py    # test cases + answer key
│   └── run_eval.py      # run the exam, print the score
└── data/
    └── grid_sample.csv  # sample data (swap for real EIA data)
```

---

## Running it

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add your keys to a `.env` file:
   ```
   OPENAI_API_KEY=sk-...
   LANGSMITH_API_KEY=lsv2_...
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=power-grid-balancer
   ```

3. Run on the sample data:
   ```bash
   python main.py
   ```

4. Run the eval:
   ```bash
   python -m evals.run_eval
   ```

5. (Optional) Fetch real EIA data — get a free key at
   https://www.eia.gov/opendata/, add `EIA_API_KEY` to `.env`, then:
   ```bash
   python fetch_data.py
   ```
   and point `main.py` at `data/grid.csv`.

---

## Scaling: hierarchy of coordinators

The current version uses one coordinator over a flat set of regions. This scales
by making coordinators **hierarchical** — each region can itself be a coordinator
for smaller regions inside it (e.g. a county coordinates its cities, which
coordinate their neighborhoods).

Each level **balances locally first and escalates only the leftover shortage**
upward (the subsidiarity principle). This keeps every coordinator's decision small
no matter how many total regions exist — and mirrors how real power grids are
actually structured.

---

## Key design principles

- Establish the coordination model ("who's in charge?") up front.
- Don't use an LLM for what plain code does better — reserve it for judgment.
- Find the hardest decision early and test it the most.
- When no answer key exists, build one from a simple rule you trust.
- Match the metric to the shape of the decision.
- An eval you never watch fail is worthless.