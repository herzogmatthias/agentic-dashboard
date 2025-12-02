from pathlib import Path

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

from src.models.dashboard_concept_lite import DashboardConceptLite
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_dashboard(
    concept: DashboardConceptLite,
    tool_context: ToolContext,
) -> str:
    """
    Persist a DashboardConcept as JSON for downstream agents.

    - Accepts either a DashboardConceptLite instance or a raw dict.
    - If validation fails, does NOT raise; instead returns a descriptive error
      string so the calling agent can decide how to handle it.
    """

    # --- Ensure we have a Pydantic model, fail gracefully on validation errors ---
    if isinstance(concept, dict):
        try:
            concept = DashboardConceptLite.model_validate(concept)
        except ValidationError as exc:
            # Log full error for observability
            logger.error(
                "Failed to validate DashboardConceptLite",
                extra={
                    "agent": "planner",
                    "phase": "persist",
                    "validation_errors": exc.errors(),
                    "raw_concept": concept,
                },
            )
            # Surface a concise but useful message to the agent
            return (
                "DASHBOARD_CONCEPT_VALIDATION_ERROR: "
                "The dashboard concept returned by the planner did not match "
                "the expected schema DashboardConceptLite. "
                f"Details: {exc}"
            )

    run_dir_str = tool_context.state.get("run_dir")
    if not run_dir_str:
        # This is a real infrastructural error; better to raise
        raise RuntimeError("Session state missing 'run_dir'; cannot write dashboard concept.")

    planner_dir = Path(run_dir_str) / "planner"
    planner_dir.mkdir(parents=True, exist_ok=True)

    out_path = planner_dir / "dashboard_concept.json"
    json_str = concept.model_dump_json(indent=2)  # Pydantic v2
    out_path.write_text(json_str, encoding="utf-8")
    
    # Save path to state for downstream agents and validation
    tool_context.state["dashboard_spec_path"] = str(out_path.resolve())

    logger.info(
        "create_dashboard",
        extra={"agent": "planner", "phase": "persist", "path": str(out_path)},
    )

    return f"Dashboard concept written to: {out_path}"


create_dashboard_tool = FunctionTool(func=create_dashboard)
