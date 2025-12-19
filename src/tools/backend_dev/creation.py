"""
File creation tools for the Backend Dev Agent.

Provides tools for creating API routes, TypeScript models, and helper/utility
files within the sample-dashboard Next.js project.

File editing operations are handled by the MCP filesystem server.
Files are validated for TypeScript syntax before being written.
"""
from __future__ import annotations

import html
import re
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.tools.utils.paths import SAMPLE_DASHBOARD_ROOT, validate_path, BACKEND_DEV_ALLOWED_PATHS
from src.tools.backend_dev.validation import _check_typescript_syntax

logger = get_logger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _unescape_html_entities(content: str) -> str:
    """
    Decode HTML entities that may have been escaped by the LLM.
    Converts &lt; to <, &gt; to >, &amp; to &, etc.
    This is a safety net for when agents escape special characters.
    """
    return html.unescape(content)


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
        r'export\s+(?:interface|type|const|function|class|enum|async\s+function)\s+\w+',
        r'export\s+\{[^}]+\}',
        r'export\s+default\s+',
    ]
    
    for pattern in export_patterns:
        if re.search(pattern, content):
            return True, ""
    
    return False, "Content must export at least one type, interface, const, function, class, or enum"


def _validate_hono_route_content(content: str) -> tuple[bool, str]:
    """
    Ensure Hono route modules include required OpenAPI registration patterns.
    Checks for:
    - createRoute(...)
    - export function register(app: OpenAPIHono)
    - app.openapi(route, ...)
    
    Note: c.req.valid(...) is NOT required since routes without params/query/json don't need it.
    """
    required_patterns = [
        r"createRoute\(",
        r"export\s+function\s+register\s*\(\s*app\s*:\s*OpenAPIHono\s*\)",
        r"app\.openapi\(",
    ]
    for pattern in required_patterns:
        if not re.search(pattern, content):
            return False, (
                "Content must include Hono route registration: "
                "createRoute(...), export function register(app: OpenAPIHono), "
                "and app.openapi(route, handler)."
            )
    return True, ""


# ============================================================================
# Tool Implementations
# ============================================================================


def create_api(
    route_path: str,
    content: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Create a new Hono API route module.
    
    Creates file at: {workspace}/src/api/{route_path}.ts
    
    The route_path should be a path under src/api, e.g.:
    - "users/getById" → src/api/users/getById.ts registering GET /users/{id}
    - "dashboard/kpis" → src/api/dashboard/kpis.ts
    
    Content MUST export a `route` created via `createRoute(...)` and a
    `register(app: OpenAPIHono)` that calls `app.openapi(route, handler)` and
    uses `c.req.valid(...)` for runtime validation.
    
    Args:
        route_path: Relative path under src/api (without extension).
        content: TypeScript content for the route module.
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    # Unescape HTML entities that may have been escaped by the LLM
    content = _unescape_html_entities(content)
    
    # Normalize the route path (no extension)
    route_path = route_path.lstrip("/\\").rstrip("/\\").replace(".ts", "")
    
    # Construct the full path (append .ts)
    api_root = SAMPLE_DASHBOARD_ROOT / "src" / "api"
    full_path = api_root / f"{route_path}.ts"
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = validate_path(
        requested_path=str(full_path),
        allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
        run_dir=run_dir,
        allow_new=True,
    )
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
    syntax_valid, syntax_errors = _check_typescript_syntax(content, f"{route_path}.ts")
    if not syntax_valid:
        logger.warning("create_api syntax check failed", extra={"route": route_path})
        return {
            "success": False,
            "error": f"TypeScript syntax error - file not created:\n{syntax_errors}",
            "path": str(full_path),
            "syntax_errors": syntax_errors,
        }
    
    hono_ok, hono_error = _validate_hono_route_content(content)
    if not hono_ok:
        return {
            "success": False,
            "error": hono_error,
            "path": str(full_path),
        }
    
    try:
        # Create parent directories if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(content, encoding="utf-8")
        
        relative_path = f"src/api/{route_path}.ts"
        endpoint = f"/api/{route_path}"
        logger.info(
            "create_api success",
            extra={"agent": "backend_dev", "path": relative_path, "endpoint": endpoint},
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "endpoint": endpoint,
            "message": f"Created Hono API route at {relative_path} (endpoint: {endpoint})",
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
    
    # Unescape HTML entities that may have been escaped by the LLM
    content = _unescape_html_entities(content)
    
    # Normalize the model name
    name = name.strip().replace(".ts", "")
    
    # Construct the full path
    models_dir = SAMPLE_DASHBOARD_ROOT / "src" / "models"
    full_path = models_dir / f"{name}.ts"
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = validate_path(
        requested_path=str(full_path),
        allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
        run_dir=run_dir,
        allow_new=True,
    )
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
            extra={"agent": "backend_dev", "path": relative_path},
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


def create_helper(
    name: str,
    content: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Create a new TypeScript helper/utility file in the lib directory.
    
    Creates file at: {workspace}/src/utils/{name}.ts
    
    Use this for shared utilities like data loading functions, formatters,
    aggregation helpers, etc. Content must export at least one function,
    type, interface, or const.
    
    Args:
        name: Name of the helper file (without .ts extension).
              Use semantic names like 'data_utils', 'formatters', 'aggregations'.
        content: TypeScript content for the helper file.
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    # Unescape HTML entities that may have been escaped by the LLM
    content = _unescape_html_entities(content)
    
    # Normalize the helper name
    name = name.strip().replace(".ts", "")
    
    # Construct the full path
    utils_dir = SAMPLE_DASHBOARD_ROOT / "src" / "utils"
    full_path = utils_dir / f"{name}.ts"
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = validate_path(
        requested_path=str(full_path),
        allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
        run_dir=run_dir,
        allow_new=True,
    )
    if not is_valid:
        logger.warning("create_helper blocked", extra={"path": str(full_path), "error": error})
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
        logger.warning("create_helper syntax check failed", extra={"helper": name})
        return {
            "success": False,
            "error": f"TypeScript syntax error - file not created:\n{syntax_errors}",
            "path": str(full_path),
            "syntax_errors": syntax_errors,
        }
    
    try:
        # Create lib directory if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(content, encoding="utf-8")
        
        relative_path = f"src/lib/{name}.ts"
        logger.info(
            "create_helper success",
            extra={"agent": "backend_dev", "path": relative_path},
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "message": f"Created helper at {relative_path}",
        }
        
    except Exception as exc:
        logger.error("create_helper failed", extra={"path": str(full_path), "error": str(exc)})
        return {
            "success": False,
            "error": f"Failed to create helper: {exc}",
            "path": str(full_path),
        }


# ============================================================================
# Tool Exports
# ============================================================================

create_api_tool = FunctionTool(func=create_api)
create_model_tool = FunctionTool(func=create_model)
create_helper_tool = FunctionTool(func=create_helper)
