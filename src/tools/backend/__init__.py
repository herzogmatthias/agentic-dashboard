"""Backend Agent tools for file system operations, creation, validation, and manifest generation.

Note: Read/write/edit/list operations are handled by the MCP filesystem server.
This module provides only:
- search_content: Scoped content search within sample-dashboard
- create_api, create_model: Domain-specific file creation with validation
- Data access tools: For reading pipeline artifacts
- Validation tools: Syntax checking, lint, and build
- Next.js docs: MCP integration with Next.js DevTools MCP server
- Filesystem MCP: MCP toolset for file read/write/edit operations
"""

from src.tools.backend.filesystem import (
    search_content,
    search_content_tool,
    ALLOWED_PATHS,
)

from src.tools.backend.filesystem_mcp import (
    create_filesystem_toolset,
    create_filesystem_toolset_with_run_dir,
    FILESYSTEM_MCP_PACKAGE,
    SAMPLE_DASHBOARD_ROOT,
    ALLOWED_DIRECTORIES,
    EXPOSED_TOOLS as FILESYSTEM_EXPOSED_TOOLS,
    CONNECTION_TIMEOUT as FILESYSTEM_CONNECTION_TIMEOUT,
)

from src.tools.backend.data_access import (
    MAX_SAMPLE_ROWS,
    get_sample_rows,
    get_sample_rows_tool,
    inspect_json_preview_tool,  # Re-exported from shared
    copy_data_to_project,  # Callback helper, not a tool
)

from src.tools.shared import (
    inspect_json_preview,
    TOKEN_THRESHOLD,
)

from src.tools.backend.creation import (
    create_api,
    create_api_tool,
    create_model,
    create_model_tool,
)

from src.tools.backend.validation import (
    run_lint,
    run_lint_tool,
    run_type_check,
    run_type_check_tool,
    run_build,
    run_build_tool,
    LINT_TIMEOUT,
    TYPE_CHECK_TIMEOUT,
    BUILD_TIMEOUT,
)

from src.tools.backend.nextjs_docs import (
    create_nextjs_docs_toolset,
    call_init as call_nextjs_init,
    NEXTJS_DEVTOOLS_PACKAGE,
    EXPOSED_TOOLS as NEXTJS_EXPOSED_TOOLS,
    CONNECTION_TIMEOUT as NEXTJS_CONNECTION_TIMEOUT,
)

from src.tools.backend.manifest import (
    write_backend_manifest,
    write_backend_manifest_tool,
    DEV_OUTPUT_DIR,
    MANIFEST_FILENAME,
)

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
    # Data access tools
    "get_sample_rows_tool",
    "inspect_json_preview_tool",
    # Creation functions
    "create_api",
    "create_model",
    # Creation tools
    "create_api_tool",
    "create_model_tool",
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
    # Manifest functions
    "write_backend_manifest",
    # Manifest tools
    "write_backend_manifest_tool",
    # Constants - manifest
    "DEV_OUTPUT_DIR",
    "MANIFEST_FILENAME",
]
