"""
File creation tools for the Backend Agent.

Provides tools for creating API routes and TypeScript models
within the sample-dashboard Next.js project.

File editing operations are handled by the MCP filesystem server.
Files are validated for TypeScript syntax before being written.
"""
from __future__ import annotations

import re
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from src.core.logging import get_logger
from src.tools.backend.filesystem import SAMPLE_DASHBOARD_ROOT, _validate_path
from src.tools.backend.validation import _check_typescript_syntax

logger = get_logger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _validate_typescript_exports(content: str) -> tuple[bool, str]:
    """
    Validate that TypeScript content exports at least one type/interface/const.
    
    Args:
        content: TypeScript file content.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    # Look for export statements
    export_patterns = [
        r'export\s+(?:interface|type|const|function|class|enum)\s+\w+',
        r'export\s+\{[^}]+\}',
        r'export\s+default\s+',
    ]
    
    for pattern in export_patterns:
        if re.search(pattern, content):
            return True, ""
    
    return False, "Content must export at least one type, interface, const, function, class, or enum"


# ============================================================================
# Tool Implementations
# ============================================================================


def create_api(
    route_path: str,
    content: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Create a new API route file in the Next.js App Router structure.
    
    Creates file at: sample-dashboard/src/app/api/{route_path}/route.ts
    
    The route_path should be in Next.js notation:
    - "sales" → /api/sales endpoint (file: api/sales/route.ts)
    - "products/[id]" → /api/products/[id] endpoint
    - "dashboard/kpis" → /api/dashboard/kpis endpoint
    
    Args:
        route_path: Route path in Next.js notation. The filename route.ts is automatically appended.
        content: TypeScript content for the route file.
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    # Normalize the route path and remove any trailing route.ts if provided
    route_path = route_path.lstrip("/\\").rstrip("/\\")
    if route_path.endswith("/route.ts"):
        route_path = route_path[:-9]  # Remove /route.ts
    elif route_path.endswith("route.ts"):
        route_path = route_path[:-8]  # Remove route.ts
    
    # Construct the full path (always append route.ts)
    api_root = SAMPLE_DASHBOARD_ROOT / "src" / "app" / "api"
    full_path = api_root / route_path / "route.ts"
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = _validate_path(str(full_path), run_dir, allow_new=True)
    if not is_valid:
        logger.warning("create_api blocked", extra={"path": str(full_path), "error": error})
        return {"success": False, "error": error, "path": str(full_path)}
    
    # Check if file already exists
    if resolved_path.exists():
        return {
            "success": False,
            "error": f"Route already exists: {resolved_path}. Use the MCP filesystem edit_file tool to modify existing routes.",
            "path": str(resolved_path),
        }
    
    # Validate TypeScript syntax before writing
    syntax_valid, syntax_errors = _check_typescript_syntax(content, f"{route_path}/route.ts")
    if not syntax_valid:
        logger.warning("create_api syntax check failed", extra={"route": route_path})
        return {
            "success": False,
            "error": f"TypeScript syntax error - file not created:\n{syntax_errors}",
            "path": str(full_path),
            "syntax_errors": syntax_errors,
        }
    
    try:
        # Create parent directories if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(content, encoding="utf-8")
        
        relative_path = f"src/app/api/{route_path}/route.ts"
        endpoint = f"/api/{route_path}"
        logger.info(
            "create_api success",
            extra={"agent": "backend", "path": relative_path, "endpoint": endpoint},
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "endpoint": endpoint,
            "message": f"Created API route at {relative_path} (endpoint: {endpoint})",
        }
        
    except Exception as exc:
        logger.error("create_api failed", extra={"path": str(full_path), "error": str(exc)})
        return {
            "success": False,
            "error": f"Failed to create API route: {exc}",
            "path": str(full_path),
        }


def create_model(
    name: str,
    content: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Create a new TypeScript model file in the models directory.
    
    Creates file at: sample-dashboard/src/models/{name}.ts
    Content must export at least one type, interface, or const.
    
    Args:
        name: Name of the model file (without .ts extension).
        content: TypeScript content for the model file.
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    # Normalize the model name
    name = name.strip().replace(".ts", "")
    
    # Construct the full path
    models_dir = SAMPLE_DASHBOARD_ROOT / "src" / "models"
    full_path = models_dir / f"{name}.ts"
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = _validate_path(str(full_path), run_dir, allow_new=True)
    if not is_valid:
        logger.warning("create_model blocked", extra={"path": str(full_path), "error": error})
        return {"success": False, "error": error, "path": str(full_path)}
    
    # Check if file already exists
    if resolved_path.exists():
        return {
            "success": False,
            "error": f"File already exists: {resolved_path}. Use the MCP filesystem edit_file tool to modify existing files.",
            "path": str(resolved_path),
        }
    
    # Validate that content exports something
    is_valid_content, validation_error = _validate_typescript_exports(content)
    if not is_valid_content:
        return {
            "success": False,
            "error": validation_error,
            "path": str(full_path),
        }
    
    # Validate TypeScript syntax before writing
    syntax_valid, syntax_errors = _check_typescript_syntax(content, f"{name}.ts")
    if not syntax_valid:
        logger.warning("create_model syntax check failed", extra={"model": name})
        return {
            "success": False,
            "error": f"TypeScript syntax error - file not created:\n{syntax_errors}",
            "path": str(full_path),
            "syntax_errors": syntax_errors,
        }
    
    try:
        # Create models directory if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(content, encoding="utf-8")
        
        relative_path = f"src/models/{name}.ts"
        logger.info(
            "create_model success",
            extra={"agent": "backend", "path": relative_path},
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "message": f"Created model at {relative_path}",
        }
        
    except Exception as exc:
        logger.error("create_model failed", extra={"path": str(full_path), "error": str(exc)})
        return {
            "success": False,
            "error": f"Failed to create model: {exc}",
            "path": str(full_path),
        }


# ============================================================================
# Tool Exports
# ============================================================================

create_api_tool = FunctionTool(func=create_api)
create_model_tool = FunctionTool(func=create_model)
