"""
File system constants and path validation for the Testing Agent.

Provides path constants for the tests/ directory and path validation
to ensure test files are created/modified only in allowed locations.

Note: For listing directories and reading files, use the shared MCP filesystem toolset.
"""
from __future__ import annotations

from pathlib import Path

from src.tools.utils import (
    SAMPLE_DASHBOARD_ROOT,
    TESTER_ALLOWED_PATHS,
    TESTS_ROOT,
    validate_path,
    get_relative_path,
)

# Re-export path constants for convenience
__all__ = [
    "SAMPLE_DASHBOARD_ROOT",
    "TESTS_ROOT",
    "ALLOWED_TEST_PATHS",
    "_validate_test_path",
    "_get_relative_test_path",
]

# Alias for module-local use
ALLOWED_TEST_PATHS = [str(p) for p in TESTER_ALLOWED_PATHS]


def _validate_test_path(
    requested_path: str | Path,
    allow_new: bool = False,
) -> tuple[bool, Path, str]:
    """
    Validate that a requested path is within allowed test paths.
    
    Wraps the shared validate_path function with test-specific allowed paths.
    
    Args:
        requested_path: The path the agent wants to access.
        allow_new: If True, allows paths that don't exist yet (for creation).
        
    Returns:
        Tuple of (is_valid, resolved_path, error_message).
        If valid, error_message is empty.
    """
    return validate_path(
        requested_path=requested_path,
        allowed_paths=TESTER_ALLOWED_PATHS,
        allow_new=allow_new,
    )


def _get_relative_test_path(path: Path) -> str:
    """
    Get a shorter display path relative to sample-dashboard for cleaner output.
    
    Args:
        path: Absolute path to convert.
        
    Returns:
        Relative path string if under sample-dashboard, otherwise absolute.
    """
    return get_relative_path(path, SAMPLE_DASHBOARD_ROOT)
