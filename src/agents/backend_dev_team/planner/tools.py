"""
Backend Planner Agent tools.

Tools for creating and managing the backend artifact todo list.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.models.backend_planner_todos import (
    PlannerTodoList,
    PlannerArtifactTodo,
    ArtifactOverallStatus,
    BackendArtifactKind,
    QueryParamSpec,
    ExpectedShape,
    JsonFieldSpec,
)
from src.models.backend_planner_input import TodoListInput
from src.agents.backend_dev_team.planner.callbacks import (
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_BACKEND_TODO_LIST,
    STATE_KEY_BACKEND_TODOS_PATH,
)

logger = get_logger(__name__)

# Output directory name within run_dir
BACKEND_DEV_TEAM_DIR = "backend_dev_team"
BACKEND_TODOS_FILENAME = "backend_todos.json"

# Valid section keys for metrics_ref
VALID_SECTION_KEYS = {"kpis", "visuals", "global_filters"}


def _load_valid_metrics_refs(run_dir: Path) -> set[str]:
    """
    Load valid metrics_ref values from dashboard_concept.json.
    
    Valid refs are:
    - Section keys: 'kpis', 'visuals', 'global_filters'
    - KPI IDs: items in kpis[].id
    - Visual IDs: items in visuals[].id
    - Filter IDs: items in global_filters[].id
    
    Returns:
        Set of valid metrics_ref strings
    """
    valid_refs = set(VALID_SECTION_KEYS)
    
    dashboard_path = run_dir / "planner" / "dashboard_concept.json"
    if not dashboard_path.exists():
        logger.warning(
            f"dashboard_concept.json not found at {dashboard_path}, skipping metrics_ref validation"
        )
        return valid_refs  # Return just section keys if file missing
    
    try:
        with open(dashboard_path, "r", encoding="utf-8") as f:
            dashboard = json.load(f)
        
        # Extract IDs from each section
        for kpi in dashboard.get("kpis", []):
            if "id" in kpi:
                valid_refs.add(kpi["id"])
        
        for visual in dashboard.get("visuals", []):
            if "id" in visual:
                valid_refs.add(visual["id"])
        
        for gf in dashboard.get("global_filters", []):
            if "id" in gf:
                valid_refs.add(gf["id"])
        
        logger.debug(
            f"Loaded {len(valid_refs)} valid metrics_ref values from dashboard_concept",
            extra={"valid_refs_count": len(valid_refs)}
        )
        
    except Exception as e:
        logger.warning(
            f"Failed to parse dashboard_concept.json: {e}, skipping metrics_ref validation"
        )
    
    return valid_refs


def _validate_metrics_refs(
    artifacts: list,
    valid_refs: set[str]
) -> list[str]:
    """
    Validate that all metrics_ref values are valid dashboard_concept IDs.
    
    Args:
        artifacts: List of artifact inputs
        valid_refs: Set of valid metrics_ref values
        
    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    
    for artifact in artifacts:
        if artifact.metrics_ref and artifact.metrics_ref not in valid_refs:
            errors.append(
                f"Artifact '{artifact.id}' has invalid metrics_ref '{artifact.metrics_ref}'. "
                f"Must be one of: {', '.join(sorted(valid_refs))}"
            )
    
    return errors


def create_backend_todo_list(
    todo_list: TodoListInput,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Create and persist the backend artifact todo list.
    
    This tool takes the barebone TodoListInput (no system fields), converts it
    to the full PlannerTodoList with auto-populated system fields, saves to JSON,
    and stores in session state.
    
    Args:
        todo_list: TodoListInput with dashboard_goal, audience, and artifacts.
        tool_context: ADK tool context with state access
        
    Returns:
        Confirmation with file path and artifact count, or error details
    """
    try:
        state = tool_context.state
        run_dir_str = state.get(STATE_KEY_RUN_DIR)
        run_id = state.get(STATE_KEY_RUN_ID)
        
        if not run_dir_str:
            return {
                "success": False,
                "error": "No run_dir in state. Cannot save todo list.",
            }
        
        run_dir = Path(run_dir_str)
        
        # Generate run_id from run_dir name if not present
        if not run_id:
            run_id = run_dir.name
        
        # Validate metrics_ref values against dashboard_concept
        valid_refs = _load_valid_metrics_refs(run_dir)
        metrics_ref_errors = _validate_metrics_refs(todo_list.artifacts, valid_refs)
        if metrics_ref_errors:
            return {
                "success": False,
                "error": "Invalid metrics_ref values found",
                "details": metrics_ref_errors,
                "valid_refs": sorted(valid_refs),
            }
        
        now = datetime.utcnow()
        
        # Convert barebone artifacts to full PlannerArtifactTodo
        validated_artifacts = []
        for i, artifact_input in enumerate(todo_list.artifacts):
            try:
                # Convert QueryParamInput to QueryParamSpec if present
                query_params = None
                if artifact_input.query_params:
                    query_params = [
                        QueryParamSpec(
                            name=qp.name,
                            type=qp.type,
                            required=qp.required,
                            description=qp.description,
                            enum_values=qp.enum_values,
                            default=qp.default,
                        )
                        for qp in artifact_input.query_params
                    ]
                
                # Convert ExpectedShapeInput to ExpectedShape if present
                expected_shape = None
                if artifact_input.expected_shape:
                    fields = [
                        JsonFieldSpec(
                            name=f.name,
                            type=f.type,
                            nullable=f.nullable,
                            description=f.description,
                        )
                        for f in artifact_input.expected_shape.fields
                    ]
                    expected_shape = ExpectedShape(
                        kind=artifact_input.expected_shape.kind,
                        fields=fields,
                        notes=artifact_input.expected_shape.notes,
                    )
                
                artifact = PlannerArtifactTodo(
                    id=artifact_input.id,
                    kind=BackendArtifactKind(artifact_input.kind),
                    title=artifact_input.title,
                    description=artifact_input.description,
                    http_path=artifact_input.http_path,
                    http_method=artifact_input.http_method,
                    query_params=query_params,
                    metrics_ref=artifact_input.metrics_ref,
                    expected_shape=expected_shape,
                    canonical_query=artifact_input.canonical_query,
                    depends_on=artifact_input.depends_on,
                    priority=artifact_input.priority,
                    tags=artifact_input.tags,
                    # System fields
                    status=ArtifactOverallStatus.pending,
                    created_at=now,
                    updated_at=now,
                )
                validated_artifacts.append(artifact)
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Invalid artifact at index {i} (id={artifact_input.id}): {str(e)}",
                }
        
        # Create the full todo list
        full_todo_list = PlannerTodoList(
            run_id=run_id,
            dashboard_goal=todo_list.dashboard_goal,
            audience=todo_list.audience,
            artifacts=validated_artifacts,
            created_at=now,
            updated_at=now,
        )
        
        # Create output directory
        output_dir = run_dir / BACKEND_DEV_TEAM_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON file
        output_path = output_dir / BACKEND_TODOS_FILENAME
        
        # Convert to dict for JSON serialization
        todo_dict = full_todo_list.model_dump(mode="json")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(todo_dict, f, indent=2, default=str)
        
        # Store in session state
        state[STATE_KEY_BACKEND_TODO_LIST] = todo_dict
        state[STATE_KEY_BACKEND_TODOS_PATH] = str(output_path)
        
        # Count artifact types
        route_count = sum(1 for a in validated_artifacts if a.kind == BackendArtifactKind.route)
        helper_count = sum(1 for a in validated_artifacts if a.kind == BackendArtifactKind.helper)
        
        logger.info(
            f"Backend todo list created with {len(validated_artifacts)} artifacts",
            extra={
                "agent": "backend_planner",
                "run_id": run_id,
                "artifact_count": len(validated_artifacts),
                "route_count": route_count,
                "helper_count": helper_count,
                "output_path": str(output_path),
            }
        )
        
        return {
            "success": True,
            "message": f"Created backend todo list with {len(validated_artifacts)} artifacts",
            "file_path": str(output_path),
            "artifact_count": len(validated_artifacts),
            "route_count": route_count,
            "helper_count": helper_count,
            "run_id": run_id,
        }
        
    except Exception as e:
        logger.exception(
            f"Failed to create backend todo list: {e}",
            extra={"agent": "backend_planner"}
        )
        return {
            "success": False,
            "error": f"Failed to create todo list: {str(e)}",
        }


# Create FunctionTool wrapper
create_backend_todo_list_tool = FunctionTool(create_backend_todo_list)
