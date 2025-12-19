"""
Shared path constants and validation utilities.

This module provides common path definitions and validation helpers
used across different agent tool modules.
"""
from __future__ import annotations

from pathlib import Path


# ============================================================================
# Path Constants
# ============================================================================

# Base path to the Hono backend project (OpenAPIHono + zod-openapi)
SAMPLE_DASHBOARD_ROOT = Path("./test_dashboard/dashboard_backend").resolve()

# Allowed paths for Backend Dev Agent
# Hono backend uses src/api (routes), src/models (types), src/utils (helpers)
BACKEND_DEV_ALLOWED_PATHS: list[Path] = [
    SAMPLE_DASHBOARD_ROOT / "src" / "api",    # Hono API routes
    SAMPLE_DASHBOARD_ROOT / "src" / "models", # TypeScript models
    SAMPLE_DASHBOARD_ROOT / "src" / "utils",  # Helper utilities
]

# Allowed paths for Testing Agent
TESTER_ALLOWED_PATHS: list[Path] = [
    SAMPLE_DASHBOARD_ROOT / "tests" / "api",      # API route tests
    SAMPLE_DASHBOARD_ROOT / "tests" / "utils",    # Helper tests
    SAMPLE_DASHBOARD_ROOT / "tests" / "models",   # Model tests
    SAMPLE_DASHBOARD_ROOT / "tests",               # Root tests folder
    SAMPLE_DASHBOARD_ROOT / "src" / "api",        # Can read API routes (for reference)
    SAMPLE_DASHBOARD_ROOT / "src" / "utils",      # Can read helpers (for reference)
]

# Tests root directory
TESTS_ROOT = SAMPLE_DASHBOARD_ROOT / "tests"


# ============================================================================
# Path Validation Helpers
# ============================================================================


def validate_path(
    requested_path: str | Path,
    allowed_paths: list[Path],
    run_dir: str | None = None,
    allow_new: bool = False,
) -> tuple[bool, Path, str]:
    """
    Validate that a requested path is within allowed paths.
    
    Handles relative paths by resolving them against SAMPLE_DASHBOARD_ROOT
    or the run_dir if provided.
    
    Args:
        requested_path: The path the agent wants to access.
        allowed_paths: List of allowed directory paths.
        run_dir: Optional run directory from session state.
        allow_new: If True, allows paths that don't exist yet (for creation).
        
    Returns:
        Tuple of (is_valid, resolved_path, error_message).
        If valid, error_message is empty.
    """
    path_str = str(requested_path)
    
    # Handle relative paths
    if not Path(path_str).is_absolute():
        path_str = path_str.replace("\\", "/")
        
        if path_str.startswith("sample-dashboard/"):
            path = (SAMPLE_DASHBOARD_ROOT.parent / path_str).resolve()
        elif path_str.startswith(("data/", "src/", "tests/")):
            path = (SAMPLE_DASHBOARD_ROOT / path_str).resolve()
        else:
            potential_path = (SAMPLE_DASHBOARD_ROOT / path_str).resolve()
            if potential_path.exists() or allow_new:
                path = potential_path
            else:
                path = Path(requested_path).resolve()
    else:
        path = Path(requested_path).resolve()
    
    # Build list of allowed paths including run_dir if provided
    check_paths = list(allowed_paths)
    if run_dir:
        check_paths.append(Path(run_dir))
    
    for allowed_path in check_paths:
        allowed_resolved = allowed_path.resolve() if allowed_path.exists() else allowed_path
        
        if path == allowed_resolved:
            if allow_new or path.exists():
                return True, path, ""
            return False, path, f"Path does not exist: {path}"
        
        try:
            path.relative_to(allowed_resolved)
            if allow_new or path.exists():
                return True, path, ""
            return False, path, f"Path does not exist: {path}"
        except ValueError:
            continue
    
    return False, path, f"Path not in allowed locations: {path}"


def get_relative_path(path: Path, base: Path | None = None) -> str:
    """
    Get a shorter display path relative to a base for cleaner output.
    
    Args:
        path: Absolute path to convert.
        base: Base path for relative display. Defaults to SAMPLE_DASHBOARD_ROOT.
        
    Returns:
        Relative path string if under base, otherwise absolute.
    """
    base = base or SAMPLE_DASHBOARD_ROOT
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
