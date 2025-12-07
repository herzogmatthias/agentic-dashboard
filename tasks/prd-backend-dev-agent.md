# PRD: Backend Dev Agent

## Overview

The **Backend Dev Agent** is a specialized LLM agent within the Backend Dev Team that transforms `PlannerArtifactTodo` items into concrete backend code. It receives a single artifact assignment, creates the necessary files (API routes, models, helpers), validates its work, and emits a structured `DevReport`.

**Location:** `src/agents/backend_dev_team/dev/`

**Goal:** Replace the existing `src/agents/backend/` agent with a cleaner, Loop-integrated design. Code reuse from the old agent is encouraged, but the end goal is full deprecation of `src/agents/backend/`.

---

## Problem Statement

The current backend agent (`src/agents/backend/agent.py`) was designed for standalone operation, outputting a monolithic `BackendManifest`. This creates several issues:

1. **Tight Coupling**: The agent writes the manifest directly, mixing code generation with documentation concerns
2. **No Artifact Isolation**: No clear contract for processing individual artifacts from the Planner
3. **Loop Incompatibility**: Cannot integrate cleanly with the Backend Dev Team's Loop Agent workflow
4. **No Incremental Reporting**: No structured output per artifact for Tester/QA agents to consume

The new Backend Dev Agent addresses these by:

- Processing **one artifact at a time** with clear I/O contracts
- Emitting **structured DevReports** that can be aggregated later
- Integrating seamlessly with the **BackendDevLoopAgent** workflow

---

## Goals

1. **Single Artifact Focus**: Process one `PlannerArtifactTodo` per invocation
2. **Structured Output**: Emit `BackendDevResult` containing a `DevReport`
3. **Code Quality**: Run lint/type-check validation before completing
4. **Reusability**: Leverage existing tools from `src/agents/backend/` (create_api, create_model, etc.)
5. **Deprecation Path**: Design as drop-in replacement, enabling deprecation of old backend agent

---

## Non-Goals

- **Manifest Generation**: The Backend Manifest is built deterministically by a separate process from DevReports
- **Multi-Artifact Processing**: Each invocation handles exactly one artifact
- **Test Execution**: Testing is handled by the Tester Agent in the Loop
- **QA Validation**: QA checks are handled by the QA Agent in the Loop

---

## Architecture

### Agent Location

```
src/agents/backend_dev_team/
├── __init__.py
├── planner/           # Backend Planner Agent (existing)
├── loop/              # BackendDevLoopAgent (existing)
└── dev/               # NEW: Backend Dev Agent
    ├── __init__.py
    ├── agent.py       # Main agent definition
    ├── prompts.py     # System prompts
    ├── schemas.py     # I/O schemas (BackendDevInput, BackendDevResult, DevReport)
    ├── tools.py       # Agent-specific tools (reuse + create_helper)
    └── callbacks.py   # State injection callbacks
```

### Input/Output Contract

#### Input: `BackendDevInput`

```python
from pydantic import BaseModel
from typing import Optional, List
from src.agents.backend_dev_team.planner.schemas import PlannerArtifactTodo

class BackendDevInput(BaseModel):
    """Input contract for Backend Dev Agent."""

    run_id: str
    """Unique identifier for this pipeline run."""

    artifact: PlannerArtifactTodo
    """The artifact to implement (from Backend Planner)."""

    workspace_root: str
    """Absolute path to the sample-dashboard project."""

    previous_summaries: Optional[List[str]] = None
    """Condensed DevReport summaries from prior artifacts in this run.
    Helps agent understand what's already been created."""
```

#### Output: `BackendDevResult`

```python
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class FileChange(BaseModel):
    """Record of a file created or modified."""

    path: str
    """Relative path from workspace_root (e.g., 'src/app/api/sales/route.ts')."""

    action: Literal["created", "modified"]
    """Whether the file was newly created or modified."""

    description: str
    """Brief description of what this file does."""

class DevReport(BaseModel):
    """Structured report of work done on a single artifact."""

    artifact_id: str
    """ID of the artifact that was implemented."""

    artifact_type: Literal["route", "helper"]
    """Type of artifact."""

    status: Literal["success", "partial", "failed"]
    """Overall status of the implementation."""

    summary: str
    """Human-readable summary of what was done (2-3 sentences)."""

    files_changed: List[FileChange]
    """List of files created or modified."""

    dependencies: List[str]
    """Other artifact IDs this implementation depends on."""

    lint_passed: bool
    """Whether lint validation passed for created files."""

    type_check_passed: bool
    """Whether type-check validation passed for created files."""

    errors: Optional[List[str]] = None
    """Error messages if status is 'partial' or 'failed'."""

    timestamp: datetime
    """When this report was generated."""

class BackendDevResult(BaseModel):
    """Output contract for Backend Dev Agent."""

    status: Literal["success", "partial", "failed"]
    """Overall status of the dev work."""

    summary: str
    """Brief summary for the Loop Agent."""

    report: DevReport
    """Detailed structured report."""
```

### DevReport Storage

DevReports are stored at:

```
{workspace_root}/artifacts/backend/dev/<artifact_id>.dev_report.json
```

Example: `sample-dashboard/artifacts/backend/dev/sales-summary-route.dev_report.json`

---

## Tools

### Reused from `src/agents/backend/`

| Tool                        | Purpose                              |
| --------------------------- | ------------------------------------ |
| `get_sample_rows_tool`      | Sample CSV rows for schema discovery |
| `inspect_json_preview_tool` | Preview JSON file structure          |
| `create_api_tool`           | Create new API route with validation |
| `create_model_tool`         | Create TypeScript model              |
| `search_content_tool`       | Search codebase for patterns         |
| `run_lint_tool`             | Execute npm lint                     |
| `run_type_check_tool`       | Execute TypeScript type-check        |
| MCP filesystem toolset      | Read/write/edit files                |

### New Tool: `create_helper_tool`

```python
def create_helper_tool(name: str, content: str) -> str:
    """
    Create a helper/utility file at src/lib/{name}.ts

    Args:
        name: Helper name (e.g., 'data_utils', 'formatters', 'aggregations')
        content: TypeScript content for the helper

    Returns:
        Success message with created file path, or error message.

    Behavior:
        1. Validates TypeScript syntax
        2. Creates src/lib/{name}.ts
        3. Returns confirmation
    """
```

### Removed Tool

| Tool                          | Reason                                                            |
| ----------------------------- | ----------------------------------------------------------------- |
| `write_backend_manifest_tool` | Manifest is built deterministically from DevReports, not by agent |

### New Tool: `write_dev_report_tool`

```python
def write_dev_report_tool(report: DevReport) -> str:
    """
    Persist the DevReport to the artifacts directory.

    Args:
        report: The completed DevReport

    Returns:
        Path where report was written.

    Behavior:
        1. Serializes DevReport to JSON
        2. Writes to {workspace_root}/artifacts/backend/dev/{artifact_id}.dev_report.json
        3. Returns confirmation with path
    """
```

---

## Agent Definition

### Model & Planner

```python
from google.adk.agents import LlmAgent
from google.adk.planners import PlanReActPlanner

backend_dev_agent = LlmAgent(
    name="backend_dev_agent",
    model="xai/grok-code-fast-1",  # Reuse same model as old backend agent
    planner=PlanReActPlanner(),    # Structured multi-step reasoning
    instruction=backend_dev_prompt,
    tools=[
        get_sample_rows_tool,
        inspect_json_preview_tool,
        create_api_tool,
        create_model_tool,
        create_helper_tool,        # NEW
        search_content_tool,
        run_lint_tool,
        run_type_check_tool,
        write_dev_report_tool,     # NEW (replaces write_backend_manifest)
        *create_filesystem_toolset(),
    ],
    output_schema=BackendDevResult,
)
```

### System Prompt Key Points

The system prompt should:

1. **Explain the single-artifact focus**: "You receive ONE artifact to implement"
2. **Reference injected context**: Dashboard concept, data profile, previous summaries
3. **Enforce TypeScript rules**: No `any`, explicit types, proper generics
4. **Define the workflow**:
   - Understand the artifact requirements
   - Check what already exists (via previous_summaries and filesystem)
   - Create necessary files (API route, model, helper)
   - Validate with lint/type-check
   - Write the DevReport
5. **Output requirement**: Must call `write_dev_report_tool` before completing

---

## Workflow Integration

### Loop Agent Integration

The `BackendDevLoopAgent` (in `src/agents/backend_dev_team/loop/agent.py`) orchestrates:

```
Planner → Loop → [Dev → Tester → QA] → Loop → Planner
```

The Loop Agent:

1. Receives artifacts from the Planner
2. Calls Backend Dev Agent for each artifact
3. Passes `DevReport` to Tester Agent
4. Routes back to Dev Agent if tests fail
5. Returns aggregated results to Planner

### State Flow

```python
# Loop Agent prepares input for Dev Agent
dev_input = BackendDevInput(
    run_id=state["run_id"],
    artifact=current_artifact,
    workspace_root=state["workspace_root"],
    previous_summaries=state.get("completed_summaries", []),
)

# Dev Agent returns structured result
dev_result: BackendDevResult = await backend_dev_agent.run(dev_input)

# Loop Agent stores summary for next artifact
state["completed_summaries"].append(dev_result.summary)
```

---

## Migration Path

### Phase 1: Parallel Operation

- New agent lives at `src/agents/backend_dev_team/dev/`
- Old agent remains at `src/agents/backend/`
- Loop Agent uses new agent; standalone flows can use old agent

### Phase 2: Deprecation Warnings

- Add deprecation warnings to old agent
- Update any standalone flows to use new agent

### Phase 3: Removal

- Delete `src/agents/backend/` directory
- Update imports across codebase

---

## Success Criteria

1. **Functional**: Agent successfully creates API routes, models, and helpers for given artifacts
2. **Validated**: All created files pass lint and type-check
3. **Structured Output**: DevReport contains accurate file changes and status
4. **Integrated**: Works seamlessly with BackendDevLoopAgent
5. **Reusable**: Tools from old agent work without modification

---

## Implementation Tasks

### Task 1: Create Folder Structure

- Create `src/agents/backend_dev_team/dev/` directory
- Create `__init__.py`, `agent.py`, `prompts.py`, `schemas.py`, `tools.py`, `callbacks.py`

### Task 2: Define I/O Schemas

- Implement `BackendDevInput`, `BackendDevResult`, `DevReport`, `FileChange` in `schemas.py`

### Task 3: Implement Tools

- Create `create_helper_tool` function
- Create `write_dev_report_tool` function
- Set up tool imports from `src/agents/backend/` for reused tools

### Task 4: Build System Prompt

- Adapt prompt from `src/agents/backend/prompts.py`
- Focus on single-artifact workflow
- Add DevReport output requirement

### Task 5: Create Agent Definition

- Define `backend_dev_agent` with all tools
- Set up callbacks for context injection
- Configure `output_schema=BackendDevResult`

### Task 6: Integration with Loop Agent

- Update `create_dev_agent()` factory in Loop Agent to use new agent
- Ensure state passing aligns with `BackendDevInput`

### Task 7: Unit Tests

- Test schema validation
- Test tool functions
- Mock agent responses

---

## Resolved Questions

1. **Helper Naming Convention**: Use **semantic names** (e.g., `data_utils.ts`, `formatters.ts`, `aggregations.ts`) rather than artifact-based naming.

2. **Report Aggregation**: The **deterministic manifest builder is triggered after the Loop finishes** processing all artifacts. The Loop Agent (or Planner upon receiving Loop results) invokes the builder.

3. **Error Recovery**: Depends on failure type:
   - **Complexity issues** (artifact too complex, unclear requirements): Surface to user with partial DevReport (`status: "failed"`, `errors` populated)
   - **Technical issues** (transient errors, tool failures): Retry within the Loop before failing
   - The Loop Agent handles retry logic; Dev Agent always writes a DevReport reflecting actual status

---

## References

- [Backend Dev Team PRD](./prd-backend-dev-team.md)
- [Existing Backend Agent](../src/agents/backend/agent.py)
- [Loop Agent Implementation](../src/agents/backend_dev_team/loop/agent.py)
- [PlannerArtifactTodo Schema](../src/agents/backend_dev_team/planner/schemas.py)
