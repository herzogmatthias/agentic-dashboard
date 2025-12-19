"""
File system constants and search tool for the Backend Dev Agent.

Provides path constants and content search functionality.
Read/write/edit operations are handled by the MCP filesystem server.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.tools.utils.paths import SAMPLE_DASHBOARD_ROOT

logger = get_logger(__name__)

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
                "agent": "backend_dev",
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
