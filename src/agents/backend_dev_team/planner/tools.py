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
    BackendTodoGroup,
    ArtifactOverallStatus,
    BackendArtifactKind,
    BackendTodoGroupKind,
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
    groups: list,
    valid_refs: set[str]
) -> list[str]:
    """
    Validate that all metrics_ref values in groups are valid dashboard_concept IDs.
    
    Args:
        groups: List of group inputs (dicts with artifacts array)
        valid_refs: Set of valid metrics_ref values
        
    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    
    for group in groups:
        artifacts = group.get("artifacts", []) if isinstance(group, dict) else group.artifacts
        for artifact in artifacts:
            artifact_dict = artifact if isinstance(artifact, dict) else artifact.model_dump()
            if artifact_dict.get("metrics_ref") and artifact_dict["metrics_ref"] not in valid_refs:
                errors.append(
                    f"Artifact '{artifact_dict['id']}' has invalid metrics_ref '{artifact_dict['metrics_ref']}'. "
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
        metrics_ref_errors = _validate_metrics_refs(todo_list.groups, valid_refs)
        if metrics_ref_errors:
            return {
                "success": False,
                "error": "Invalid metrics_ref values found",
                "details": metrics_ref_errors,
                "valid_refs": sorted(valid_refs),
            }
        
        now = datetime.utcnow()
        
        # Convert groups and artifacts to full models
        validated_groups = []
        total_artifact_count = 0
        route_count = 0
        helper_count = 0
        
        for group_input in todo_list.groups:
            # Handle both dict and GroupInput object
            group_dict = group_input if isinstance(group_input, dict) else group_input.model_dump()
            
            # Convert artifacts in this group
            group_artifacts = []
            for i, artifact_input in enumerate(group_dict.get("artifacts", [])):
                try:
                    # Handle both dict and ArtifactInput object
                    artifact_dict = artifact_input if isinstance(artifact_input, dict) else artifact_input.model_dump()
                    
                    # Convert QueryParamInput to QueryParamSpec if present
                    query_params = None
                    if artifact_dict.get("query_params"):
                        query_params = [
                            QueryParamSpec(
                                name=str(qp.get("name", "")) if isinstance(qp, dict) else qp.name,
                                type=(qp.get("type", "string") if isinstance(qp, dict) else qp.type),  # type: ignore
                                required=bool(qp.get("required", False)) if isinstance(qp, dict) else qp.required,
                                description=qp.get("description") if isinstance(qp, dict) else qp.description,
                                enum_values=qp.get("enum_values") if isinstance(qp, dict) else qp.enum_values,
                                default=qp.get("default") if isinstance(qp, dict) else qp.default,
                            )
                            for qp in artifact_dict.get("query_params", [])
                        ]
                    
                    # Convert ExpectedShapeInput to ExpectedShape if present
                    expected_shape = None
                    if artifact_dict.get("expected_shape"):
                        es = artifact_dict["expected_shape"]
                        es_dict = es if isinstance(es, dict) else es.model_dump()
                        fields = [
                            JsonFieldSpec(
                                name=str(f.get("name", "")) if isinstance(f, dict) else f.name,
                                type=(f.get("type", "string") if isinstance(f, dict) else f.type),  # type: ignore
                                nullable=bool(f.get("nullable", False)) if isinstance(f, dict) else f.nullable,
                                description=f.get("description") if isinstance(f, dict) else f.description,
                            )
                            for f in es_dict.get("fields", [])
                        ]
                        expected_shape = ExpectedShape(
                            kind=(es_dict.get("kind", "array")),  # type: ignore
                            fields=fields,
                            notes=es_dict.get("notes"),
                        )
                    
                    artifact = PlannerArtifactTodo(
                        id=artifact_dict["id"],
                        kind=BackendArtifactKind(artifact_dict["kind"]),
                        title=artifact_dict["title"],
                        description=artifact_dict.get("description"),
                        http_path=artifact_dict.get("http_path"),
                        http_method=artifact_dict.get("http_method"),
                        query_params=query_params,
                        metrics_ref=artifact_dict.get("metrics_ref"),
                        expected_shape=expected_shape,
                        canonical_query=artifact_dict.get("canonical_query"),
                        depends_on=artifact_dict.get("depends_on", []),
                        priority=artifact_dict.get("priority", 1),
                        tags=artifact_dict.get("tags", []),
                        # System fields
                        status=ArtifactOverallStatus.pending,
                        created_at=now,
                        updated_at=now,
                    )
                    group_artifacts.append(artifact)
                    
                    # Count artifact types
                    if artifact.kind == BackendArtifactKind.route:
                        route_count += 1
                    else:
                        helper_count += 1
                    total_artifact_count += 1
                    
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Invalid artifact in group '{group_dict['id']}' at index {i}: {str(e)}",
                    }
            
            # Create the group
            group = BackendTodoGroup(
                id=group_dict["id"],
                kind=BackendTodoGroupKind(group_dict["kind"]),
                label=group_dict["label"],
                description=group_dict.get("description"),
                artifacts=group_artifacts,
            )
            validated_groups.append(group)
        
        # Create the full todo list
        full_todo_list = PlannerTodoList(
            run_id=run_id,
            dashboard_goal=todo_list.dashboard_goal,
            audience=todo_list.audience,
            groups=validated_groups,
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
        
        # Count artifact types and log
        logger.info(
            f"Backend todo list created with {total_artifact_count} artifacts in {len(validated_groups)} groups",
            extra={
                "agent": "backend_planner",
                "run_id": run_id,
                "group_count": len(validated_groups),
                "artifact_count": total_artifact_count,
                "route_count": route_count,
                "helper_count": helper_count,
                "output_path": str(output_path),
            }
        )
        
        return {
            "success": True,
            "message": f"Created backend todo list with {total_artifact_count} artifacts in {len(validated_groups)} groups",
            "file_path": str(output_path),
            "artifact_count": total_artifact_count,
            "group_count": len(validated_groups),
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
