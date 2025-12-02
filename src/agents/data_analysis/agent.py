from pathlib import Path
from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from phoenix.otel import register as register_phoenix
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
import json
from src.core.daytona_client import DaytonaSandboxSingleton
from src.core.logging import get_logger
from src.models.data_analysis_agent_output import DataAnalysisOutput
from src.prompts.system_prompts import build_analysis_agent_prompt
from src.tools.filesystem import (
    inspect_directory_tool,
    inspect_json_keys_tool,
    inspect_json_value_tool,
    read_snippet_tool,
    run_python_tool,
    write_cleaning_summary_tool,
    write_data_profile_tool,
    write_metrics_summary_tool,
)
from src.tools.delegation import summarize_actions_tool

OUTPUT_KEY = "data_analysis_output"

tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)


def create_data_analysis_agent() -> LlmAgent:
    model = LiteLlm(model="gpt-5-mini")

    agent = LlmAgent(
        name="data_analysis_agent",
        model=model,
        instruction=build_analysis_agent_prompt(),
        tools=[
            run_python_tool,
            inspect_directory_tool,
            read_snippet_tool,
            write_data_profile_tool,
            write_cleaning_summary_tool,
            write_metrics_summary_tool,
            inspect_json_keys_tool,
            inspect_json_value_tool,
            summarize_actions_tool,
        ],
        include_contents='none',
        after_agent_callback=copy_data_analysis_artifacts_after_agent,
        output_key=OUTPUT_KEY,
        output_schema=DataAnalysisOutput,
        description="Profiles, cleans, and exports dataset artifacts using a Daytona sandbox.",
    )

    return agent


def copy_data_analysis_artifacts_after_agent(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    - Read structured output from state[OUTPUT_KEY]
    - Normalize & filter additional_artifacts_path
    - Ensure cleaned.csv is always downloaded (if not listed, add it)
    - Filter out original data.csv
    - Copy remaining artifacts from sandbox to local run dir
    - Return None to preserve the original agent answer
    """
    try:
        intermediate_results = DaytonaSandboxSingleton().copy_workspace_to_artifacts(
            local_artifacts_dir=Path(callback_context.state["run_dir"]) / "artifacts",
            remote_root="workspace/artifacts/data_analysis"
        )
        logger.info("Copied data analysis artifacts", extra={"agent": "data_analysis", "phase": "copy_artifacts", "count": len(intermediate_results)})
        callback_context.state["data_analysis_intermediate_artifacts"] = intermediate_results
        results = DaytonaSandboxSingleton().copy_workspace_to_artifacts(
            local_artifacts_dir=Path(callback_context.state["run_dir"]) / "cleaned",
            remote_root="workspace/cleaned"
        )
        
        callback_context.state["additional_artifacts_path"] = results
        logger.info("Copied data analysis results", extra={"agent": "data_analysis", "phase": "copy_artifacts", "count": len(results)})
    except Exception as e:
        logger.exception("Error copying data analysis artifacts", extra={"agent": "data_analysis", "phase": "copy_artifacts"})
    finally:
        DaytonaSandboxSingleton().stop_and_archive(copy_artifacts=True)
        pass

    # Option 1: return as pretty JSON text
    return None