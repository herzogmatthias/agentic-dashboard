"""
Shared tools used by multiple agents.

This module provides common tools that are reused across different agents:
- JSON preview and inspection
- Filesystem operations (delete, exists)
- Data access (sample rows)
- MCP filesystem toolset (dynamic allowed paths)
"""
from src.tools.shared.json_preview import (
    inspect_json_preview,
    inspect_json_preview_tool,
    TOKEN_THRESHOLD,
    _count_tokens,
    _minify_json,
)

from src.tools.shared.filesystem import (
    delete_file,
    delete_file_tool,
    file_exists,
    file_exists_tool,
)

from src.tools.shared.data_access import (
    get_sample_rows,
    get_sample_rows_tool,
    DEFAULT_MAX_SAMPLE_ROWS,
)

# Alias for backward compatibility - tests used MAX_SAMPLE_ROWS
MAX_SAMPLE_ROWS = DEFAULT_MAX_SAMPLE_ROWS

from src.tools.shared.filesystem_mcp import (
    create_filesystem_toolset,
    create_backend_dev_filesystem_toolset,
    create_tester_filesystem_toolset,
    FILESYSTEM_MCP_PACKAGE,
    CONNECTION_TIMEOUT,
    ALL_FILESYSTEM_TOOLS,
    READ_TOOLS,
    FULL_ACCESS_TOOLS,
)

__all__ = [
    # JSON preview
    "inspect_json_preview",
    "inspect_json_preview_tool",
    "TOKEN_THRESHOLD",
    "_count_tokens",
    "_minify_json",
    # Filesystem
    "delete_file",
    "delete_file_tool",
    "file_exists",
    "file_exists_tool",
    # Data access
    "get_sample_rows",
    "get_sample_rows_tool",
    "DEFAULT_MAX_SAMPLE_ROWS",
    "MAX_SAMPLE_ROWS",  # Backward compatibility alias
    # MCP Filesystem
    "create_filesystem_toolset",
    "create_backend_dev_filesystem_toolset",
    "create_tester_filesystem_toolset",
    "FILESYSTEM_MCP_PACKAGE",
    "CONNECTION_TIMEOUT",
    "ALL_FILESYSTEM_TOOLS",
    "READ_TOOLS",
    "FULL_ACCESS_TOOLS",
]
