"""Backend Dev Agent tools for file system operations, creation, validation, and data access.

This module consolidates all tools needed by the Backend Dev Agent:
- Filesystem: Content search (local), MCP filesystem toolset (shared)
- Creation: create_api, create_model, create_helper
- Validation: run_lint, run_type_check, run_build, run_check_openapi
- Data access: load_data_profile, read_backend_manifest, inspect_json_preview
- Hono backend: OpenAPI registration via @hono/zod-openapi

Note: Read/write/edit operations are handled by the shared MCP filesystem server.
Note: Testing Agent tools are in a separate module: src.tools.tester
Note: copy_data_to_project is now in src.core.utils
"""

from src.tools.backend_dev.filesystem import (
    search_content,
    search_content_tool,
    _get_relative_display_path,
)

# Use shared filesystem MCP toolset
from src.tools.shared import (
    create_backend_dev_filesystem_toolset,
    inspect_json_preview,
    inspect_json_preview_tool,
    TOKEN_THRESHOLD,
    get_sample_rows,
    get_sample_rows_tool,
    FULL_ACCESS_TOOLS as FILESYSTEM_EXPOSED_TOOLS,
    CONNECTION_TIMEOUT as FILESYSTEM_CONNECTION_TIMEOUT,
    FILESYSTEM_MCP_PACKAGE,
)

from src.tools.utils import (
    SAMPLE_DASHBOARD_ROOT,
    BACKEND_DEV_ALLOWED_PATHS as ALLOWED_DIRECTORIES,
)

from src.tools.backend_dev.data_access import (
    load_data_profile,
    load_data_profile_tool,
    read_backend_manifest,
    read_backend_manifest_tool,
)

from src.tools.backend_dev.creation import (
    create_api,
    create_api_tool,
    create_model,
    create_model_tool,
    create_helper,
    create_helper_tool,
)

from src.tools.backend_dev.validation import (
    run_lint,
    run_lint_tool,
    run_type_check,
    run_type_check_tool,
    run_build,
    run_build_tool,
    run_check_openapi,
    run_check_openapi_tool,
    LINT_TIMEOUT,
    TYPE_CHECK_TIMEOUT,
    BUILD_TIMEOUT,
    _check_typescript_syntax,
)


from typing import Any


# ============================================================================
# Tool Aggregation for Backend Dev Agent
# ============================================================================

def get_backend_dev_tools(run_dir: str | None = None) -> list:
    """
    Get all FunctionTools for the Backend Dev Agent.
    
    Returns a list of tools that the Backend Dev Agent needs:
    - Data exploration: get_sample_rows, inspect_json_preview, load_data_profile, read_backend_manifest
    - File creation: create_api, create_model, create_helper
    - Content search: search_content
    - Validation: run_lint, run_type_check, run_check_openapi
    
    Note: For MCP filesystem tools (read_file, write_file, etc.), use
    `get_backend_dev_mcp_toolset(run_dir)` separately. The MCP toolset is
    limited to code/test paths and intentionally cannot reach the data folder.
    
    Args:
        run_dir: Optional run directory (reserved for future use).
    
    Returns:
        List of FunctionTool instances.
    """
    return [
        # Data exploration
        get_sample_rows_tool,
        inspect_json_preview_tool,
        load_data_profile_tool,
        read_backend_manifest_tool,
        # File creation
        create_api_tool,
        create_model_tool,
        create_helper_tool,
        # Content search
        search_content_tool,
        # Validation
        run_lint_tool,
        run_type_check_tool,
        run_check_openapi_tool,
    ]


def get_backend_dev_mcp_toolset(run_dir: str | None = None) -> Any:
    """
    Get the MCP filesystem toolset for the Backend Dev Agent.
    
    This provides MCP-based file operations (read_file, write_file,
    list_directory, etc.) with access restricted to:
    - src/api/** (Hono API routes)
    - src/models/** (TypeScript types/interfaces)
    - src/utils/** (Helper utilities)

    Note: The data folder is intentionally excluded; use get_sample_rows or
    inspect_json_preview for controlled data access.
    
    Args:
        run_dir: Optional run directory to add to allowed paths.
        
    Returns:
        McpToolset instance configured for backend dev agent.
    """
    return create_backend_dev_filesystem_toolset(run_dir=run_dir)


# Legacy alias for backward compatibility
get_dev_tools = get_backend_dev_tools


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Search tool
    "search_content",
    "search_content_tool",
    # Filesystem MCP toolset factory (from shared)
    "create_backend_dev_filesystem_toolset",
    "get_backend_dev_mcp_toolset",
    # Data access functions
    "get_sample_rows",
    "inspect_json_preview",
    "load_data_profile",
    "read_backend_manifest",
    # Data access tools
    "get_sample_rows_tool",
    "inspect_json_preview_tool",
    "load_data_profile_tool",
    "read_backend_manifest_tool",
    # Creation functions
    "create_api",
    "create_model",
    "create_helper",
    # Creation tools
    "create_api_tool",
    "create_model_tool",
    "create_helper_tool",
    # Validation functions
    "run_lint",
    "run_type_check",
    "run_build",
    # Validation tools
    "run_lint_tool",
    "run_type_check_tool",
    "run_build_tool",
    "run_check_openapi",
    "run_check_openapi_tool",
    # Tool aggregation
    "get_backend_dev_tools",
    "get_dev_tools",  # Legacy alias
    # Constants - filesystem
    "FILESYSTEM_MCP_PACKAGE",
    "SAMPLE_DASHBOARD_ROOT",
    "ALLOWED_DIRECTORIES",
    "FILESYSTEM_EXPOSED_TOOLS",
    "FILESYSTEM_CONNECTION_TIMEOUT",
    # Constants - data access
    "TOKEN_THRESHOLD",
    # Constants - validation
    "LINT_TIMEOUT",
    "TYPE_CHECK_TIMEOUT",
    "BUILD_TIMEOUT",
    # Internal helpers (for submodules)
    "_get_relative_display_path",
    "_check_typescript_syntax",
]

