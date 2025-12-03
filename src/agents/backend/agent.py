"""
Backend Agent - Creates Next.js API routes and TypeScript models.

This agent is responsible for implementing the data layer of the dashboard
by creating API routes, TypeScript models, and utilities in the sample-dashboard
Next.js project.
"""

from pathlib import Path
from typing import Any, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as gt
from phoenix.otel import register as register_phoenix
from src.agents.backend.prompts import build_backend_agent_prompt
from src.core.logging import get_logger
from src.tools.backend import (
    # Data access tools
    get_sample_rows_tool,
    read_data_profile_tool,
    read_dashboard_concept_tool,
    # Creation tools
    create_api_tool,
    create_model_tool,
    # Search tool
    search_content_tool,
    # Validation tools
    run_lint_tool,
    run_build_tool,
    # Manifest tool
    write_backend_manifest_tool,
    # MCP toolset factories
    create_filesystem_toolset,
    create_nextjs_docs_toolset,
    # Callback helper (not a tool)
    copy_data_to_project,
    # Constants
    SAMPLE_DASHBOARD_ROOT,
)
from src.tools.filesystem import (
    inspect_json_keys_tool,
    inspect_json_value_tool,
)

tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)

# State keys
STATE_KEY_RUN_ID = "run_id"
STATE_KEY_RUN_DIR = "run_dir"
STATE_KEY_DATA_PROFILE_PATH = "data_profile_path"
STATE_KEY_DASHBOARD_SPEC_PATH = "dashboard_spec_path"
STATE_KEY_CLEANED_DATA_FILES = "cleaned_data_files"
STATE_KEY_CLEANED_DATA_PATH = "cleaned_data_path"

# Default run directory for standalone testing
DEFAULT_TEST_RUN_DIR = Path("runs/run_20251202_115759")


def _get_cleaned_data_files(run_dir: Path) -> list[str]:
    """
    Get list of all cleaned data files from the run directory.
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        List of file paths relative to sample-dashboard/data/
    """
    cleaned_dir = run_dir / "cleaned"
    
    if not cleaned_dir.exists():
        return []
    
    files = []
    for f in cleaned_dir.iterdir():
        if f.is_file():
            # Return path as it will appear in sample-dashboard/data/
            files.append(f"sample-dashboard/data/{f.name}")
    
    return sorted(files)


def initialize_backend_state(callback_context: CallbackContext) -> Optional[gt.Content]:
    """
    Initialize session state for the Backend Agent.
    
    This callback:
    1. Sets up run_id and run_dir if not present (uses default for standalone testing)
    2. Sets data_profile_path and dashboard_spec_path
    3. Copies cleaned data files to sample-dashboard/data/
    4. Populates cleaned_data_files list
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to allow normal agent execution
    """
    try:
        state = callback_context.state
        
        # Use existing run_dir or default for standalone testing
        if STATE_KEY_RUN_DIR not in state or state[STATE_KEY_RUN_DIR] is None:
            # Standalone testing mode - use default test run
            run_dir = DEFAULT_TEST_RUN_DIR.resolve()
            state[STATE_KEY_RUN_DIR] = str(run_dir)
            state[STATE_KEY_RUN_ID] = DEFAULT_TEST_RUN_DIR.name
            logger.info(
                f"Backend agent using default test run: {run_dir}",
                extra={"agent": "backend", "phase": "init", "run_id": DEFAULT_TEST_RUN_DIR.name}
            )
        else:
            run_dir = Path(state[STATE_KEY_RUN_DIR])
        
        # Set data_profile_path if not present
        if STATE_KEY_DATA_PROFILE_PATH not in state or state[STATE_KEY_DATA_PROFILE_PATH] is None:
            data_profile_path = run_dir / "data_profile.md"
            if data_profile_path.exists():
                state[STATE_KEY_DATA_PROFILE_PATH] = str(data_profile_path.resolve())
        
        # Set dashboard_spec_path if not present
        if STATE_KEY_DASHBOARD_SPEC_PATH not in state or state[STATE_KEY_DASHBOARD_SPEC_PATH] is None:
            dashboard_spec_path = run_dir / "planner" / "dashboard_concept.json"
            if dashboard_spec_path.exists():
                state[STATE_KEY_DASHBOARD_SPEC_PATH] = str(dashboard_spec_path.resolve())
        
        # Copy cleaned data to sample-dashboard/data/
        # Build a plain dict from the state values (state is a proxy object, not a dict)
        state_dict = {
            STATE_KEY_RUN_DIR: state.get(STATE_KEY_RUN_DIR),
            STATE_KEY_CLEANED_DATA_PATH: state.get(STATE_KEY_CLEANED_DATA_PATH),
        }
        copy_result = copy_data_to_project(state_dict)
        if "error" in copy_result:
            logger.warning(
                f"Failed to copy data to project: {copy_result['error']}",
                extra={"agent": "backend", "phase": "init"}
            )
        else:
            logger.info(
                f"Copied {copy_result.get('total_files', 0)} files to sample-dashboard/data/",
                extra={"agent": "backend", "phase": "init", "files": copy_result.get('total_files', 0)}
            )
        
        # Populate cleaned_data_files list
        cleaned_files = _get_cleaned_data_files(run_dir)
        state[STATE_KEY_CLEANED_DATA_FILES] = cleaned_files
        
        logger.info(
            f"Backend agent state initialized",
            extra={
                "agent": "backend",
                "phase": "init",
                "run_dir": str(run_dir),
                "data_profile_path": state.get(STATE_KEY_DATA_PROFILE_PATH),
                "dashboard_spec_path": state.get(STATE_KEY_DASHBOARD_SPEC_PATH),
                "cleaned_files_count": len(cleaned_files),
            }
        )
        
    except Exception as e:
        logger.exception(
            f"Failed to initialize backend state: {e}",
            extra={"agent": "backend", "phase": "init"}
        )
    
    return None


async def backend_instruction_provider(context: ReadonlyContext) -> str:
    """
    Dynamic instruction provider that injects session state into the prompt.
    
    Manually extracts state values and passes them to build_backend_agent_prompt
    to avoid ADK's buggy regex-based template substitution.
    
    Args:
        context: ReadonlyContext with access to session state
        
    Returns:
        Prompt string with state values injected
    """
    state = context.state
    
    # Extract state values with defaults
    cleaned_files = state.get(STATE_KEY_CLEANED_DATA_FILES, [])
    if isinstance(cleaned_files, list):
        cleaned_data_files = ", ".join(cleaned_files) if cleaned_files else "(none found)"
    else:
        cleaned_data_files = str(cleaned_files) if cleaned_files else "(none found)"
    
    data_profile_path = state.get(STATE_KEY_DATA_PROFILE_PATH, "(not set)")
    dashboard_spec_path = state.get(STATE_KEY_DASHBOARD_SPEC_PATH, "(not set)")
    
    # Get project root as absolute path
    project_root = str(SAMPLE_DASHBOARD_ROOT.resolve())
    
    return build_backend_agent_prompt(
        cleaned_data_files=cleaned_data_files,
        data_profile_path=data_profile_path,
        dashboard_spec_path=dashboard_spec_path,
        project_root=project_root,
    )


def create_backend_agent() -> LlmAgent:
    """
    Create and configure the Backend Agent.
    
    The Backend Agent uses:
    - Custom tools for file creation (create_api, create_model)
    - MCP filesystem tools for read/write/edit operations
    - Data access tools for reading pipeline artifacts
    - Validation tools for lint/build checking
    - JSON inspection tools for exploring data files
    
    Returns:
        Configured LlmAgent instance
    """
    # Use LiteLlm model like other agents
    model = LiteLlm(model="gpt-5-mini")
    
    # Collect all tools
    tools = [
        # Data access tools
        get_sample_rows_tool,
        read_data_profile_tool,
        read_dashboard_concept_tool,
        # JSON inspection tools
        #inspect_json_keys_tool,
        #inspect_json_value_tool,
        # Creation tools
        create_api_tool,
        create_model_tool,
        # Search tool
        search_content_tool,
        # Validation tools
        run_lint_tool,
        run_build_tool,
        # Manifest tool
        write_backend_manifest_tool,
        # MCP toolsets
        create_filesystem_toolset(),
        #create_nextjs_docs_toolset(),
    ]
    
    agent = LlmAgent(
        name="backend",
        model=model,
        instruction=backend_instruction_provider,
        tools=tools,
        before_agent_callback=initialize_backend_state,
    )
    
    logger.info(
        "Backend agent created",
        extra={"agent": "backend", "phase": "create", "model": "gpt-5-mini"}
    )
    
    return agent


# Convenience function for testing
def get_backend_agent() -> LlmAgent:
    """Get a configured Backend Agent instance."""
    return create_backend_agent()
