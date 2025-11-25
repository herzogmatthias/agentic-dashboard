from pathlib import Path
from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from phoenix.otel import register as register_phoenix
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
import json
from src.core.daytona_client import DaytonaSandboxSingleton
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

OUTPUT_KEY = "data_analysis_output"

tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)


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
            inspect_json_value_tool
        ],
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
        copied = DaytonaSandboxSingleton().copy_workspace_to_artifacts(
            local_artifacts_dir=Path(callback_context.state["run_dir"]) / "artifacts",
            remote_root="workspace/artifacts/data_analysis"
        )
        print(f"Copied data analysis artifacts: {copied}")
        copied.extend(
            DaytonaSandboxSingleton().copy_workspace_to_artifacts(
            local_artifacts_dir=Path(callback_context.state["run_dir"]) / "cleaned",
            remote_root="workspace/cleaned"
        )
        )
        callback_context.state[OUTPUT_KEY]["additional_artifacts_path"] = copied

    except Exception as e:
        print(f"Error copying data analysis artifacts: {e}")
    finally:
        #DaytonaSandboxSingleton().stop_and_archive(copy_artifacts=True)
        pass
    
    output = callback_context.state[OUTPUT_KEY]

    # Option 1: return as pretty JSON text
    return types.Content(
        role="model",
        parts=[types.Part(text=json.dumps(output, indent=2))]
    )
