"""
MCP Filesystem Server integration for the Backend Dev Agent.

Provides file operations (read, write, edit, list, tree) via the Anthropic MCP filesystem server.
https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem

Usage:
    from src.tools.backend_dev.filesystem_mcp import create_filesystem_toolset
    
    agent = LlmAgent(
        model="gemini-2.0-flash",
        name="backend_dev_agent",
        tools=[create_filesystem_toolset()],
    )

Available MCP Tools:
    - read_file: Read file contents
    - write_file: Create new files (prefer create_api/create_model for domain types)
    - edit_file: Modify existing files with search/replace
    - list_directory: List directory contents
    - directory_tree: Get directory structure
    - read_multiple_files: Read multiple files at once
    - search_files: Search for files matching pattern
    - get_file_info: Get file metadata
    - move_file: Move or rename files

Note:
    - McpToolset manages connection lifecycle automatically
    - Only paths within ALLOWED_DIRECTORIES can be accessed
    - For new API routes and models, prefer create_api/create_model tools
    - For editing existing files, use edit_file from this toolset
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

# Base path to the sample-dashboard project
SAMPLE_DASHBOARD_ROOT = Path("C:/Users/darks/Documents/agentic-dashboard/sample-dashboard")

# Allowed directories for the MCP filesystem server
# These paths are passed as arguments to the MCP server
# NOTE: data/ directory is NOT included - no write access to data files
# Data paths are provided via state templating and read via get_sample_rows tool
ALLOWED_DIRECTORIES = [
    SAMPLE_DASHBOARD_ROOT / "src" / "app" / "api",  # API routes
    SAMPLE_DASHBOARD_ROOT / "src" / "models",        # TypeScript models
    SAMPLE_DASHBOARD_ROOT / "src" / "lib",           # Utility functions
]

# Tools exposed to the agent
# The filesystem MCP server provides these tools:
EXPOSED_TOOLS = [
    "read_file",           # Read file contents
    "write_file",          # Create new files
    "edit_file",           # Modify existing files (search/replace)
    "list_directory",      # List directory contents
    "list_allowed_directories",
    "directory_tree",      # Get directory structure
    "read_multiple_files", # Read multiple files at once
    "search_files",        # Search for files matching pattern
]

# Connection timeout (seconds)
CONNECTION_TIMEOUT = 30


# ============================================================================
# Toolset Factory
# ============================================================================


def create_filesystem_toolset(
    additional_paths: list[Path] | None = None,
    tool_filter: list[str] | None = None,
) -> McpToolset:
    """
    Create a McpToolset for filesystem operations.
    
    Returns an McpToolset that provides file read/write/edit operations
    scoped to the allowed directories in the sample-dashboard project.
    
    Args:
        additional_paths: Optional additional paths to allow access to.
            Useful for adding run-specific directories.
        tool_filter: Optional list of tool names to expose. If None,
            all EXPOSED_TOOLS are available.
    
    Returns:
        McpToolset configured for @modelcontextprotocol/server-filesystem.
    
    Example:
        # Basic usage with default allowed paths
        toolset = create_filesystem_toolset()
        agent = LlmAgent(tools=[toolset])
        
        # Add run directory for artifacts
        run_dir = Path("runs/run_123")
        toolset = create_filesystem_toolset(additional_paths=[run_dir])
        
        # Filter to only read operations
        toolset = create_filesystem_toolset(
            tool_filter=["read_file", "list_directory", "directory_tree"]
        )
    """
    # Build the list of allowed paths
    allowed_paths = [str(p) for p in ALLOWED_DIRECTORIES]
    
    if additional_paths:
        allowed_paths.extend(str(p) for p in additional_paths)
    
    # Build args: npx -y @modelcontextprotocol/server-filesystem <paths...>
    args = ["-y", FILESYSTEM_MCP_PACKAGE] + allowed_paths
    
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=args,
            ),
            timeout=CONNECTION_TIMEOUT,
        ),
        tool_filter=tool_filter or EXPOSED_TOOLS,
    )


def create_filesystem_toolset_with_run_dir(run_dir: str | Path) -> McpToolset:
    """
    Create a filesystem toolset that includes a run directory.
    
    Convenience function that adds the run directory to the allowed paths,
    enabling the agent to read/write artifacts from the current run.
    
    Args:
        run_dir: Path to the current run directory (e.g., "runs/run_123").
    
    Returns:
        McpToolset with run directory added to allowed paths.
    
    Example:
        toolset = create_filesystem_toolset_with_run_dir("runs/run_20231201_120000")
        agent = LlmAgent(tools=[toolset])
    """
    run_path = Path(run_dir) if isinstance(run_dir, str) else run_dir
    return create_filesystem_toolset(additional_paths=[run_path])
