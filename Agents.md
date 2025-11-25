````md
# Agentic Dashboard Builder

The project focuses on an **agentic backend** that takes a user-uploaded dataset and automatically builds a dashboard concept around it.  
The system:

1. Profiles and cleans the raw data in a **Daytona** Python sandbox,
2. Performs exploratory & statistical analysis,
3. Plans a dashboard (`dashboard.json` with KPIs, charts, filters, layout),
4. Hands the concept to a UI Dev agent,
5. Lets a QA agent define and (later) run checks against the built UI.

> **Scope:** This repo defines and wires all five agents (Orchestrator, Data Analysis, Planner, UI Dev, QA), but we implement them **agent by agent**, in small, isolated steps.

---

## Role

You are an expert **Agentic System Engineer** working with:

- **Google ADK** for multi-agent orchestration,
- **Daytona** as a persistent Python sandbox,
- **LiteLLM** to talk to OpenAI models,
- **OpenRouter** for a cheap summarizer model,
- **Phoenix** for observability and trace inspection.

You extend and maintain agent definitions, tools, and flows so they work reliably under **tight resources**:  
**1 vCPU / 1 GiB RAM / 3 GiB storage per run.**

---

## Development Setup

### Installation

```bash
# Python 3.13
pip install -r requirements.txt
```
````

### Development

```bash
# Start API / orchestrator (example)
python -m src.app.main
```

### Build

```bash
# Optional: build distribution
python -m build
```

### Tests

```bash
pytest
```

---

## Tech Stack

- **Orchestration:** Google ADK (Agentic Development Kit) https://google.github.io/adk-docs/
- **Language:** Python **3.13**
- **LLM Routing:** LiteLLM (OpenAI models as primary brain)
- **Summarizer:** Small OSS model via OpenRouter (for log/output compression)
- **Sandbox:** Daytona persistent Python workspace
- **Observability:** Phoenix (traces, spans, LLM/tool monitoring)

### Data Analysis Sandbox (Daytona)

Available Python packages for `run_python` inside the Data Analysis Agent’s sandbox:

- `numpy`
- `pandas`
- `polars`
- `pyarrow`
- `duckdb`
- `scipy`
- `scikit-learn`
- `python-dateutil`
- `matplotlib`
- `seaborn`

---

## Project Structure

```text
.
├── agents.md                      # This document
├── pyproject.toml / requirements.txt
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py                # Entrypoint (HTTP/CLI) to orchestrator flow
│   │
│   ├── core/
│   │   ├── config.py              # Env config, model names, limits
│   │   ├── state.py               # Shared ADK session state (run_id, paths, flags)
│   │   ├── daytona_client.py      # Client for interacting with Daytona workspace
│   │   ├── logging.py             # Logging helpers
│   │   └── phoenix_integration.py # Phoenix observability hooks
│   │
│   ├── flows/
│   │   ├── __init__.py
│   │   └── dashboard_flow.py      # Google ADK graph wiring all agents
│   │
│   ├── agents/
│   │   ├── orchestrator/
│   │   │   ├── __init__.py
│   │   │   └── orchestrator_agent.py  # Entry agent; coordinates others
│   │   │
│   │   ├── data_analysis/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # LLM agent using run_python + file tools
│   │   │   ├── prompts.py             # System prompts for EDA/cleaning
│   │   │   └── schemas.py             # DataProfile, CleaningSummary models
│   │   │
│   │   ├── planner/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # LLM agent that creates dashboard.json
│   │   │   ├── prompts.py             # Planning prompts
│   │   │   └── dashboard_schema.py    # Pydantic model for dashboard.json
│   │   │
│   │   ├── ui_dev/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # LLM agent; outputs UI spec for external app
│   │   │   └── prompts.py
│   │   │
│   │   └── qa/
│   │       ├── __init__.py
│   │       ├── agent.py               # LLM agent; proposes QA checks & scenarios
│   │       └── scenarios.py           # Reusable QA scenario templates
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── data_profile.py
│   │   ├── cleaning_summary.py
│   │   └── dashboard_concept.py      # Shared view of dashboard.json structure
│   │
│   └── tools/
│       ├── __init__.py
│       ├── llm_client.py             # LiteLLM + OpenRouter helpers
│       ├── filesystem.py             # Helpers to map Daytona paths <-> artifacts
│       └── resource_limits.py        # Helpers for chunking, sampling under 1 vCPU/1GiB
│
├── artifacts/
│   ├── sample_runs/                  # Exported copies of Daytona files for debugging
│   └── README.md                     # Clarifies artifacts/ is a mirror, not source of truth
│
└── tests/
    ├── test_flows_dashboard.py       # End-to-end tests of dashboard_flow
    ├── agents/
    │   ├── test_data_analysis_agent.py
    │   ├── test_planner_agent.py
    │   └── test_orchestrator_agent.py
    └── fixtures/
        └── sample_datasets/          # Small CSV/Parquet for tests
```

> **Important:**
> Runtime workspaces live in **Daytona**, not in this repo.
> `artifacts/` only contains exported snapshots for debugging and reference.

---

## Agent Responsibilities

### Orchestrator Agent

- **Role:** Entry point and conductor.
- **Tasks:**

  - Receives the dataset reference (upload ID/path) + optional user goals.
  - Creates a **run_id** and initial shared state.
  - Orchestrates calls to:

    - Data Analysis Agent (profiling & cleaning),
    - Planner Agent (dashboard.json),
    - UI Dev Agent (UI spec),
    - QA Agent (test scenarios).

  - Writes high-level run summary and paths into shared state.

---

### Data Analysis Agent (LLM + Daytona Tools)

- **Role:** Data profiler, cleaner, and statistical workhorse.

- **Tools available:**

  - `run_python`
    Execute arbitrary Python in the Daytona sandbox, with access to:

    - numpy, pandas, polars, pyarrow, duckdb,
    - scipy, scikit-learn,
    - python-dateutil, matplotlib, seaborn.

  - `inspect_files`
    List/read files in the Daytona workspace (e.g. datasets, scripts, reports).
  - `write_data_profile`
    Persist a structured **DataProfile** artifact (and optionally link to a Markdown report).
  - `write_cleaning_summary`
    Persist a structured **CleaningSummary** artifact (what changed, why, and pointers to cleaned data).

- **Typical workflow:**

  1. Use `run_python` to explore schema, types, missing values, distributions.
  2. Use `run_python` to clean data and write a **cleaned dataset** to a stable path.
  3. Use `run_python` for deeper analysis (correlations, simple regressions, clustering) **as needed**.
  4. Use `write_cleaning_summary` and `write_data_profile` to record:

     - Where the cleaned data is,
     - What the main characteristics and quality issues are,
     - Any extra analysis artifacts (e.g. regression results) with file paths.

  5. Update shared session state with file pointers (no raw data in LLM messages).

> **Key principle:**
> All **heavy numeric work** (including regression, clustering, key figures) lives here via `run_python`.
> The Planner can **request** further analysis, but never runs Python itself.

---

### Planner Agent

- **Role:** Dashboard architect.

- **Inputs:**

  - Shared state:

    - Path to **cleaned dataset** (Daytona),
    - `DataProfile` and `CleaningSummary`,
    - Optional extra analysis files (regressions, clusters, metrics).

  - High-level user goals (e.g. “sales overview”, “operations monitoring”).

- **Outputs:**

  - `dashboard.json` describing:

    - `goal`
    - `kpis[]` (name, formula, explanation)
    - `charts[]` (type, x/y, breakdown, source fields)
    - `filters[]` (fields, default ranges)
    - `layout` (sections, priorities)
    - `assumptions` / `limitations` (derived from data quality & analysis)

- **Behavior:**

  - Never runs Python or touches raw data directly.
  - Uses file paths + summaries from the Data Analysis Agent.
  - If more analysis is needed, it instructs the **Orchestrator** to call the Data Analysis Agent again with a more specific task.

---

### UI Dev Agent

- **Role:** Bridge from `dashboard.json` to a concrete **UI implementation plan**.
- **Outputs:**

  - UI spec artifacts (e.g. `ui_spec.md`, `component_plan.json`) that an external Next.js/React project can consume.

- **Behavior:**

  - Consumes `dashboard.json`.
  - Proposes components, data flows, and `data-testid` conventions to support QA.
  - No actual frontend code execution happens in this repo; this is a **planning agent**.

---

### QA Agent

- **Role:** Quality planner for dashboards.
- **Outputs:**

  - QA scenario definitions (e.g. `qa_scenarios.json`), with:

    - Filters to apply,
    - Expected KPI changes,
    - Simple sanity checks (totals, monotonicity, etc.).

- **Future:** Integrate with browser automation to run scenarios against a real UI.
- **For now:** Only generates test plans and expected behaviors.

---

## Design Standards

- **Separation of Concerns**

  - **Data Analysis Agent** = all data manipulation & numeric computation via `run_python`.
  - **Planner Agent** = semantic reasoning & dashboard design using outputs and file pointers.
  - **UI Dev & QA** = downstream consumers; they never mutate data.

- **Daytona as Source of Truth**

  - All datasets, reports, and artifacts live in the **Daytona workspace**.
  - The repo only sees **exported copies** in `artifacts/` for debugging.

- **Shared Session State (Google ADK)**

  - Use a single shared state object per run, including:

    - `run_id`
    - `daytona_workspace_root`
    - `paths` (dict of logical names → Daytona paths)
    - `flags` (which agents have completed)
    - `summary` (short textual run summary)

- **Token & Resource Discipline**

  - 1 vCPU / 1 GiB RAM / 3 GiB storage means:

    - Prefer **sampling** and **chunked processing** on very large datasets.
    - Avoid huge joins or full in-memory copies when not needed.
    - Use the OpenRouter summarizer to compress verbose logs / EDA outputs before feeding them to other agents.
    - Keep `run_python` scripts focused and small; reuse helper modules instead of redoing heavy work.

- **Agent-by-Agent Implementation**

  - Each agent has its own folder and can be implemented, tested, and iterated on independently.
  - No "big bang" implementation: we gradually grow each agent’s capabilities while preserving stable interfaces (artifacts + shared state).

---

## Common Pitfalls to Avoid

- **DON’T** send full datasets or massive logs through LLM messages.

- **DON’T** let the Planner Agent run any Python or touch raw data directly.

- **DON’T** write to local `artifacts/` from agents; they should only write to Daytona.

- **DO**:

  - Write all heavy outputs to Daytona and pass **paths** via shared state.
  - Summarize large outputs via OpenRouter before feeding them into other LLM calls.
  - Keep `run_python` scripts under control: measure runtime, memory, and file sizes.
  - Reuse analysis results instead of recomputing (e.g. store regression outputs and link them in the DataProfile).

---

## Resource & Performance Considerations

Given **1 vCPU / 1 GiB RAM / 3 GiB storage**:

- Prefer **column pruning** and **row sampling** for first-pass EDA.
- Use **DuckDB/polars** where appropriate to avoid loading everything into pandas at once.
- Persist intermediate results and avoid in-memory chains of huge transformations.
- Use `matplotlib`/`seaborn` sparingly; store plots as files in Daytona and only summarize them textually for LLMs.
- Implement guardrails in `resource_limits.py` (e.g. max rows to load, max file size threshold, timeout hints for `run_python`).

---

## Additional Resources

- **Google ADK docs** – agent and flow definitions
- **Phoenix** – observability and tracing patterns
- **Daytona** – workspace and sandbox documentation
- **LiteLLM** – configuration for OpenAI routing
- **OpenRouter** – model selection for the summarizer

> For local testing, use the small example datasets under `tests/fixtures/sample_datasets/` and inspect exported artifacts in `artifacts/sample_runs/` to see how agents interact via Daytona and shared state.
