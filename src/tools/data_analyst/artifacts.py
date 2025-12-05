import json
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.function_tool import FunctionTool
from pathlib import Path
from pydantic import ValidationError
from src.core.logging import get_logger
from src.models.cleaning_summary import CleaningSummary
from src.models.data_profile import DataProfile
from src.models.metrics_summary import MetricsSummary

logger = get_logger(__name__)


def write_cleaning_summary(
    summary: CleaningSummary,
    tool_context: ToolContext,
) -> str:
    """
    Save a CleaningSummary JSON file to the host run directory.
    Requires `run_dir` to be present in session state.
    
    Also saves the path to state["cleaning_summary_path"] for templating in other agent prompts.
    
    Args:
        summary: CleaningSummary Pydantic model with cleaning details
    """
    if tool_context is None or "run_dir" not in tool_context.state:
        raise RuntimeError("Session state missing 'run_dir'; cannot write cleaning summary.")

    # Handle dict input from ADK (LLM passes JSON as dict)
    if isinstance(summary, dict):
        try:
            summary = CleaningSummary.model_validate(summary)
        except ValidationError as exc:
            logger.error(
                "Failed to validate CleaningSummary",
                extra={"agent": "data_analysis", "phase": "write_cleaning_summary", "errors": exc.errors()},
            )
            return f"VALIDATION_ERROR: {exc}"

    base_dir = Path(tool_context.state["run_dir"])
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "cleaning_summary.json"
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    
    # Save path to state for prompt templating
    tool_context.state["cleaning_summary_path"] = str(path.resolve())
    
    logger.info("write_cleaning_summary", extra={"agent": "data_analysis", "phase": "write_cleaning_summary", "path": str(path)})
    return str(path.resolve())


def write_data_profile(
    profile: DataProfile,
    tool_context: ToolContext,
) -> str:
    """
    Save a DataProfile JSON file to the host run directory.
    Requires `run_dir` to be present in session state.
    
    Also saves the path to state["data_profile_path"] for templating in other agent prompts.
    
    Args:
        profile: DataProfile Pydantic model with dataset profiling details
    """
    if tool_context is None or "run_dir" not in tool_context.state:
        raise RuntimeError("Session state missing 'run_dir'; cannot write data profile.")

    # Handle dict input from ADK (LLM passes JSON as dict)
    if isinstance(profile, dict):
        try:
            profile = DataProfile.model_validate(profile)
        except ValidationError as exc:
            logger.error(
                "Failed to validate DataProfile",
                extra={"agent": "data_analysis", "phase": "write_data_profile", "errors": exc.errors()},
            )
            return f"VALIDATION_ERROR: {exc}"

    base_dir = Path(tool_context.state["run_dir"])
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "data_profile.json"
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    
    # Save path to state for prompt templating
    tool_context.state["data_profile_path"] = str(path.resolve())
    
    logger.info("write_data_profile", extra={"agent": "data_analysis", "phase": "write_data_profile", "path": str(path)})
    return str(path.resolve())


def write_metrics_summary(
    summary: MetricsSummary,
    tool_context: ToolContext,
) -> str:
    """
    Save a MetricsSummary JSON file to the host run directory.
    This is for additional analysis artifacts (regressions, correlations, key metrics)
    that aren't directly in cleaned.csv.
    
    Requires `run_dir` to be present in session state.
    
    Also saves the path to state["metrics_summary_path"] for templating in other agent prompts.
    
    Args:
        summary: MetricsSummary Pydantic model with metrics and analysis results
    """
    if tool_context is None or "run_dir" not in tool_context.state:
        raise RuntimeError("Session state missing 'run_dir'; cannot write metrics summary.")

    # Handle dict input from ADK (LLM passes JSON as dict)
    if isinstance(summary, dict):
        try:
            summary = MetricsSummary.model_validate(summary)
        except ValidationError as exc:
            logger.error(
                "Failed to validate MetricsSummary",
                extra={"agent": "data_analysis", "phase": "write_metrics_summary", "errors": exc.errors()},
            )
            return f"VALIDATION_ERROR: {exc}"

    base_dir = Path(tool_context.state["run_dir"])
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "metrics_summary.json"
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    
    # Save path to state for prompt templating
    tool_context.state["metrics_summary_path"] = str(path.resolve())
    
    logger.info("write_metrics_summary", extra={"agent": "data_analysis", "phase": "write_metrics_summary", "path": str(path)})
    return str(path.resolve())


write_data_profile_tool = FunctionTool(func=write_data_profile)
write_cleaning_summary_tool = FunctionTool(func=write_cleaning_summary)
write_metrics_summary_tool = FunctionTool(func=write_metrics_summary)