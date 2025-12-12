"""
Backend Dev Agent package.

The Backend Dev Agent implements a SINGLE PlannerArtifactTodo item per invocation,
creating API routes, TypeScript models, or helper utilities in the sample-dashboard
Next.js project.

Key differences from the old Backend Agent (src/agents/backend/):
- Single-artifact focus (not batch processing)
- Structured output via BackendDevResult schema
- Previous artifact summaries for context continuity
- DevReport for downstream agents (Tester, QA)
- No auto-injection of full dashboard_concept/data_profile (only metrics_ref lookup)

State initialization happens at the Loop Agent level (before_agent_callback in
inject_artifact_context_for_dev), not here. The Dev Agent only runs within the
Loop Agent's custom control flow.
"""

from src.agents.backend_dev_team.dev.agent import (
    # Main agent
    create_backend_dev_agent,
    get_backend_dev_agent,
    # Instruction provider
    backend_dev_instruction_provider,
    # State keys
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_WORKSPACE_ROOT,
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_CLEANED_DATA_FILES,
    STATE_KEY_METRICS_REF_CONTEXT,
    # Constants
    BACKEND_DEV_MODEL,
)

from src.agents.backend_dev_team.dev.prompts import (
    build_backend_dev_prompt,
    MINIMAL_TEST_PROMPT,
)


__all__ = [
    # Main agent factory
    "create_backend_dev_agent",
    "get_backend_dev_agent",
    # Prompt builder
    "build_backend_dev_prompt",
    "backend_dev_instruction_provider",
    # State keys
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_CURRENT_ARTIFACT",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_METRICS_REF_CONTEXT",
    # Constants
    "BACKEND_DEV_MODEL",
    "MINIMAL_TEST_PROMPT",
]
