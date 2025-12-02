# Dev Orchestrator & Backend Agent PRD

## 1. Introduction / Overview

This feature introduces a **Dev Orchestrator** and its first sub-agent, the **Backend Agent**, to the agentic-dashboard system. The Dev Orchestrator acts as a coordinator for the development team agents (Backend, Frontend, QA), similar to how the Manager Agent coordinates the Data Analysis and Planner agents.

**Problem Statement:** After the Planner Agent produces a `dashboard_concept.json`, there is currently no automated way to translate that specification into working code. Engineers must manually create API routes, data models, and UI components.

**Solution:** The Dev Orchestrator receives the dashboard concept and cleaned data artifacts, then coordinates specialized agents to implement:

1. **Backend Agent** (this PRD): Creates API routes that serve data to the dashboard
2. Frontend Agent (future): Creates React components using DaisyUI/Tailwind
3. QA Agent (future): Creates and runs tests against the implementation

The target Next.js project uses:

- **DaisyUI + Tailwind CSS v4** for styling
- **Next.js App Router** for routing and API routes
- **TanStack Table** for data tables
- **Recharts** for visualizations

---

## 2. Goals

1. **Create Dev Orchestrator** as a streaming sub-agent under the main Manager Agent, coordinating Backend, Frontend, and QA agents.

2. **Implement Backend Agent** that can:

   - Read and understand the dashboard concept specification
   - Access cleaned data files and data profiles
   - Create Next.js API routes that serve data for each visual/KPI
   - Create TypeScript data models/types
   - Validate its work via `npm run lint` and `npm run build`
   - Auto-fix issues when lint/build fails (max 3 retries)

3. **Produce a Backend Manifest** documenting all created routes, models, and their relationships to dashboard visuals.

4. **Scope API routes to the sample-dashboard project** at `C:\Users\darks\Documents\agentic-dashboard\sample-dashboard\src`.

5. **Enable iterative development** where the Backend Agent can be re-run to fix issues or add endpoints based on Frontend/QA feedback.

---

## 3. User Stories

1. **As a developer**, I want the Dev Orchestrator to receive the dashboard concept and automatically start backend implementation so I don't have to manually create API routes.

2. **As a developer**, I want the Backend Agent to analyze the dashboard concept and create appropriate API endpoints for each KPI and visual so the frontend has data to display.

3. **As a developer**, I want the Backend Agent to copy the cleaned CSV to the Next.js project's `data/` folder so API routes can access it.

4. **As a developer**, I want the Backend Agent to create TypeScript interfaces for API responses so the frontend has type safety.

5. **As a developer**, I want the Backend Agent to validate its code with `npm run lint` and `npm run build` so I know the generated code compiles correctly.

6. **As a developer**, I want the Backend Agent to automatically fix lint/build errors (up to 3 attempts) so minor issues don't block progress.

7. **As a developer**, I want a backend manifest listing all created routes and models so the Frontend Agent knows what APIs are available.

8. **As a developer**, I want the Backend Agent to use Next.js documentation when needed so it follows current best practices for App Router API routes.

---

## 4. Functional Requirements

### 4.1 Dev Orchestrator

1. The system must implement a **Dev Orchestrator Agent** as a sub-agent under the main Manager Agent.

2. The Dev Orchestrator must receive from session state:

   - `dashboard_spec_path`: Path to `dashboard_concept.json`
   - `cleaned_data_path`: Path to the cleaned CSV file
   - `data_profile_path`: Path to `data_profile.md`
   - `run_dir`: Current run directory for artifacts

3. The Dev Orchestrator must coordinate the following sub-agents (sequentially for v1):

   - Backend Agent (implemented in this PRD)
   - Frontend Agent (future)
   - QA Agent (future)

4. The Dev Orchestrator must pass relevant context to each sub-agent and collect their outputs.

5. The Dev Orchestrator must handle failures gracefully, reporting which agent failed and why.

### 4.2 Backend Agent Tools

The Backend Agent must have access to the following tools:

#### File Reading Tools

6. **`read_file(path, from_line?, to_line?)`**: Read file contents, scoped to allowed paths:

   - `sample-dashboard/src/**` (Next.js project source)
   - Run artifacts: `cleaned/`, `data_profile.md`, `dashboard_concept.json`

7. **`get_sample_rows(csv_path, num_rows=5)`**: Read first N rows of a CSV file to understand data structure without loading the entire file.

8. **`read_data_profile()`**: Read the `data_profile.md` from the current run's artifacts.

9. **`read_dashboard_concept()`**: Read the `dashboard_concept.json` from the current run's planner output.

#### Directory Tools

10. **`inspect_dir(path)`**: List contents of a directory, scoped to allowed paths.

#### File Creation Tools

11. **`create_api(route_path, content)`**: Create a new API route file.

    - `route_path`: Relative path under `app/api/` (e.g., `kpis/attrition-rate/route.ts`)
    - `content`: Full TypeScript content for the route handler
    - Must create parent directories if they don't exist
    - Must fail if file already exists (use `patch_file` to modify)

12. **`create_model(name, content)`**: Create a new TypeScript model/type file.
    - `name`: Model name (e.g., `AttritionData`)
    - Creates file at `models/{name}.ts`
    - Must export the type/interface

#### File Modification Tool

13. **`patch_file(file_path, patch_content)`**: Apply patches to existing files using a context-based SEARCH/REPLACE format that is LLM-friendly:

    ```
    <<<<<<< SEARCH
    Text to find in the file (must appear exactly once)
    =======
    Text to replace it with
    >>>>>>> REPLACE
    ```

    - Supports multiple SEARCH/REPLACE blocks in a single call
    - Validates that each search text appears **exactly once** in the file
    - Returns error if search text not found or appears multiple times
    - This format avoids line number issues that LLMs struggle with

#### Search Tool

14. **`search_content(query, path_pattern?)`**: Search for text/patterns in allowed paths.
    - Searches in `sample-dashboard/src/**` by default
    - Returns file paths and matching lines
    - Useful for finding existing patterns, imports, or implementations

#### Validation Tools

15. **`run_lint()`**: Execute `npm run lint` in the sample-dashboard project.

    - Returns stdout/stderr and exit code
    - Working directory: `sample-dashboard/`

16. **`run_build()`**: Execute `npm run build` in the sample-dashboard project.
    - Returns stdout/stderr and exit code (truncated if too long)
    - Working directory: `sample-dashboard/`

#### Documentation Tool

17. **`nextjs_docs(topic)`**: Query Next.js documentation via MCP server.
    - Must call `nextjs_init()` before first use in a session
    - Topics: App Router, Route Handlers, API Routes, Data Fetching, etc.
    - Agent decides what to search based on current task

#### Output Tool

18. **`write_backend_manifest(manifest)`**: Write the backend manifest to the run directory.
    - Manifest schema (see Section 4.4)
    - Saves to `{run_dir}/dev/backend_manifest.json`

### 4.3 Backend Agent Workflow

19. The Backend Agent must follow this general workflow:

    ```
    1. Initialize: Call nextjs_init() to enable docs access
    2. Understand: Read dashboard_concept.json and data_profile.md
    3. Plan: Determine required API routes based on KPIs and visuals
    4. Inspect: Check existing project structure (models/, app/api/)
    5. Copy Data: Ensure cleaned CSV is in sample-dashboard/data/
    6. Create Models: Generate TypeScript interfaces for data shapes
    7. Create Routes: Generate API route handlers for each endpoint
    8. Validate: Run lint, fix errors if any (max 3 retries)
    9. Build: Run build, fix errors if any (max 3 retries)
    10. Manifest: Write backend_manifest.json documenting all created artifacts
    ```

20. When lint or build fails, the Backend Agent must:

    - Parse the error output to identify the issue
    - Use `patch_file` or `create_api`/`create_model` to fix the issue
    - Retry the validation (max 3 total attempts per validation type)
    - If still failing after 3 attempts, report failure with context

21. The Backend Agent must create API routes that:
    - Use Next.js App Router conventions (`route.ts` files)
    - Return JSON responses with proper typing
    - Handle query parameters for filtering (matching dashboard filters)
    - Read data from the CSV file in `data/` folder
    - Include basic error handling

### 4.4 Backend Manifest Schema

22. The backend manifest must conform to this schema:

    ```typescript
    interface BackendManifest {
      created_at: string; // ISO timestamp
      run_id: string; // Reference to the run
      data_source: {
        original_path: string; // Path to cleaned CSV in run artifacts
        project_path: string; // Path in sample-dashboard/data/
        row_count: number;
        columns: string[];
      };
      models: Array<{
        name: string; // e.g., "AttritionData"
        file_path: string; // e.g., "models/AttritionData.ts"
        description: string;
        exports: string[]; // Exported type names
      }>;
      routes: Array<{
        path: string; // e.g., "/api/kpis/attrition-rate"
        file_path: string; // e.g., "app/api/kpis/attrition-rate/route.ts"
        method: "GET" | "POST";
        description: string;
        serves_visual_ids: string[]; // References to dashboard_concept visual IDs
        query_params?: Array<{
          name: string;
          type: string;
          required: boolean;
          description: string;
        }>;
        response_schema: string; // Reference to model or inline type
      }>;
      validation: {
        lint_passed: boolean;
        build_passed: boolean;
        errors?: string[];
      };
      notes: string[]; // Any important notes for Frontend/QA
    }
    ```

### 4.5 Data Access Patterns

23. The Backend Agent must be able to access:

    - **Dashboard Concept**: `{run_dir}/planner/dashboard_concept.json`
    - **Data Profile**: `{run_dir}/data_analysis/data_profile.md`
    - **Cleaned Data**: `{run_dir}/data_analysis/cleaned/*.csv`
    - **Next.js Project**: `C:\Users\darks\Documents\agentic-dashboard\sample-dashboard\src\`

24. The Backend Agent must copy the cleaned CSV to `sample-dashboard/data/` before creating API routes.

25. API routes should read data using a utility function that:
    - Loads CSV data (consider caching for performance)
    - Applies filters based on query parameters
    - Aggregates data as needed for KPIs/visuals

### 4.6 Integration with Existing System

26. The Dev Orchestrator must be callable from the main Manager Agent after the Planner completes successfully.

27. The Dev Orchestrator must read necessary paths from session state (set by Planner/Data Analysis agents).

28. The Backend Agent must update session state with:
    - `backend_manifest_path`: Path to the generated manifest
    - `backend_status`: "success" | "failed" | "partial"

---

## 5. Non-Goals (Out of Scope)

1. **Frontend Agent implementation** - Will be a separate PRD
2. **QA Agent implementation** - Will be a separate PRD
3. **Database integration** - API routes read from CSV files only
4. **Authentication/Authorization** - No auth on API routes
5. **Caching layer** - Simple in-memory data loading only
6. **API documentation generation** - Manifest serves as documentation
7. **Running the Next.js dev server** - Validation via lint/build only
8. **Complex data transformations** - Basic filtering and aggregation only
9. **WebSocket/real-time endpoints** - REST API routes only
10. **Deployment** - Local development only

---

## 6. Design Considerations

### Agent Architecture

```
Manager Agent (existing)
    ├── Data Analysis Agent (existing)
    ├── Planner Agent (existing)
    └── Dev Orchestrator (NEW)
            ├── Backend Agent (NEW - this PRD)
            ├── Frontend Agent (future)
            └── QA Agent (future)
```

### File Structure for Backend Agent

```
src/agents/dev_orchestrator/
    ├── __init__.py
    ├── agent.py              # Dev Orchestrator LlmAgent
    └── prompts.py            # System prompts

src/agents/backend/
    ├── __init__.py
    ├── agent.py              # Backend Agent LlmAgent
    ├── prompts.py            # System prompts for backend tasks
    └── schemas.py            # BackendManifest and related Pydantic models

src/tools/backend/
    ├── __init__.py
    ├── filesystem.py         # read_file, inspect_dir, search_content
    ├── creation.py           # create_api, create_model
    ├── patching.py           # patch_file implementation
    ├── validation.py         # run_lint, run_build
    ├── data_access.py        # get_sample_rows, read_data_profile, read_dashboard_concept
    └── manifest.py           # write_backend_manifest
```

### patch_file Implementation

The `patch_file` tool uses a SEARCH/REPLACE block format that is more reliable for LLMs than line-number-based editing:

```python
def patch_file(file_path: str, patch_content: str) -> str:
    """
    Apply patches using SEARCH/REPLACE blocks.

    Format:
    <<<<<<< SEARCH
    exact text to find (must appear exactly once)
    =======
    text to replace it with
    >>>>>>> REPLACE

    Multiple blocks can be included in one call.
    """
    # 1. Validate block integrity (balanced markers)
    # 2. Parse all SEARCH/REPLACE blocks
    # 3. For each block:
    #    - Verify search text appears exactly once
    #    - Replace with new text
    # 4. Write updated content
    # 5. Return success/failure message
```

### State Management

The Dev Orchestrator reads from state:

```python
{
    "dashboard_spec_path": str,    # From Planner
    "cleaned_data_path": str,      # From Data Analysis
    "data_profile_path": str,      # From Data Analysis
    "run_dir": str,                # From Manager
}
```

The Backend Agent writes to state:

```python
{
    "backend_manifest_path": str,
    "backend_status": "success" | "failed" | "partial",
}
```

---

## 7. Technical Considerations

### Next.js Project Structure

The target project at `sample-dashboard/src/` follows Next.js App Router conventions:

```
sample-dashboard/
├── src/
│   ├── app/
│   │   ├── api/           # API routes created by Backend Agent
│   │   │   ├── kpis/
│   │   │   │   └── [kpi-name]/
│   │   │   │       └── route.ts
│   │   │   └── visuals/
│   │   │       └── [visual-id]/
│   │   │           └── route.ts
│   │   ├── page.tsx
│   │   └── layout.tsx
│   └── models/            # TypeScript types created by Backend Agent
│       └── *.ts
├── data/                  # Cleaned CSV copied here
│   └── cleaned.csv
└── package.json
```

### API Route Pattern

Example generated route for a KPI:

```typescript
// app/api/kpis/attrition-rate/route.ts
import { NextResponse } from "next/server";
import { readData, filterData } from "@/lib/data-utils";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);

  const filters = {
    incomeCategory: searchParams.get("income_category"),
    cardCategory: searchParams.get("card_category"),
  };

  const data = await readData();
  const filtered = filterData(data, filters);

  const totalCustomers = filtered.length;
  const attrited = filtered.filter((r) => r.churn_flag === 1).length;
  const attritionRate = totalCustomers > 0 ? attrited / totalCustomers : 0;

  return NextResponse.json({
    value: attritionRate,
    formatted: `${(attritionRate * 100).toFixed(1)}%`,
    metadata: {
      total_customers: totalCustomers,
      attrited_customers: attrited,
    },
  });
}
```

### Next.js MCP Server

The Backend Agent uses the Next.js DevTools MCP server for documentation:

- Repository: https://github.com/vercel/next-devtools-mcp
- Only the `nextjs_docs` tool is needed
- Must call initialization before first docs query

### Validation Strategy

1. **Lint First**: Catches syntax errors, import issues, type errors
2. **Build Second**: Catches runtime configuration issues
3. **Retry Logic**:
   - Parse error output
   - Identify file and issue
   - Apply fix via `patch_file`
   - Re-run validation
   - Max 3 attempts per validation type

### Path Scoping

All file operations must be scoped to prevent unauthorized access:

```python
ALLOWED_PATHS = [
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/src",
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/data",
    "{run_dir}/data_analysis/cleaned",
    "{run_dir}/data_analysis/data_profile.md",
    "{run_dir}/planner/dashboard_concept.json",
]
```

---

## 8. Success Metrics

1. **Functional Success**:

   - Given a valid `dashboard_concept.json`, the Backend Agent creates:
     - At least one API route per KPI defined
     - At least one API route per visual that requires data
     - TypeScript models for response types
   - `npm run lint` passes
   - `npm run build` passes
   - `backend_manifest.json` is complete and valid

2. **Code Quality**:

   - Generated code follows Next.js App Router conventions
   - TypeScript types are properly defined and exported
   - API routes handle basic error cases

3. **Reliability**:

   - Auto-fix successfully resolves common lint/build errors
   - Backend Agent completes within reasonable time (< 5 minutes)
   - Clear error messages when fixes fail

4. **Integration**:
   - Dev Orchestrator successfully receives Backend Agent output
   - State is properly updated for Frontend Agent consumption
   - Manifest provides sufficient information for Frontend development

---

## 9. Open Questions

1. **Data Utility Library**: Should we pre-create a `lib/data-utils.ts` with CSV loading and filtering utilities, or should the Backend Agent create this as needed?

2. **Route Granularity**: Should each KPI/visual have its own route, or should we have aggregate endpoints (e.g., `/api/kpis` returning all KPIs)?

3. **Error Response Format**: What should the standard error response format be for API routes?

4. **CSV Parsing Library**: Should we mandate a specific CSV parsing library (e.g., `papaparse`, `csv-parse`) or let the agent decide?

5. **Caching Strategy**: For v1, we skip caching, but should the generated code include TODO comments for future caching implementation?

6. **TypeScript Strictness**: Should generated code satisfy `strict: true` TypeScript configuration?

7. **Test File Generation**: Should the Backend Agent also create basic test files for the API routes, or leave this entirely to the QA Agent?
