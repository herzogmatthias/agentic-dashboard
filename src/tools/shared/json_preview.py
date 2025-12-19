"""
Shared JSON preview tool for exploring JSON files.

Used by both Planner and Backend agents to inspect JSON structures
with token-aware truncation for large files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger

logger = get_logger(__name__)

# Token threshold for applying preview truncation
TOKEN_THRESHOLD = 1000


def _count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken or fallback."""
    if tiktoken is None:
        # Crude fallback: ~4 chars per token
        return max(1, len(text) // 4)
    try:
        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def _minify_json(obj: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
    """
    Recursively minify a JSON object:
    - Objects: keep all keys but only first value preview at each level
    - Arrays: keep only the first element
    - Max depth: truncate deeper levels
    """
    if current_depth >= max_depth:
        if isinstance(obj, dict):
            return "{...}"
        elif isinstance(obj, list):
            return "[...]" if obj else []
        return obj
    
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            result[key] = _minify_json(value, max_depth, current_depth + 1)
        return result
    elif isinstance(obj, list):
        if not obj:
            return []
        # Only first element
        return [_minify_json(obj[0], max_depth, current_depth + 1)]
    else:
        return obj


def inspect_json_preview(
    filename: str,
    max_depth: int = 3,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Preview a JSON file in the cleaned/ folder.
    
    Always resolves to: {run_dir}/cleaned/{filename}
    Returns full minified content if under 1000 tokens,
    otherwise returns truncated structure preview.
    
    Args:
        filename: Simple filename (e.g., "metrics.json", "aggregates.json")
                  Will be resolved to {run_dir}/cleaned/{filename}
        max_depth: Maximum nesting depth for truncated preview (default 3)
        tool_context: Tool context with state access (required for run_dir)
    
    Returns:
        Dictionary with:
        - content: Full or truncated JSON string
        - path: Full resolved path that was read
        - tokens: Number of tokens (if truncated, original full count)
        - truncated: Boolean indicating if content was truncated
        - max_depth: Depth limit applied (if truncated)
        - error: Error message if reading failed
    """
    if not tool_context:
        return {"error": "Tool context required for run_dir resolution"}
    
    run_dir = tool_context.state.get("run_dir")
    if not run_dir:
        return {"error": "run_dir not found in session state"}
    
    # Resolve to cleaned/ folder
    target_path = Path(run_dir) / "cleaned" / filename
    
    if not target_path.exists():
        return {
            "error": f"File not found: {filename}",
            "expected_location": str(target_path),
        }
    
    if target_path.suffix.lower() != ".json":
        return {
            "error": f"Not a JSON file: {filename} (expected .json extension)",
            "path": str(target_path),
        }
    
    try:
        content = json.loads(target_path.read_text(encoding="utf-8"))
        
        # First, try full minified version
        full_minified = json.dumps(content, separators=(",", ":"))
        token_count = _count_tokens(full_minified)
        
        if token_count <= TOKEN_THRESHOLD:
            # Under threshold - return full content
            logger.info(
                "inspect_json_preview success (full)",
                extra={"data_filename": filename, "tokens": token_count},
            )
            relative_path = f"data/{filename}"
            return {
                "content": full_minified,
                "path": relative_path,
                "tokens": token_count,
                "truncated": False,
            }
        else:
            # Over threshold - apply truncation
            max_depth = min(max_depth, 5)  # Cap at 5
            preview = _minify_json(content, max_depth=max_depth)
            preview_str = json.dumps(preview, separators=(",", ":"))
            
            logger.info(
                "inspect_json_preview success (truncated)",
                extra={"data_filename": filename, "tokens": token_count, "max_depth": max_depth},
            )
            
            relative_path = f"data/{filename}"
            return {
                "content": preview_str,
                "path": relative_path,
                "tokens": token_count,
                "truncated": True,
                "max_depth": max_depth,
            }
        
    except json.JSONDecodeError as exc:
        logger.error("inspect_json_preview JSON error", extra={"filename": filename, "error": str(exc)})
        relative_path = f"data/{filename}"
        return {
            "error": f"Invalid JSON: {exc}",
            "path": relative_path,
        }
    except Exception as exc:
        logger.error("inspect_json_preview failed", extra={"data_filename": filename, "error": str(exc)})
        relative_path = f"data/{filename}"
        return {
            "error": f"Failed to read JSON: {exc}",
            "path": relative_path,
        }


# Tool export
inspect_json_preview_tool = FunctionTool(func=inspect_json_preview)
