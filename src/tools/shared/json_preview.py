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
from src.tools.utils import SAMPLE_DASHBOARD_ROOT, validate_path

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
    file_path: str,
    max_depth: int = 3,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Preview a JSON file, returning full minified content if under 1000 tokens,
    otherwise a truncated structure preview.
    
    - If total tokens <= 1000: returns full minified JSON
    - If total tokens > 1000: returns truncated preview (arrays limited to first element, depth limited)
    
    Args:
        file_path: Path to the JSON file (can be relative to run_dir or absolute)
        max_depth: Maximum nesting depth for truncated preview (default 3)
        tool_context: Optional tool context with state access
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None

    # Build allowed locations: current run_dir (if provided) + sample dashboard data folder
    allowed_paths = [SAMPLE_DASHBOARD_ROOT / "data"]
    if run_dir:
        allowed_paths.append(Path(run_dir))

    # Resolve and validate the requested path against allowed locations
    target_path = (
        Path(run_dir) / file_path
        if run_dir and not Path(file_path).is_absolute()
        else Path(file_path)
    )
    is_valid, path, error_msg = validate_path(
        requested_path=str(target_path),
        allowed_paths=allowed_paths,
        run_dir=run_dir,
        allow_new=False,
    )

    if not is_valid:
        if "does not exist" in error_msg.lower():
            return {"error": f"File not found: {file_path}", "path": str(path)}
        return {"error": f"Path not in allowed locations: {file_path}. {error_msg}"}

    if not path.exists():
        return {"error": f"File not found: {file_path}", "path": str(path)}

    if path.suffix.lower() != ".json":
        return {"error": f"Not a JSON file: {path}", "path": str(path)}
    
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
        
        # First, try full minified version
        full_minified = json.dumps(content, separators=(",", ":"))
        token_count = _count_tokens(full_minified)
        
        if token_count <= TOKEN_THRESHOLD:
            # Under threshold - return full content
            logger.info(
                "inspect_json_preview success (full)",
                extra={"path": str(path), "tokens": token_count},
            )
            return {
                "content": full_minified,
                "path": str(path),
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
                extra={"path": str(path), "tokens": token_count, "depth": max_depth},
            )
            
            return {
                "content": preview_str,
                "path": str(path),
                "tokens": token_count,
                "truncated": True,
                "max_depth": max_depth,
            }
        
    except json.JSONDecodeError as exc:
        logger.error("inspect_json_preview JSON error", extra={"path": str(path), "error": str(exc)})
        return {"error": f"Invalid JSON: {exc}", "path": str(path)}
    except Exception as exc:
        logger.error("inspect_json_preview failed", extra={"path": str(path), "error": str(exc)})
        return {"error": f"Failed to read JSON: {exc}", "path": str(path)}


# Tool export
inspect_json_preview_tool = FunctionTool(func=inspect_json_preview)
