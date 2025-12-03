"""
File system constants and search tool for the Backend Agent.

Provides path constants and content search functionality.
Read/write/edit operations are handled by the MCP filesystem server.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from src.core.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# Path Constants
# ============================================================================

# Base path to the sample-dashboard Next.js project
SAMPLE_DASHBOARD_ROOT = Path("C:/Users/darks/Documents/agentic-dashboard/sample-dashboard")

# Allowed paths for Backend Agent file operations
# These should match the MCP filesystem server configuration
ALLOWED_PATHS: list[str] = [
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/src/app/api",
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/src/models",
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/src/lib",
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/data",
]


def _resolve_allowed_paths(run_dir: str | None = None) -> list[Path]:
    """
    Resolve allowed paths, substituting {run_dir} placeholder if provided.
    
    Args:
        run_dir: The current run directory from session state, or None.
        
    Returns:
        List of resolved Path objects for allowed paths.
    """
    resolved: list[Path] = []
    for path_template in ALLOWED_PATHS:
        if "{run_dir}" in path_template:
            if run_dir:
                resolved_path = path_template.replace("{run_dir}", run_dir)
                resolved.append(Path(resolved_path))
        else:
            resolved.append(Path(path_template))
    return resolved


def _validate_path(
    requested_path: str | Path,
    run_dir: str | None = None,
    allow_new: bool = False,
) -> tuple[bool, Path, str]:
    """
    Validate that a requested path is within allowed paths.
    
    Handles relative paths intelligently:
    - Paths starting with 'sample-dashboard/' are resolved relative to SAMPLE_DASHBOARD_ROOT's parent
    - Paths starting with 'data/', 'src/' are resolved relative to SAMPLE_DASHBOARD_ROOT
    - Absolute paths are used as-is
    
    Args:
        requested_path: The path the agent wants to access.
        run_dir: The current run directory from session state.
        allow_new: If True, allows paths that don't exist yet (for creation).
        
    Returns:
        Tuple of (is_valid, resolved_path, error_message).
        If valid, error_message is empty.
    """
    path_str = str(requested_path)
    
    # Handle relative paths - resolve them relative to SAMPLE_DASHBOARD_ROOT
    if not Path(path_str).is_absolute():
        # Normalize path separators
        path_str = path_str.replace("\\", "/")
        
        if path_str.startswith("sample-dashboard/"):
            # e.g., "sample-dashboard/data/cleaned.csv" -> resolve from parent of SAMPLE_DASHBOARD_ROOT
            path = (SAMPLE_DASHBOARD_ROOT.parent / path_str).resolve()
        elif path_str.startswith(("data/", "src/")):
            # e.g., "data/cleaned.csv" -> resolve from SAMPLE_DASHBOARD_ROOT
            path = (SAMPLE_DASHBOARD_ROOT / path_str).resolve()
        else:
            # Other relative paths - try resolving from SAMPLE_DASHBOARD_ROOT first
            potential_path = (SAMPLE_DASHBOARD_ROOT / path_str).resolve()
            if potential_path.exists() or allow_new:
                path = potential_path
            else:
                # Fall back to resolving from current directory
                path = Path(requested_path).resolve()
    else:
        path = Path(requested_path).resolve()
    
    allowed = _resolve_allowed_paths(run_dir)
    
    for allowed_path in allowed:
        allowed_resolved = allowed_path.resolve() if allowed_path.exists() else allowed_path
        
        # Check if the path is the allowed path itself
        if path == allowed_resolved:
            if allow_new or path.exists():
                return True, path, ""
            return False, path, f"Path does not exist: {path}"
        
        # Check if the path is under the allowed directory
        try:
            path.relative_to(allowed_resolved)
            if allow_new or path.exists():
                return True, path, ""
            return False, path, f"Path does not exist: {path}"
        except ValueError:
            # path is not relative to this allowed_path, continue checking
            continue
    
    # Path not in any allowed location
    return False, path, f"Path not in allowed locations: {path}"


def _get_relative_display_path(path: Path) -> str:
    """
    Get a shorter display path relative to sample-dashboard for cleaner output.
    
    Args:
        path: Absolute path to convert.
        
    Returns:
        Relative path string if under sample-dashboard, otherwise absolute.
    """
    try:
        return str(path.relative_to(SAMPLE_DASHBOARD_ROOT))
    except ValueError:
        return str(path)


# ============================================================================
# Search Tool
# ============================================================================


def search_content(
    query: str,
    file_pattern: str | None = None,
    max_results: int = 50,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Search for text or regex patterns within the sample-dashboard/src directory.
    
    Always searches in sample-dashboard/src/**, excluding node_modules, .next, and binary files.
    
    Args:
        query: Text or regex pattern to search for (case-insensitive).
        file_pattern: Optional filename glob pattern to filter files (e.g., "*.ts", "*.tsx", "route.ts").
                      This filters by FILENAME only, not by path.
        max_results: Maximum number of matching lines to return (default 50).
    """
    # Default search path is sample-dashboard/src
    search_root = SAMPLE_DASHBOARD_ROOT / "src"
    
    if not search_root.exists():
        return {
            "error": f"Search root does not exist: {search_root}",
            "query": query,
            "matches": [],
        }
    
    # Compile regex pattern (case-insensitive)
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error as exc:
        return {"error": f"Invalid regex pattern: {exc}", "query": query, "matches": []}
    
    # File pattern for filtering
    filename_pattern = file_pattern or "*"
    
    matches: list[dict[str, Any]] = []
    total_matches = 0
    
    # Directories to skip
    skip_dirs = {"node_modules", ".next", ".git", "__pycache__", ".pytest_cache"}
    
    # Binary file extensions to skip
    binary_extensions = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot"}
    
    try:
        for root, dirs, files in os.walk(search_root):
            # Modify dirs in-place to skip certain directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            root_path = Path(root)
            
            for filename in files:
                # Apply file pattern filter
                if not fnmatch.fnmatch(filename, filename_pattern):
                    continue
                
                file_path = root_path / filename
                
                # Skip binary files
                if file_path.suffix.lower() in binary_extensions:
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for line_num, line in enumerate(content.splitlines(), start=1):
                        if pattern.search(line):
                            total_matches += 1
                            if len(matches) < max_results:
                                display_path = _get_relative_display_path(file_path)
                                matches.append({
                                    "file": display_path,
                                    "line_number": line_num,
                                    "line_content": line.strip()[:200],  # Truncate long lines
                                })
                except Exception:
                    # Skip files that can't be read
                    continue
        
        logger.info(
            "search_content success",
            extra={
                "agent": "backend",
                "query": query,
                "matches": len(matches),
                "total": total_matches,
            },
        )
        
        return {
            "query": query,
            "matches": matches,
            "total_matches": total_matches,
            "truncated": total_matches > max_results,
        }
        
    except Exception as exc:
        logger.error("search_content failed", extra={"query": query, "error": str(exc)})
        return {"error": f"Search failed: {exc}", "query": query, "matches": []}


# ============================================================================
# Tool Export
# ============================================================================

search_content_tool = FunctionTool(func=search_content)
