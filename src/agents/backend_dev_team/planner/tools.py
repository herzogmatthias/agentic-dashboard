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
