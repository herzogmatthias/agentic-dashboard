"""
File system operations for the Backend Agent.

Provides tools for reading files, inspecting directories, and searching content
within the scoped paths allowed for the Backend Agent.
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
# Path Constants and Validation
# ============================================================================

# Base path to the sample-dashboard Next.js project
SAMPLE_DASHBOARD_ROOT = Path("C:/Users/darks/Documents/agentic-dashboard/sample-dashboard")

# Allowed paths for Backend Agent file operations
# {run_dir} is a placeholder that gets resolved from session state
ALLOWED_PATHS: list[str] = [
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/src/app/api",
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/src/models",
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/src/lib",
    "C:/Users/darks/Documents/agentic-dashboard/sample-dashboard/data",
    "{run_dir}/data_analysis/cleaned",
    "{run_dir}/data_analysis/data_profile.md",
    "{run_dir}/planner/dashboard_concept.json",
]


def _resolve_allowed_paths(run_dir: str | None) -> list[Path]:
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
    run_dir: str | None,
    allow_new: bool = False,
) -> tuple[bool, Path, str]:
    """
    Validate that a requested path is within allowed paths.
    
    Args:
        requested_path: The path the agent wants to access.
        run_dir: The current run directory from session state.
        allow_new: If True, allows paths that don't exist yet (for creation).
        
    Returns:
        Tuple of (is_valid, resolved_path, error_message).
        If valid, error_message is empty.
    """
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
# Tool Implementations
# ============================================================================


def read_file(
    path: str,
    from_line: int | None = None,
    to_line: int | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read file contents from an allowed path.
    
    Scoped to allowed paths:
    - sample-dashboard/src/app/api/**
    - sample-dashboard/src/models/**
    - sample-dashboard/src/lib/data-utils.ts
    - sample-dashboard/data/**
    - {run_dir}/data_analysis/cleaned/**
    - {run_dir}/data_analysis/data_profile.md
    - {run_dir}/planner/dashboard_concept.json
    
    Args:
        path: Absolute path to the file to read.
        from_line: Optional starting line (1-based). If provided, reads from this line.
        to_line: Optional ending line (1-based, inclusive). If provided, reads up to this line.
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - content: File contents (or slice if line range specified)
        - path: The resolved path
        - total_lines: Total number of lines in the file
        - lines_returned: Number of lines returned (if sliced)
        - error: Error message if operation failed
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    is_valid, resolved_path, error = _validate_path(path, run_dir)
    if not is_valid:
        logger.warning("read_file blocked", extra={"path": path, "error": error})
        return {"error": error, "path": path}
    
    if not resolved_path.is_file():
        return {"error": f"Not a file: {resolved_path}", "path": str(resolved_path)}
    
    try:
        content = resolved_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        
        # Handle line range slicing
        if from_line is not None or to_line is not None:
            start = max(0, (from_line or 1) - 1)  # Convert to 0-based
            end = min(total_lines, to_line or total_lines)  # Inclusive end
            sliced_lines = lines[start:end]
            content = "".join(sliced_lines)
            lines_returned = len(sliced_lines)
        else:
            lines_returned = total_lines
        
        display_path = _get_relative_display_path(resolved_path)
        logger.info(
            "read_file success",
            extra={"agent": "backend", "path": display_path, "lines": lines_returned},
        )
        
        return {
            "content": content,
            "path": str(resolved_path),
            "total_lines": total_lines,
            "lines_returned": lines_returned,
        }
        
    except Exception as exc:
        logger.error("read_file failed", extra={"path": path, "error": str(exc)})
        return {"error": f"Failed to read file: {exc}", "path": str(resolved_path)}


def inspect_dir(
    path: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    List contents of a directory within allowed paths.
    
    Returns file names, types (file/directory), and sizes for discovery.
    
    Args:
        path: Absolute path to the directory to inspect.
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - path: The directory path
        - entries: List of entries with name, is_dir, and size_bytes
        - error: Error message if operation failed
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    is_valid, resolved_path, error = _validate_path(path, run_dir)
    if not is_valid:
        logger.warning("inspect_dir blocked", extra={"path": path, "error": error})
        return {"error": error, "path": path}
    
    if not resolved_path.is_dir():
        return {"error": f"Not a directory: {resolved_path}", "path": str(resolved_path)}
    
    try:
        entries = []
        for entry in sorted(resolved_path.iterdir()):
            entry_info = {
                "name": entry.name,
                "is_dir": entry.is_dir(),
            }
            if entry.is_file():
                entry_info["size_bytes"] = entry.stat().st_size
            entries.append(entry_info)
        
        display_path = _get_relative_display_path(resolved_path)
        logger.info(
            "inspect_dir success",
            extra={"agent": "backend", "path": display_path, "count": len(entries)},
        )
        
        return {
            "path": str(resolved_path),
            "entries": entries,
        }
        
    except Exception as exc:
        logger.error("inspect_dir failed", extra={"path": path, "error": str(exc)})
        return {"error": f"Failed to inspect directory: {exc}", "path": str(resolved_path)}


def search_content(
    query: str,
    path_pattern: str | None = None,
    max_results: int = 50,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Search for text or regex patterns within allowed paths.
    
    Searches in sample-dashboard/src/** by default.
    
    Args:
        query: Text or regex pattern to search for (case-insensitive).
        path_pattern: Optional glob pattern to filter files (e.g., "*.ts", "**/*.tsx").
                      Defaults to all files in sample-dashboard/src/.
        max_results: Maximum number of matching lines to return (default 50).
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - query: The search query
        - matches: List of matches with file, line_number, and line_content
        - total_matches: Total matches found (may exceed returned if > max_results)
        - error: Error message if operation failed
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
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
    file_pattern = path_pattern or "*"
    
    matches: list[dict[str, Any]] = []
    total_matches = 0
    
    try:
        # Walk through allowed directories
        for root, _dirs, files in os.walk(search_root):
            root_path = Path(root)
            
            # Skip node_modules and other non-source directories
            if any(skip in str(root_path) for skip in ["node_modules", ".next", ".git"]):
                continue
            
            for filename in files:
                # Apply file pattern filter
                if not fnmatch.fnmatch(filename, file_pattern):
                    continue
                
                file_path = root_path / filename
                
                # Skip binary files
                if file_path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2"}:
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
# Tool Exports
# ============================================================================

read_file_tool = FunctionTool(func=read_file)
inspect_dir_tool = FunctionTool(func=inspect_dir)
search_content_tool = FunctionTool(func=search_content)
