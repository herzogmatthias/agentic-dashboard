"""Backend Dev Agent tools for file system operations, creation, validation, and data access.

This module consolidates all tools needed by the Backend Dev Agent:
- Filesystem: Path constants, content search, MCP filesystem toolset
- Creation: create_api, create_model, create_helper
- Validation: run_lint, run_type_check, run_build
- Data access: get_sample_rows, inspect_json_preview
- Next.js docs: MCP integration with Next.js DevTools

Note: Read/write/edit operations are handled by the MCP filesystem server.
"""

from src.tools.backend_dev.filesystem import (
    search_content,
    search_content_tool,
    ALLOWED_PATHS,
    SAMPLE_DASHBOARD_ROOT,
    _validate_path,
    _get_relative_display_path,
)

from src.tools.backend_dev.filesystem_mcp import (
    create_filesystem_toolset,
    create_filesystem_toolset_with_run_dir,
    FILESYSTEM_MCP_PACKAGE,
    ALLOWED_DIRECTORIES,
    EXPOSED_TOOLS as FILESYSTEM_EXPOSED_TOOLS,
    CONNECTION_TIMEOUT as FILESYSTEM_CONNECTION_TIMEOUT,
)

from src.tools.backend_dev.data_access import (
    MAX_SAMPLE_ROWS,
    get_sample_rows,
    get_sample_rows_tool,
    load_data_profile,
    load_data_profile_tool,
    inspect_json_preview_tool,  # Re-exported from shared
    copy_data_to_project,  # Callback helper, not a tool
)

from src.tools.shared import (
    inspect_json_preview,
    TOKEN_THRESHOLD,
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
    LINT_TIMEOUT,
    TYPE_CHECK_TIMEOUT,
    BUILD_TIMEOUT,
    _check_typescript_syntax,
)

from src.tools.backend_dev.nextjs_docs import (
    create_nextjs_docs_toolset,
    call_init as call_nextjs_init,
    NEXTJS_DEVTOOLS_PACKAGE,
    EXPOSED_TOOLS as NEXTJS_EXPOSED_TOOLS,
    CONNECTION_TIMEOUT as NEXTJS_CONNECTION_TIMEOUT,
)

from typing import Any


# ============================================================================
# Tool Aggregation for Backend Dev Agent
# ============================================================================

def get_dev_tools() -> tuple[list, Any]:
    """
    Get all tools for the Backend Dev Agent.
    
    Returns a tuple of (regular_tools, mcp_toolset) that the Backend Dev Agent needs:
    - Data exploration: get_sample_rows, inspect_json_preview, load_data_profile
    - File creation: create_api, create_model, create_helper
    - Content search: search_content
    - Validation: run_lint, run_type_check
    - MCP filesystem toolset for read/write/edit
    
    Returns:
        Tuple of (regular_tools_list, mcp_toolset).
        The caller should spread regular_tools and handle mcp_toolset appropriately.
    """
    tools = [
        # Data exploration
        get_sample_rows_tool,
        inspect_json_preview_tool,
        load_data_profile_tool,
        # File creation
        create_api_tool,
        create_model_tool,
        create_helper_tool,
        # Content search
        search_content_tool,
        # Validation
        run_lint_tool,
        run_type_check_tool,
    ]
    
    filesystem_toolset = create_filesystem_toolset()
    
    return tools, filesystem_toolset


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Search tool
    "search_content",
    "search_content_tool",
    # Filesystem MCP toolset factories
    "create_filesystem_toolset",
    "create_filesystem_toolset_with_run_dir",
    # Data access functions
    "get_sample_rows",
    "inspect_json_preview",
    "load_data_profile",
    # Data access tools
    "get_sample_rows_tool",
    "inspect_json_preview_tool",
    "load_data_profile_tool",
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
    # Next.js docs toolset factory
    "create_nextjs_docs_toolset",
    # Next.js docs manual init helper
    "call_nextjs_init",
    # Callback helpers (not tools)
    "copy_data_to_project",
    # Tool aggregation
    "get_dev_tools",
    # Constants - filesystem
    "ALLOWED_PATHS",
    "FILESYSTEM_MCP_PACKAGE",
    "SAMPLE_DASHBOARD_ROOT",
    "ALLOWED_DIRECTORIES",
    "FILESYSTEM_EXPOSED_TOOLS",
    "FILESYSTEM_CONNECTION_TIMEOUT",
    # Constants - data access
    "MAX_SAMPLE_ROWS",
    "TOKEN_THRESHOLD",
    # Constants - validation
    "LINT_TIMEOUT",
    "TYPE_CHECK_TIMEOUT",
    "BUILD_TIMEOUT",
    # Constants - nextjs docs
    "NEXTJS_DEVTOOLS_PACKAGE",
    "NEXTJS_EXPOSED_TOOLS",
    "NEXTJS_CONNECTION_TIMEOUT",
    # Internal helpers (for submodules)
    "_validate_path",
    "_get_relative_display_path",
    "_check_typescript_syntax",
]

