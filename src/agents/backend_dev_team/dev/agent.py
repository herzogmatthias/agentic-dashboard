"""
Backend Dev Agent - Implements single PlannerArtifactTodo items.

This agent receives ONE artifact to implement per invocation, creates the
necessary files (API routes, models, helpers), validates with lint/type-check,
and returns a structured BackendDevResult with DevReport.

Uses PlanReActPlanner for structured multi-step reasoning.

Note: State initialization (run_dir, workspace_root, metrics_ref lookup, cleaned_data_files)
happens at the Loop Agent level in `inject_artifact_context_for_dev` callback.
The Dev Agent only runs within the Loop Agent's custom control flow.
"""

import json
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.planners import PlanReActPlanner
from google.adk.models.lite_llm import LiteLlm
from phoenix.otel import register as register_phoenix

from src.core.logging import get_logger
from src.models.backend_dev import BackendDevResult, BackendDevInput, PlannerArtifactTodo
from src.tools.backend_dev import (
    get_backend_dev_tools,
    get_backend_dev_mcp_toolset,
    SAMPLE_DASHBOARD_ROOT,
)
from src.agents.backend_dev_team.dev.prompts import build_backend_dev_prompt

from src.agents.backend_dev_team.dev.state import (STATE_KEY_DEV_RESULT)

# Register Phoenix tracing
tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)

# Model configuration
BACKEND_DEV_MODEL = "xai/grok-code-fast-1"


# =============================================================================
# State Keys (set by loop/callbacks.py inject_artifact_context_for_dev)
# =============================================================================

STATE_KEY_RUN_ID = "run_id"
STATE_KEY_RUN_DIR = "run_dir"
STATE_KEY_WORKSPACE_ROOT = "workspace_root"
STATE_KEY_CURRENT_ARTIFACT = "current_artifact"
STATE_KEY_CURRENT_GROUP = "current_group"
STATE_KEY_PREVIOUS_SUMMARIES = "previous_summaries"
STATE_KEY_CLEANED_DATA_FILES = "cleaned_data_files"
STATE_KEY_METRICS_REF_CONTEXT = "metrics_ref_context"



# =============================================================================
# Dynamic Instruction Provider
# =============================================================================

async def backend_dev_instruction_provider(context: ReadonlyContext) -> str:
    """
    Dynamic instruction provider that builds the prompt with injected state.
    
    Reads from session state:
    - workspace_root: Absolute path to sample-dashboard
    - current_group: The BackendTodoGroup to implement (contains multiple artifacts)
    - previous_summaries: List of summaries from prior groups
    - cleaned_data_files: List of cleaned data file paths
    - metrics_ref_context: Pre-looked-up metrics reference context
    
    Args:
        context: ReadonlyContext with access to session state
        
    Returns:
        Prompt string with state values injected
    """
    state = context.state
    
    # Get workspace root
    workspace_root = state.get(STATE_KEY_WORKSPACE_ROOT)
    if not workspace_root:
        workspace_root = str(SAMPLE_DASHBOARD_ROOT.resolve())
    
    # Get group info
    group = state.get(STATE_KEY_CURRENT_GROUP)
    if group:
        if isinstance(group, dict):
            group_id = group.get("id", "unknown")
            group_kind = group.get("kind", "other")
            group_label = group.get("label", group_id)
            group_description = group.get("description", "")
            artifacts = group.get("artifacts", [])
            pending_artifacts = [a for a in artifacts if a.get("status", "pending") == "pending"]
            artifacts_json = json.dumps(pending_artifacts, separators=(",", ":"))
        elif hasattr(group, "model_dump"):
            group_data = group.model_dump()
            group_id = group_data.get("id", "unknown")
            group_kind = group_data.get("kind", "other")
            group_label = group_data.get("label", group_id)
            group_description = group_data.get("description", "")
            artifacts = group_data.get("artifacts", [])
            pending_artifacts = [a for a in artifacts if a.get("status", "pending") == "pending"]
            artifacts_json = json.dumps(pending_artifacts, separators=(",", ":"))
        else:
            group_id = "unknown"
            group_kind = "other"
            group_label = "Unknown"
            group_description = ""
            artifacts_json = str(group)
    else:
        group_id = "unknown"
        group_kind = "other"
        group_label = "No group assigned"
        group_description = ""
        artifacts_json = "[]"
    
    # Get previous summaries
    previous_summaries = state.get(STATE_KEY_PREVIOUS_SUMMARIES, [])
    if previous_summaries:
        summaries_text = "\n".join(f"- {s}" for s in previous_summaries)
    else:
        summaries_text = "(no prior groups completed)"
    
    # Get cleaned data files
    cleaned_files = state.get(STATE_KEY_CLEANED_DATA_FILES, [])
    if cleaned_files:
        cleaned_data_files = ", ".join(cleaned_files)
    else:
        cleaned_data_files = "(not yet loaded)"
    
    # Get metrics_ref context (pre-looked-up in callback)
    metrics_ref_context_raw = state.get(STATE_KEY_METRICS_REF_CONTEXT, "(no metrics_ref specified)")
    if isinstance(metrics_ref_context_raw, (dict, list)):
        metrics_ref_context = json.dumps(metrics_ref_context_raw, separators=(",", ":"))
    else:
        metrics_ref_context = str(metrics_ref_context_raw)
    
    return build_backend_dev_prompt(
        workspace_root=workspace_root,
        group_id=group_id,
        group_kind=group_kind,
        group_label=group_label,
        group_description=group_description,
        artifacts_json=artifacts_json,
        previous_summaries=summaries_text,
        cleaned_data_files=cleaned_data_files,
        metrics_ref_context=metrics_ref_context,
    )


# =============================================================================
# Agent Factory
# =============================================================================

def create_backend_dev_agent(
    workspace_root: str | None = None,
) -> LlmAgent:
    """
    Create and configure the Backend Dev Agent.
    
    The Backend Dev Agent uses:
    - PlanReActPlanner for structured multi-step reasoning
    - Custom tools for file creation (create_api, create_model, create_helper)
    - MCP filesystem tools for read/write/edit
    - Data access tools (get_sample_rows, load_data_profile)
    - Validation tools (run_lint, run_type_check)
    - output_schema=BackendDevResult for structured output
    
    Args:
        workspace_root: Optional workspace root override (default: SAMPLE_DASHBOARD_ROOT)
        
    Returns:
        Configured LlmAgent instance
    """
    model = LiteLlm(model=BACKEND_DEV_MODEL)
    
    # Get tools - separate regular tools and MCP toolset
    regular_tools = get_backend_dev_tools()
    filesystem_toolset = get_backend_dev_mcp_toolset()
    
    # Combine tools
    tools = [
        *regular_tools,
        filesystem_toolset,
    ]
    
    # Note: before_agent_callback is NOT used here.
    # State initialization (run_dir, metrics_ref lookup, etc.) happens at the
    # Loop Agent level in inject_artifact_context_for_dev callback.
    # The Dev Agent only runs within the Loop Agent's custom control flow.
    agent = LlmAgent(
        name="backend_dev",
        model=model,
        #planner=PlanReActPlanner(),
        include_contents='none',
        instruction=backend_dev_instruction_provider,
        tools=tools,
        output_key=STATE_KEY_DEV_RESULT,
        output_schema=BackendDevResult,
    )
    
    logger.info(
        "Backend Dev Agent created",
        extra={
            "agent": "backend_dev",
            "phase": "create",
            "model": BACKEND_DEV_MODEL,
            "workspace_root": workspace_root or str(SAMPLE_DASHBOARD_ROOT),
        }
    )
    
    return agent


def get_backend_dev_agent() -> LlmAgent:
    """Get a configured Backend Dev Agent instance."""
    return create_backend_dev_agent()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main agent
    "create_backend_dev_agent",
    "get_backend_dev_agent",
    # Instruction provider
    "backend_dev_instruction_provider",
    # State keys
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_CURRENT_ARTIFACT",
    "STATE_KEY_CURRENT_GROUP",
    "STATE_KEY_PREVIOUS_SUMMARIES",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_METRICS_REF_CONTEXT",
    # Constants
    "BACKEND_DEV_MODEL",
]
