from pathlib import Path

from google.adk.tools import FunctionTool, ToolContext

from src.models.dashboard_concept_lite import DashboardConceptLite


def create_dashboard(
    concept: DashboardConceptLite,
    tool_context: ToolContext,
    filename: str = "dashboard_concept.json",
) -> str:
    """
    Persist a DashboardConcept as JSON for downstream agents.

    Requires session state to contain `run_dir`. Writes to {run_dir}/planner/{filename}.
    Returns the path to the written file as a string message.
    """
    run_dir_str = tool_context.state.get("run_dir")
    if not run_dir_str:
        raise RuntimeError("Session state missing 'run_dir'; cannot write dashboard concept.")

    planner_dir = Path(run_dir_str) / "planner"
    planner_dir.mkdir(parents=True, exist_ok=True)

    out_path = planner_dir / filename
    json_str = concept.model_dump_json(indent=2)  # Pydantic v2
    out_path.write_text(json_str, encoding="utf-8")

    return f"Dashboard concept written to: {out_path}"


create_dashboard_tool = FunctionTool(func=create_dashboard)
