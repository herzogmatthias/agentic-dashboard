"""
Testing Agent - Writes and runs tests for backend artifacts.

This agent receives ONE artifact to test per invocation, creates Jest test
files, runs the tests, and returns a structured TestAgentResult with TestReport.

Uses PlanReActPlanner for structured multi-step reasoning.

Note: State initialization (run_dir, dev_report, etc.) happens at the Loop Agent
level. The Testing Agent only runs within the Loop Agent's custom control flow.
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
from src.models.testing_agent import TestAgentResult
from src.tools.tester import (
    get_tester_tools,
    get_tester_mcp_toolset,
    SAMPLE_DASHBOARD_ROOT,
    TESTS_ROOT,
)
from src.agents.backend_dev_team.tester.prompts import build_tester_prompt

# Register Phoenix tracing
tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)

# Model configuration
TESTER_MODEL = "xai/grok-code-fast-1"


# =============================================================================
# State Keys (set by loop/callbacks.py or loop agent)
# =============================================================================

STATE_KEY_RUN_ID = "run_id"
STATE_KEY_RUN_DIR = "run_dir"
STATE_KEY_WORKSPACE_ROOT = "workspace_root"
STATE_KEY_CURRENT_ARTIFACT = "current_artifact"
STATE_KEY_DEV_RESULT = "dev_result"
STATE_KEY_DEV_REPORT_PATH = "dev_report_path"
STATE_KEY_PREVIOUS_TEST_SUMMARY = "previous_test_summary"
STATE_KEY_CLEANED_DATA_FILES = "cleaned_data_files"
STATE_KEY_TESTER_RESULT = "tester_result"


# =============================================================================
# Dynamic Instruction Provider
# =============================================================================

async def tester_instruction_provider(context: ReadonlyContext) -> str:
    """
    Dynamic instruction provider that builds the prompt with injected state.
    
    Reads from session state:
    - workspace_root: Absolute path to sample-dashboard
    - current_artifact: The PlannerArtifactTodo to test
    - dev_result: The DevReport from Backend Dev Agent
    - previous_test_summary: Summary from previous test iteration (for retries)
    - cleaned_data_files: List of cleaned data file paths
    
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
    
    # Get artifact as JSON string
    artifact = state.get(STATE_KEY_CURRENT_ARTIFACT)
    if artifact:
        if isinstance(artifact, dict):
            artifact_json = json.dumps(artifact, indent=2)
        elif hasattr(artifact, "model_dump"):
            artifact_json = json.dumps(artifact.model_dump(), indent=2)
        else:
            artifact_json = str(artifact)
    else:
        artifact_json = "{}"
    
    # Get DevReport as JSON string
    dev_result = state.get(STATE_KEY_DEV_RESULT)
    if dev_result:
        # Extract the report portion if it's a full DevResult
        if isinstance(dev_result, dict):
            report = dev_result.get("report", dev_result)
            dev_report_json = json.dumps(report, indent=2)
        elif hasattr(dev_result, "report") and dev_result.report:
            dev_report_json = json.dumps(dev_result.report.model_dump(), indent=2)
        elif hasattr(dev_result, "model_dump"):
            dev_report_json = json.dumps(dev_result.model_dump(), indent=2)
        else:
            dev_report_json = str(dev_result)
    else:
        dev_report_json = "{}"
    
    # Get previous test summary
    previous_test_summary = state.get(STATE_KEY_PREVIOUS_TEST_SUMMARY)
    if not previous_test_summary:
        previous_test_summary = "(no previous test run)"
    
    # Get cleaned data files
    cleaned_files = state.get(STATE_KEY_CLEANED_DATA_FILES, [])
    if cleaned_files:
        cleaned_data_files = ", ".join(cleaned_files)
    else:
        cleaned_data_files = "(not yet loaded)"
    
    return build_tester_prompt(
        workspace_root=workspace_root,
        artifact_json=artifact_json,
        dev_report_json=dev_report_json,
        previous_test_summary=previous_test_summary,
        cleaned_data_files=cleaned_data_files,
    )


# =============================================================================
# Agent Factory
# =============================================================================

def create_tester_agent(
    workspace_root: str | None = None,
) -> LlmAgent:
    """
    Create and configure the Testing Agent.
    
    The Testing Agent uses:
    - PlanReActPlanner for structured multi-step reasoning
    - Custom tools for test creation (create_test)
    - Test execution tools (run_npm_test)
    - MCP filesystem tools for read access to source/tests
    - Context tools (read_dev_report, read_backend_manifest)
    - output_schema=TestAgentResult for structured output
    
    Args:
        workspace_root: Optional workspace root override (default: SAMPLE_DASHBOARD_ROOT)
        output_key: Optional state key where result is stored (for loop integration)
        
    Returns:
        Configured LlmAgent instance
    """
    model = LiteLlm(model=TESTER_MODEL)
    
    # Get regular tools
    regular_tools = get_tester_tools()
    
    # Get MCP filesystem toolset
    filesystem_toolset = get_tester_mcp_toolset()
    
    # Combine tools
    tools = [
        *regular_tools,
        filesystem_toolset,
    ]
    
    # Create agent
    agent = LlmAgent(
        name="backend_tester",
        model=model,
        #planner=PlanReActPlanner(),
        include_contents='none',
        instruction=tester_instruction_provider,
        tools=tools,
        output_key=STATE_KEY_TESTER_RESULT,
        output_schema=TestAgentResult,
    )
    
    logger.info(
        "Testing Agent created",
        extra={
            "agent": "backend_tester",
            "phase": "create",
            "model": TESTER_MODEL,
            "workspace_root": workspace_root or str(SAMPLE_DASHBOARD_ROOT),
            "tests_root": str(TESTS_ROOT),
        }
    )
    
    return agent


def get_tester_agent() -> LlmAgent:
    """Get a configured Testing Agent instance."""
    return create_tester_agent()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main agent
    "create_tester_agent",
    "get_tester_agent",
    # Instruction provider
    "tester_instruction_provider",
    # State keys
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_CURRENT_ARTIFACT",
    "STATE_KEY_DEV_RESULT",
    "STATE_KEY_DEV_REPORT_PATH",
    "STATE_KEY_PREVIOUS_TEST_SUMMARY",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_TESTER_RESULT",
    # Constants
    "TESTER_MODEL",
]
