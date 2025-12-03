# Tasks: Dev Orchestrator & Backend Agent

## Relevant Files

### New Files to Create

- `src/agents/dev_orchestrator/__init__.py` - Package init for Dev Orchestrator
- `src/agents/dev_orchestrator/agent.py` - Dev Orchestrator LlmAgent coordinating Backend, Frontend, QA agents
- `src/agents/dev_orchestrator/prompts.py` - System prompts for Dev Orchestrator

- `src/agents/backend/__init__.py` - Package init for Backend Agent
- `src/agents/backend/agent.py` - Backend Agent LlmAgent for creating API routes
- `src/agents/backend/prompts.py` - System prompts for backend development tasks

- `src/models/backend_manifest.py` - BackendManifest and related Pydantic models

- `src/tools/backend/__init__.py` - Package init for backend tools
- `src/tools/backend/filesystem.py` - `search_content` (scoped search; read/write via MCP filesystem server)
- `src/tools/backend/creation.py` - `create_api`, `create_model` (domain-specific creation with validation)
- `src/tools/backend/validation.py` - `run_lint`, `run_build`
- `src/tools/backend/data_access.py` - `get_sample_rows`, `read_data_profile`, `read_dashboard_concept`, `copy_data_to_project`
- `src/tools/backend/manifest.py` - `write_backend_manifest`
- `src/tools/backend/nextjs_docs.py` - `nextjs_init`, `nextjs_docs` (MCP server wrapper)

### Existing Files to Modify

- `src/agents/manager/agent.py` - Add Dev Orchestrator as sub-agent after Planner
- `src/prompts/system_prompts.py` - Add prompts for Dev Orchestrator and Backend Agent (or reference new prompt files)

### Test Files

- `tests/agents/test_dev_orchestrator.py` - Unit tests for Dev Orchestrator
- `tests/agents/test_backend_agent.py` - Unit tests for Backend Agent
- `tests/tools/test_backend_tools.py` - Unit tests for backend tools (patching, creation, validation)

### External Dependencies

- Next.js sample project: `C:\Users\darks\Documents\agentic-dashboard\sample-dashboard\`
- Next.js DevTools MCP server: https://github.com/vercel/next-devtools-mcp

### Notes

- The Backend Agent operates on files in `sample-dashboard/src/` - all file operations must be scoped to allowed paths
- `papaparse` is already installed in the sample-dashboard project for CSV parsing
- `lib/data-utils.ts` already exists with base CSV loading utilities
- File read/write/edit operations are handled by the MCP filesystem server
- Custom tools (`create_api`, `create_model`) encode domain intent and validation

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:

- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

---

## Tasks

### Phase 0: Setup

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/dev-orchestrator-backend-agent`)

---

### Phase 1: Backend Agent Schemas and Models

- [x] 1.0 Define Pydantic schemas for Backend Agent outputs
  - [x] 1.1 Create `src/agents/backend/__init__.py` with package exports
  - [x] 1.2 Create `src/models/backend_manifest.py` with the following models:
    - [x] 1.2.1 `DataSourceInfo` - schema for data source metadata (original_path, project_path, row_count, columns)
    - [x] 1.2.2 `ModelInfo` - schema for created TypeScript models (name, file_path, description, exports)
    - [x] 1.2.3 `QueryParam` - schema for API query parameters (name, type, required, description)
    - [x] 1.2.4 `RouteInfo` - schema for created API routes (path, file_path, method, description, serves_visual_ids, query_params, response_schema)
    - [x] 1.2.5 `ValidationResult` - schema for lint/build results (lint_passed, build_passed, errors)
    - [x] 1.2.6 `BackendManifest` - main manifest schema combining all above (created_at, run_id, data_source, models, routes, validation, notes)
  - [x] 1.3 Add `ApiError` TypeScript interface definition as a constant string for reference in prompts

---

### Phase 2: Backend Tools - File System Operations

- [x] 2.0 Implement scoped filesystem tools
  - [x] 2.1 Create `src/tools/backend/__init__.py` with package exports
  - [x] 2.2 Create `src/tools/backend/filesystem.py`:
    - [x] 2.2.1 Define `ALLOWED_PATHS` constant with scoped paths (sample-dashboard/src/api, models, lib/data-utils.ts, data, and run artifacts)
    - [x] 2.2.2 Implement `_validate_path(path: str, run_dir: str) -> Path` helper that checks if path is within allowed scope
    - [x] 2.2.3 Implement `read_file(path: str, from_line: int = None, to_line: int = None)` tool - reads file content with optional line range
    - [x] 2.2.4 Implement `inspect_dir(path: str)` tool - lists directory contents with file/folder indicators
    - [x] 2.2.5 Implement `search_content(query: str, path_pattern: str = None)` tool - grep-like search in allowed paths
  - [x] 2.3 Write unit tests for path validation and scoping in `tests/tools/test_backend_tools.py`

---

### Phase 3: Backend Tools - Data Access

- [x] 3.0 Implement data access tools
  - [x] 3.1 Create `src/tools/backend/data_access.py`:
    - [x] 3.1.1 Implement `get_sample_rows(csv_path: str, num_rows: int = 5)` tool - reads first N rows of CSV using polars (max 5 rows)
    - [x] 3.1.2 Implement `read_data_profile()` tool - reads `{run_dir}/data_analysis/data_profile.md`
    - [x] 3.1.3 Implement `read_dashboard_concept()` tool - reads and parses `{run_dir}/planner/dashboard_concept.json`
    - [x] 3.1.4 Implement `copy_data_to_project()` tool - copies all files from `{run_dir}/data_analysis/cleaned/` to `sample-dashboard/data/`
  - [x] 3.2 Ensure `copy_data_to_project` creates the `data/` directory if it doesn't exist
  - [x] 3.3 Ensure `copy_data_to_project` returns a summary of copied files and their paths
  - [x] 3.4 Add unit tests for data access tools

---

### Phase 4: Backend Tools - File Creation

- [x] 4.0 Implement file creation tools
  - [x] 4.1 Create `src/tools/backend/creation.py`:
    - [x] 4.1.1 Implement `create_api(route_path: str, content: str)` tool:
      - Accepts Next.js route notation (e.g., "sales", "products/[id]")
      - Auto-appends `route.ts` filename
      - Creates file at `sample-dashboard/src/app/api/{route_path}/route.ts`
      - Creates parent directories if needed
      - Fails if file already exists (suggests MCP filesystem edit_file)
      - Returns success message with full path and endpoint
    - [x] 4.1.2 Implement `create_model(name: str, content: str)` tool:
      - Creates file at `sample-dashboard/src/models/{name}.ts`
      - Creates `models/` directory if needed
      - Validates that content exports at least one type/interface
      - Fails if file already exists
  - [x] 4.2 Add unit tests for creation tools

**Note:** File editing (e.g., modifying existing routes, adding utilities) is handled by the MCP filesystem server's `edit_file` tool. Custom tools focus on domain-specific creation with validation.

---

### Phase 5: Backend Tools - Validation

- [x] 5.0 Implement validation tools
  - [x] 5.1 Create `src/tools/backend/validation.py`:
    - [x] 5.1.1 Define `SAMPLE_DASHBOARD_PATH` constant pointing to project root
    - [x] 5.1.2 Implement `check_typescript_syntax(content, filename)` tool:
      - Uses `tsc --noEmit` on temp file for fast syntax validation
      - Returns structured result with valid (bool) and errors (string)
      - Gracefully handles missing tsc (allows creation to proceed)
    - [x] 5.1.3 Implement `run_lint()` tool:
      - Execute `npm run lint` in sample-dashboard directory
      - Capture stdout/stderr
      - Return structured result with exit_code, stdout, stderr, passed (bool)
      - Truncate output if > 5000 chars
    - [x] 5.1.4 Implement `run_build()` tool:
      - Execute `npm run build` in sample-dashboard directory
      - Capture stdout/stderr
      - Return structured result with exit_code, stdout, stderr, passed (bool)
      - Truncate output if > 10000 chars (builds can be verbose)
  - [x] 5.2 Implement subprocess handling for npm commands
  - [x] 5.3 Add timeout handling (max 120 seconds for build, 60 seconds for lint, 10 seconds for syntax check)
  - [x] 5.4 Integrate syntax validation into `create_api` and `create_model` (pre-check before write)
  - [x] 5.5 Add unit tests in `tests/tools/test_validation.py` (20 tests)

---

### Phase 6: Backend Tools - Next.js Documentation

- [x] 6.0 Implement Next.js MCP documentation tool
  - [x] 6.1 Create `src/tools/backend/nextjs_docs.py`:
    - [x] 6.1.1 Research Next.js DevTools MCP server integration (https://github.com/vercel/next-devtools-mcp)
    - [x] 6.1.2 Implement `nextjs_init()` tool - initializes MCP server connection if needed
    - [x] 6.1.3 Implement `nextjs_docs(topic: str)` tool - queries Next.js documentation
    - [x] 6.1.4 Handle MCP server connection errors gracefully
  - [x] 6.2 Implemented MCP integration using ADK McpToolset:
    - [x] 6.2.1 `NextJsDocsMcp` class manages connection lifecycle with manual `init` call
    - [x] 6.2.2 `create_nextjs_toolset()` helper for direct McpToolset integration
    - [x] 6.2.3 Wrapper `nextjs_docs_tool` and `nextjs_init_tool` FunctionTools available
  - [x] 6.3 Document the chosen approach in code comments (see nextjs_docs.py header)
  - [x] 6.4 Add unit tests in `tests/tools/test_nextjs_docs.py` (26 tests)

---

### Phase 7: MCP Filesystem Server Integration

- [x] 7.0 Configure MCP filesystem server for Backend Agent
  - [x] 7.1 Document MCP server configuration:
    - [x] 7.1.1 Define allowed directories for the filesystem MCP server:
      - `sample-dashboard/src/app/api` - API routes
      - `sample-dashboard/src/models` - TypeScript models
      - `sample-dashboard/src/lib` - Utility functions
      - **NOTE**: `data` directory removed - read-only access via `get_sample_rows` tool and state templating
    - [x] 7.1.2 Create `src/tools/backend/filesystem_mcp.py` with programmatic McpToolset factory
    - [x] 7.1.3 Document the MCP tools available to the Backend Agent:
      - `read_file` - Read file contents
      - `write_file` - Create new files (prefer `create_api`/`create_model` for domain types)
      - `edit_file` - Modify existing files with search/replace
      - `list_directory` - List directory contents
      - `directory_tree` - Get directory structure
      - `read_multiple_files` - Read multiple files at once
      - `search_files` - Search for files by pattern
      - `list_allowed_directories` - List allowed directories
  - [x] 7.2 Update Backend Agent prompts:
    - [x] 7.2.1 Created `src/agents/backend/prompts.py` with `build_backend_agent_prompt()`
    - [x] 7.2.2 Implemented "Information Gathering First" workflow:
      - MUST read dashboard_concept, data_profile, sample_rows BEFORE coding
      - Clear phase-based workflow: Understand → Plan → Copy Data → Models → Routes → Validate → Manifest
    - [x] 7.2.3 Document that `create_api` and `create_model` should be preferred for new files
    - [x] 7.2.4 Document that `edit_file` should be used for modifying existing files
    - [x] 7.2.5 Refactored prompts structure:
      - Moved agent prompts from `src/prompts/system_prompts.py` to respective agent folders
      - Created `src/agents/data_analysis/prompts.py`
      - Created `src/agents/planner/prompts.py`
      - Created `src/agents/orchestrator/prompts.py`
      - Moved summarizer prompts to `src/tools/llm_client.py` as `get_output_summary_prompt()` and `get_snippet_summary_prompt()`
      - Deleted `src/prompts/` folder
    - [x] 7.2.6 Removed `data` directory from MCP filesystem allowed paths (read-only via state templating)
  - [x] 7.3 Test MCP filesystem integration:
    - [x] 7.3.1 Created `tests/tools/test_filesystem_mcp.py` with 19 unit tests
    - [x] 7.3.2 All factory function tests pass (correct filter, npx command, allowed paths, timeout)
    - [x] 7.3.3 Module exports correctly via `__init__.py` with renamed constants

---

### Phase 8: Backend Tools - Manifest

- [ ] 8.0 Implement manifest writing tool
  - [ ] 8.1 Create `src/tools/backend/manifest.py`:
    - [ ] 8.1.1 Implement `write_backend_manifest(manifest: BackendManifest)` tool:
      - Validate manifest against schema
      - Create `{run_dir}/dev/` directory if needed
      - Write manifest as JSON to `{run_dir}/dev/backend_manifest.json`
      - Return success message with path
  - [ ] 8.2 Add helper to auto-populate `created_at` timestamp if not provided
  - [ ] 8.3 Add unit tests for manifest writing

---

### Phase 9: Backend Agent Implementation

- [ ] 9.0 Implement Backend Agent
  - [ ] 9.1 Create `src/agents/backend/prompts.py`:
    - [ ] 9.1.1 Define `BACKEND_AGENT_SYSTEM_PROMPT` with:
      - Role description (Next.js API route developer)
      - Available tools and their purposes
      - Workflow steps (init → understand → plan → inspect → copy → utilities → models → routes → validate → manifest)
      - API route patterns and conventions
      - Error response format (`ApiError` interface)
      - TypeScript best practices (pragmatic strict mode)
      - Retry strategy for lint/build failures
    - [ ] 9.1.2 Include example API route template in prompt
    - [ ] 9.1.3 Include `papaparse` usage examples
  - [ ] 9.2 Create `src/agents/backend/agent.py`:
    - [ ] 9.2.1 Import all backend tools from `src/tools/backend/`
    - [ ] 9.2.2 Create `BackendAgent` as `LlmAgent` with:
      - Name: `"backend_agent"`
      - Model: Use configured LLM (e.g., `gpt-4o`)
      - System prompt from `prompts.py`
      - Tools: all backend tools
      - Output schema: None (uses tool calls and manifest)
    - [ ] 9.2.3 Implement `before_agent_callback` to log start and read initial state
    - [ ] 9.2.4 Implement `after_agent_callback` to:
      - Update state with `backend_manifest_path` and `backend_status`
      - Log completion status
  - [ ] 9.3 Add retry tracking for lint/build in agent state or tool context

---

### Phase 10: Dev Orchestrator Implementation

- [ ] 10.0 Implement Dev Orchestrator
  - [ ] 10.1 Create `src/agents/dev_orchestrator/__init__.py` with package exports
  - [ ] 10.2 Create `src/agents/dev_orchestrator/prompts.py`:
    - [ ] 10.2.1 Define `DEV_ORCHESTRATOR_SYSTEM_PROMPT` with:
      - Role description (coordinator for Backend, Frontend, QA agents)
      - Available sub-agents and their responsibilities
      - State keys it reads from (dashboard_spec_path, cleaned_data_path, etc.)
      - State keys it writes to (backend_manifest_path, backend_status)
      - Sequential workflow (Backend → Frontend → QA)
      - Error handling and reporting responsibilities
  - [ ] 10.3 Create `src/agents/dev_orchestrator/agent.py`:
    - [ ] 10.3.1 Import `BackendAgent` from `src/agents/backend/agent.py`
    - [ ] 10.3.2 Create `DevOrchestrator` as `LlmAgent` with:
      - Name: `"dev_orchestrator"`
      - Model: Use configured LLM
      - System prompt from `prompts.py`
      - Sub-agents: `[backend_agent]` (Frontend, QA added later)
    - [ ] 10.3.3 Implement `before_agent_callback` to:
      - Validate required state keys exist (dashboard_spec_path, cleaned_data_path, etc.)
      - Log orchestration start
    - [ ] 10.3.4 Implement `after_agent_callback` to:
      - Collect results from sub-agents
      - Update final state
      - Log orchestration completion
  - [ ] 10.4 Configure Dev Orchestrator to delegate to Backend Agent with proper context

---

### Phase 11: Integration with Manager Agent

- [ ] 11.0 Integrate Dev Orchestrator into main flow
  - [ ] 11.1 Update `src/agents/manager/agent.py`:
    - [ ] 11.1.1 Import `DevOrchestrator` from `src/agents/dev_orchestrator/agent.py`
    - [ ] 11.1.2 Add Dev Orchestrator as sub-agent after Planner Agent
    - [ ] 11.1.3 Update Manager's system prompt to include Dev Orchestrator in workflow
  - [ ] 11.2 Update `src/prompts/system_prompts.py` if needed for Manager Agent changes
  - [ ] 11.3 Ensure state flows correctly:
    - [ ] 11.3.1 Planner sets `dashboard_spec_path` in state
    - [ ] 11.3.2 Data Analysis sets `cleaned_data_path` and `data_profile_path` in state
    - [ ] 11.3.3 Dev Orchestrator reads these and passes to Backend Agent
    - [ ] 11.3.4 Backend Agent writes `backend_manifest_path` and `backend_status`

---

### Phase 12: Testing

- [ ] 12.0 Add comprehensive tests
  - [x] 12.1 Create `tests/tools/test_backend_tools.py`:
    - [x] 12.1.1 Test `_validate_path` with allowed and disallowed paths
    - [x] 12.1.2 Test `search_content` with regex patterns
    - [x] 12.1.3 Test `create_api` creates files correctly with Next.js notation
    - [x] 12.1.4 Test `create_api` fails on existing file
    - [x] 12.1.5 Test `create_model` validates exports
    - [x] 12.1.6 Test `copy_data_to_project` copies all files
    - [x] 12.1.7 Test data access tools (get_sample_rows, read_data_profile, read_dashboard_concept)
  - [ ] 12.2 Create `tests/agents/test_backend_agent.py`:
    - [ ] 12.2.1 Test Backend Agent initialization
    - [ ] 12.2.2 Test Backend Agent has all required tools
    - [ ] 12.2.3 Mock tool calls to verify workflow
  - [ ] 12.3 Create `tests/agents/test_dev_orchestrator.py`:
    - [ ] 12.3.1 Test Dev Orchestrator initialization
    - [ ] 12.3.2 Test state validation in before_agent_callback
    - [ ] 12.3.3 Test delegation to Backend Agent

---

### Phase 13: End-to-End Testing and Documentation

- [ ] 13.0 End-to-end testing and documentation
  - [ ] 13.1 Run full pipeline with sample data:
    - [ ] 13.1.1 Use existing run with dashboard_concept.json
    - [ ] 13.1.2 Verify Backend Agent creates API routes
    - [ ] 13.1.3 Verify lint passes
    - [ ] 13.1.4 Verify build passes
    - [ ] 13.1.5 Verify backend_manifest.json is complete
  - [ ] 13.2 Test auto-fix capability:
    - [ ] 13.2.1 Intentionally create a lint error
    - [ ] 13.2.2 Verify Backend Agent detects and fixes it
    - [ ] 13.2.3 Verify retry count is tracked
  - [ ] 13.3 Update project documentation:
    - [ ] 13.3.1 Update `Agents.md` with Dev Orchestrator and Backend Agent sections
    - [ ] 13.3.2 Document the new tools in README or separate tools documentation
  - [ ] 13.4 Create sample run artifacts for testing

---

## Tool Reference

### Custom Tools (Summary)

| Tool                     | File             | Purpose                                               |
| ------------------------ | ---------------- | ----------------------------------------------------- |
| `search_content`         | `filesystem.py`  | Search for patterns in files (scoped)                 |
| `get_sample_rows`        | `data_access.py` | Read CSV sample rows (max 5)                          |
| `read_data_profile`      | `data_access.py` | Read data profile markdown                            |
| `read_dashboard_concept` | `data_access.py` | Read dashboard spec JSON                              |
| `copy_data_to_project`   | `data_access.py` | Copy cleaned data to Next.js project                  |
| `create_api`             | `creation.py`    | Create new API route (Next.js notation + syntax)      |
| `create_model`           | `creation.py`    | Create new TypeScript model with validation           |
| `run_lint`               | `validation.py`  | Execute npm run lint                                  |
| `run_build`              | `validation.py`  | Execute npm run build                                 |
| `nextjs_init`            | `nextjs_docs.py` | Initialize Next.js MCP connection (call before agent) |
| `nextjs_docs`            | `nextjs_docs.py` | Query Next.js documentation via MCP                   |
| `write_backend_manifest` | `manifest.py`    | Write manifest JSON                                   |

> Note: TypeScript syntax validation (`_check_typescript_syntax`) is an internal helper used by `create_api` and `create_model`, not exposed as a tool.

> Note: `nextjs_init` should be called once before the agent starts (via `NextJsDocsMcp.connect()`) to initialize the MCP connection and call the required `init` tool. Only `nextjs_docs` is exposed to the agent via `tool_filter=['nextjs_docs']`.

### MCP Filesystem Server Tools

| Tool                  | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `read_file`           | Read file contents                                   |
| `write_file`          | Create new files (prefer custom tools for API/model) |
| `edit_file`           | Modify existing files with search/replace            |
| `list_directory`      | List directory contents                              |
| `directory_tree`      | Get directory structure                              |
| `read_multiple_files` | Read multiple files at once                          |
| `search_files`        | Search for files by pattern                          |
| `get_file_info`       | Get file metadata                                    |
| `move_file`           | Move or rename files                                 |

### Filesystem MCP Integration

The MCP filesystem server is integrated programmatically via `src/tools/backend/filesystem_mcp.py`:

```python
from src.tools.backend import create_filesystem_toolset

# Create toolset with default allowed directories
toolset = create_filesystem_toolset()

# Or with additional paths (e.g., run directory)
toolset = create_filesystem_toolset_with_run_dir("runs/run_123")

# Add to agent's tools list
agent = LlmAgent(
    model="gemini-2.0-flash",
    name="backend_agent",
    tools=[
        toolset,  # McpToolset auto-connects when agent runs
        # ... other tools
    ],
)
```

### Allowed Paths (Filesystem MCP)

The filesystem MCP server is configured with these directories (defined in `filesystem_mcp.py`):

```python
ALLOWED_DIRECTORIES = [
    "sample-dashboard/src/app/api",   # API routes
    "sample-dashboard/src/models",    # TypeScript models
    "sample-dashboard/src/lib",       # Utility functions
    # NOTE: data/ directory NOT included - no write access
    # Data paths provided via state templating, read via get_sample_rows
]
```

Additional paths can be added via `create_filesystem_toolset(additional_paths=[...])` or `create_filesystem_toolset_with_run_dir(run_dir)`.

### State Keys

**Read by Dev Orchestrator:**

- `dashboard_spec_path` - Path to dashboard_concept.json (from Planner)
- `cleaned_data_path` - Path to cleaned CSV (from Data Analysis)
- `data_profile_path` - Path to data_profile.md (from Data Analysis)
- `run_dir` - Current run directory (from Manager)

**Written by Backend Agent:**

- `backend_manifest_path` - Path to generated manifest
- `backend_status` - "success" | "failed" | "partial"
