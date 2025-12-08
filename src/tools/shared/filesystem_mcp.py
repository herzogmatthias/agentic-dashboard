"""
Shared MCP Filesystem Server integration.

Provides file operations (read, write, edit, list, tree) via the Anthropic MCP filesystem server.
https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem

This module provides a configurable filesystem toolset that can be used by different agents
with different allowed paths and tool filters.

Usage:
    from src.tools.shared.filesystem_mcp import create_filesystem_toolset
    from src.tools.utils import BACKEND_DEV_ALLOWED_PATHS, TESTER_ALLOWED_PATHS
    
    # For Backend Dev Agent
    toolset = create_filesystem_toolset(
        allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
        tool_filter=["read_file", "write_file", "edit_file", "list_directory"],
    )
    
    # For Testing Agent (read-heavy, limited write)
    toolset = create_filesystem_toolset(
        allowed_paths=TESTER_ALLOWED_PATHS,
        tool_filter=["read_file", "list_directory", "directory_tree"],
    )
"""
from __future__ import annotations

from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters


# ============================================================================
# Constants
# ============================================================================

# MCP filesystem server NPM package
FILESYSTEM_MCP_PACKAGE = "@modelcontextprotocol/server-filesystem"

# Connection timeout (seconds)
CONNECTION_TIMEOUT = 30

# All available tools from the MCP filesystem server
ALL_FILESYSTEM_TOOLS = [
    "read_file",           # Read file contents
    "write_file",          # Create new files
    "edit_file",           # Modify existing files (search/replace)
    "list_directory",      # List directory contents
    "list_allowed_directories",  # Show allowed directories
    "directory_tree",      # Get directory structure
    "read_multiple_files", # Read multiple files at once
    "search_files",        # Search for files matching pattern
    "get_file_info",       # Get file metadata
    "move_file",           # Move or rename files
]

# Default tools for read-heavy operations
READ_TOOLS = [
    "read_file",
    "read_multiple_files",
    "list_directory",
    "directory_tree",
    "list_allowed_directories",
    "search_files",
    "get_file_info",
]

# Default tools for full file operations
FULL_ACCESS_TOOLS = [
    "read_file",
    "write_file",
    "edit_file",
    "list_directory",
    "list_allowed_directories",
    "directory_tree",
    "read_multiple_files",
    "search_files",
]


# ============================================================================
# Toolset Factory
# ============================================================================


def create_filesystem_toolset(
    allowed_paths: list[Path] | list[str],
    tool_filter: list[str] | None = None,
    additional_paths: list[Path] | None = None,
    timeout: int = CONNECTION_TIMEOUT,
) -> McpToolset:
    """
    Create a McpToolset for filesystem operations with specified allowed paths.
    
    Args:
        allowed_paths: List of paths the agent is allowed to access.
            These are passed to the MCP server as allowed directories.
        tool_filter: Optional list of tool names to expose. If None,
            FULL_ACCESS_TOOLS are used. Use READ_TOOLS for read-only access.
        additional_paths: Optional additional paths to allow (e.g., run directories).
        timeout: Connection timeout in seconds.
    
    Returns:
        McpToolset configured for @modelcontextprotocol/server-filesystem.
    
    Example:
        from src.tools.utils import BACKEND_DEV_ALLOWED_PATHS
        
        # Full access for backend dev
        toolset = create_filesystem_toolset(
            allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
        )
        
        # Read-only for inspection
        toolset = create_filesystem_toolset(
            allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
            tool_filter=READ_TOOLS,
        )
        
        # Add run directory
        toolset = create_filesystem_toolset(
            allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
            additional_paths=[Path("runs/run_123")],
        )
    """
    # Build the list of allowed paths as strings
    path_strings = [str(p) for p in allowed_paths]
    
    if additional_paths:
        path_strings.extend(str(p) for p in additional_paths)
    
    # Build args: npx -y @modelcontextprotocol/server-filesystem <paths...>
    args = ["-y", FILESYSTEM_MCP_PACKAGE] + path_strings
    
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=args,
            ),
            timeout=timeout,
        ),
        tool_filter=tool_filter or FULL_ACCESS_TOOLS,
    )


def create_backend_dev_filesystem_toolset(
    run_dir: str | Path | None = None,
    tool_filter: list[str] | None = None,
) -> McpToolset:
    """
    Create a filesystem toolset configured for the Backend Dev Agent.
    
    Uses BACKEND_DEV_ALLOWED_PATHS with optional run directory.
    
    Args:
        run_dir: Optional run directory to add to allowed paths.
        tool_filter: Optional tool filter. Defaults to FULL_ACCESS_TOOLS.
    
    Returns:
        McpToolset for backend dev operations.
    """
    from src.tools.utils import BACKEND_DEV_ALLOWED_PATHS
    
    additional = [Path(run_dir)] if run_dir else None
    
    return create_filesystem_toolset(
        allowed_paths=BACKEND_DEV_ALLOWED_PATHS,
        tool_filter=tool_filter,
        additional_paths=additional,
    )


def create_tester_filesystem_toolset(
    run_dir: str | Path | None = None,
    tool_filter: list[str] | None = None,
) -> McpToolset:
    """
    Create a filesystem toolset configured for the Testing Agent.
    
    Uses TESTER_ALLOWED_PATHS with optional run directory.
    By default, uses FULL_ACCESS_TOOLS since testers need to create test files.
    
    Args:
        run_dir: Optional run directory to add to allowed paths.
        tool_filter: Optional tool filter. Defaults to FULL_ACCESS_TOOLS.
    
    Returns:
        McpToolset for tester operations.
    """
    from src.tools.utils import TESTER_ALLOWED_PATHS
    
    additional = [Path(run_dir)] if run_dir else None
    
    return create_filesystem_toolset(
        allowed_paths=TESTER_ALLOWED_PATHS,
        tool_filter=tool_filter,
        additional_paths=additional,
    )
