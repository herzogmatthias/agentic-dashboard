"""Testing Agent tools for test file creation, execution, and context.

This module consolidates all tools needed by the Testing Agent:
- Filesystem MCP: Dynamic filesystem toolset for tests/ directory (read, write, list)
- Filesystem: Path constants and test path validation
- Creation: create_test for creating Jest test files
- Testing: run_npm_test for executing tests
- Context: read_dev_report, read_backend_manifest for understanding what to test
- Shared tools: get_sample_rows, delete_file, file_exists from shared module
"""
from typing import Any

# Import centralized path constants from tools/utils
from src.tools.utils import (
    SAMPLE_DASHBOARD_ROOT,
    TESTS_ROOT,
    TESTER_ALLOWED_PATHS,
)

# Import local filesystem validation helpers
from src.tools.tester.filesystem import (
    ALLOWED_TEST_PATHS,
    _validate_test_path,
    _get_relative_test_path,
)

# Import MCP filesystem factory from shared
from src.tools.shared import (
    create_tester_filesystem_toolset,
    READ_TOOLS,
    FULL_ACCESS_TOOLS,
    ALL_FILESYSTEM_TOOLS,
)

from src.tools.tester.creation import (
    create_test,
    create_test_tool,
)

from src.tools.tester.testing import (
    run_npm_test,
    run_npm_test_tool,
    TEST_TIMEOUT,
)

from src.tools.tester.context import (
    read_dev_report,
    read_dev_report_tool,
    read_backend_manifest,
    read_backend_manifest_tool,
)

# Re-export shared tools that the Testing Agent needs
from src.tools.shared import (
    get_sample_rows,
    get_sample_rows_tool,
    delete_file,
    delete_file_tool,
    file_exists,
    file_exists_tool,
)


# ============================================================================
# Tool Aggregation for Testing Agent
# ============================================================================

def get_tester_tools(run_dir: str | None = None) -> list[Any]:
    """
    Get all tools for the Testing Agent.
    
    Returns a list of tools that the Testing Agent needs:
    - Test creation: create_test
    - Test execution: run_npm_test
    - Context: read_dev_report, read_backend_manifest
    - Data access: get_sample_rows (for understanding expected data)
    - Filesystem: delete_file, file_exists
    
    Note: For MCP filesystem tools (read_file, write_file, list_directory),
    use `get_tester_mcp_toolset(run_dir)` separately as it returns an McpToolset
    that needs async initialization.
    
    Args:
        run_dir: Optional run directory for run-specific file access.
        
    Returns:
        List of FunctionTool instances for the Testing Agent.
    """
    return [
        # Test creation
        create_test_tool,
        # Test execution
        run_npm_test_tool,
        # Context
        read_dev_report_tool,
        read_backend_manifest_tool,
        # Data access (from shared)
        get_sample_rows_tool,
        # Filesystem (from shared)
        delete_file_tool,
        file_exists_tool,
    ]


def get_tester_mcp_toolset(
    run_dir: str | None = None,
    tool_filter: list[str] | None = None,
) -> Any:
    """
    Get the MCP filesystem toolset for the Testing Agent.
    
    This provides MCP-based file operations (read_file, write_file, 
    list_directory, etc.) with access restricted to:
    - tests/** (full access - read, write, create)
    - src/app/api/** (read-only - to understand what's being tested)
    - src/lib/** (read-only - to understand helpers)
    - data/** (read-only - to understand test data)
    
    Args:
        run_dir: Optional run directory for run-specific file access.
        tool_filter: Optional list of tool names to include. Defaults to FULL_ACCESS_TOOLS.
        
    Returns:
        McpToolset instance configured for tester agent.
    """
    return create_tester_filesystem_toolset(run_dir=run_dir, tool_filter=tool_filter)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Filesystem constants (from tools/utils)
    "SAMPLE_DASHBOARD_ROOT",
    "TESTS_ROOT",
    "TESTER_ALLOWED_PATHS",
    "ALLOWED_TEST_PATHS",
    # Filesystem helpers
    "_validate_test_path",
    "_get_relative_test_path",
    # MCP filesystem factory
    "create_tester_filesystem_toolset",
    "get_tester_mcp_toolset",
    "READ_TOOLS",
    "FULL_ACCESS_TOOLS",
    "ALL_FILESYSTEM_TOOLS",
    # Creation functions
    "create_test",
    # Creation tools
    "create_test_tool",
    # Testing functions
    "run_npm_test",
    # Testing tools
    "run_npm_test_tool",
    # Context functions
    "read_dev_report",
    "read_backend_manifest",
    # Context tools
    "read_dev_report_tool",
    "read_backend_manifest_tool",
    # Shared tools re-exported
    "get_sample_rows",
    "get_sample_rows_tool",
    "delete_file",
    "delete_file_tool",
    "file_exists",
    "file_exists_tool",
    # Tool aggregation
    "get_tester_tools",
    # Constants
    "TEST_TIMEOUT",
]
