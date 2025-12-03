import json
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

try:
    import tiktoken  # optional; used for token-aware summaries
except Exception:  # pragma: no cover - fallback if not installed
    tiktoken = None  # type: ignore
from google.adk.tools import FunctionTool, ToolContext

from src.core.logging import get_logger
from src.tools.llm_client import Summarizer, get_output_summary_prompt, get_snippet_summary_prompt

from ..core.config import SANDBOX_CLEANED_CSV_PATH, SANDBOX_CSV_PATH, SLICE_LIMIT
from ..core.daytona_client import DaytonaSandboxSingleton

logger = get_logger(__name__)

def _count_tokens(text: str) -> int:
    if tiktoken is None:
        # crude fallback: ~4 chars per token
        return max(1, len(text) // 4)
    try:
        enc = tiktoken.encoding_for_model("gpt-5-mini")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def run_python(code: str, timeout_seconds: int = 180) -> Dict[str, Any]:
    """
    Execute Python code inside the persistent Daytona sandbox.

    - CSV_PATH and CLEANED_PATH variables are injected automatically.
    - Captures stdout/stderr and auto-summarizes outputs > ~1000 chars.
    - Full unsummarized output is saved under workspace/ for later inspection.
    - Returns exit_code, a (possibly summarized) result string, and a message.
    """
    header = textwrap.dedent(
        f"""
        import warnings
        warnings.filterwarnings("ignore")
        CSV_PATH = {SANDBOX_CSV_PATH!r}
        CLEANED_PATH = {SANDBOX_CLEANED_CSV_PATH!r}
    """
    )
    final_code = header + "\n" + code
    sandbox = DaytonaSandboxSingleton().get_sandbox()
    resp = sandbox.process.code_run(final_code, timeout=timeout_seconds)
    result = resp.result
    msg= "Full Output is displayed"
    charts = []
    token_count = _count_tokens(resp.result)
    if resp.artifacts:
        if resp.artifacts.charts:
            charts = {chart.png for chart in resp.artifacts.charts}
    if token_count > 1000:
        result = Summarizer().summarize(resp.result, system_prompt=get_output_summary_prompt(), max_tokens=500)
        path = f"workspace/summarized_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        sandbox.fs.upload_file(resp.result.encode(), path)
        msg = f"Output is summarized to 500 tokens. Full output saved to sandbox at {path}"
    logger.info("run_python executed", extra={"agent": "data_analysis", "phase": "run_python", "exit_code": resp.exit_code})
    return {"exit_code": resp.exit_code, "result": result, "charts": charts, "message": msg}

def read_snippet(file_path: str, from_line: int = 1, to_line: int = 50):
    """
    Read a specific line range from a file.
    
    Automatically detects if path is local (contains Windows/Unix absolute paths)
    or sandbox-relative (starts with 'workspace/').
    
    Useful for retrieving details from large saved logs without loading the entire file.
    
    Args:
        file_path: Path to the file (local absolute path or sandbox-relative)
        from_line: Starting line number (1-based, minimum 1). Defaults to 1.
        to_line: Ending line number (1-based, inclusive). Defaults to 50.
    """
    # Ensure 1-based indexing - clamp from_line to minimum of 1
    from_line = max(1, from_line)
    to_line = max(from_line, to_line)
    
    # Check if path is local absolute path
    local_path = Path(file_path)
    if local_path.is_absolute() and local_path.exists():
        # Read from local filesystem
        try:
            data = local_path.read_bytes()
        except Exception as exc:
            raise RuntimeError(f"Failed to read local file {file_path}: {exc}") from exc
    else:
        # Read from sandbox
        sandbox = DaytonaSandboxSingleton().get_sandbox()
        try:
            data = sandbox.fs.download_file(file_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to read sandbox file {file_path}: {exc}") from exc

    lines = data.decode(errors="replace").splitlines()
    snippet = lines[from_line - 1 : to_line]
    snippet_text = "\n".join(snippet)
    token_count = _count_tokens(snippet_text)
    message = "Full Snippet Returned"
    if token_count > 1000:
        snippet = Summarizer().summarize(snippet_text, system_prompt=get_snippet_summary_prompt(), max_tokens=500).splitlines()
        message = "Snippet Summarized"
    logger.info("read_snippet", extra={"agent": "filesystem", "phase": "read_snippet", "path": str(file_path)})
    return {
        "file_lines": len(lines),
        "snippet": "\n".join(snippet),
        "message": message
    }

def inspect_directory(path: str = "workspace") -> Dict[str, Any]:
    """
    List files and directories inside the sandbox at the given path.
    Returns names, directory flags, and file sizes for discovery and debugging.
    """
    sandbox = DaytonaSandboxSingleton().get_sandbox()
    info: Dict[str, Any] = {"path": path}

    try:
        entries = sandbox.fs.list_files(path)
        info["type"] = "directory"
        info["entries"] = [{"name": entry.name, "is_dir": entry.is_dir, "size_bytes": entry.size} for entry in entries]
    except Exception:
        pass
    logger.info("inspect_directory", extra={"agent": "filesystem", "phase": "inspect_directory", "path": path})
    return info


def write_data_profile(
    markdown: str,
    tool_context: ToolContext,
) -> str:
    """
    Save a DataProfile markdown file to the host run directory.
    Requires `run_dir` to be present in session state.
    
    Also saves the path to state["data_profile_path"] for templating in other agent prompts.
    """
    if tool_context is None or "run_dir" not in tool_context.state:
        raise RuntimeError("Session state missing 'run_dir'; cannot write data profile.")

    base_dir = Path(tool_context.state["run_dir"])
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "data_profile.md"
    path.write_text(markdown, encoding="utf-8")
    
    # Save path to state for prompt templating
    tool_context.state["data_profile_path"] = str(path.resolve())
    
    logger.info("write_data_profile", extra={"agent": "filesystem", "phase": "write_data_profile", "path": str(path)})
    return str(path.resolve())


def write_cleaning_summary(
    markdown: str,
    tool_context: ToolContext,
) -> str:
    """
    Save a CleaningSummary markdown file to the host run directory.
    Requires `run_dir` to be present in session state.
    
    Also saves the path to state["cleaning_summary_path"] for templating in other agent prompts.
    """
    if tool_context is None or "run_dir" not in tool_context.state:
        raise RuntimeError("Session state missing 'run_dir'; cannot write cleaning summary.")

    base_dir = Path(tool_context.state["run_dir"])
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "cleaning_summary.md"
    path.write_text(markdown, encoding="utf-8")
    
    # Save path to state for prompt templating
    tool_context.state["cleaning_summary_path"] = str(path.resolve())
    
    logger.info("write_cleaning_summary", extra={"agent": "filesystem", "phase": "write_cleaning_summary", "path": str(path)})
    return str(path.resolve())


def write_metrics_summary(
    markdown: str,
    tool_context: ToolContext,
) -> str:
    """
    Save a metrics summary markdown file to the host run directory.
    This is for additional analysis artifacts (regressions, correlations, key metrics)
    that aren't directly in cleaned.csv.
    
    Requires `run_dir` to be present in session state.
    
    Also saves the path to state["metrics_summary_path"] for templating in other agent prompts.
    
    Args:
        markdown: Markdown content describing key metrics and analysis results
        tool_context: Tool context with session state
    
    Returns:
        Absolute path to the written file
    """
    if tool_context is None or "run_dir" not in tool_context.state:
        raise RuntimeError("Session state missing 'run_dir'; cannot write metrics summary.")

    base_dir = Path(tool_context.state["run_dir"])
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "metrics_summary.md"
    path.write_text(markdown, encoding="utf-8")
    
    # Save path to state for prompt templating
    tool_context.state["metrics_summary_path"] = str(path.resolve())
    
    logger.info("write_metrics_summary", extra={"agent": "filesystem", "phase": "write_metrics_summary", "path": str(path)})
    return str(path.resolve())

def inspect_json_keys(
    file_path: str,
    max_depth: int = 2,
    max_keys: int = 50
) -> Dict[str, Any]:
    """
    Return flattened JSON key paths from a file.
    
    Automatically detects if path is local (contains Windows/Unix absolute paths)
    or sandbox-relative (starts with 'workspace/').

    - Extracts only key names, never values.
    - Traverses objects and arrays up to `max_depth`.
    - Limits keys per object to `max_keys`.
    - Output format: {"structure": ["a", "a.b", "a.b.c", ...]}

    """
    # Check if path is local absolute path
    local_path = Path(file_path)
    if local_path.is_absolute() and local_path.exists():
        # Read from local filesystem
        try:
            data_bytes = local_path.read_bytes()
        except Exception as exc:
            raise RuntimeError(f"Failed to read local file {file_path}: {exc}") from exc
    else:
        # Read from sandbox
        sandbox = DaytonaSandboxSingleton().get_sandbox()
        try:
            data_bytes = sandbox.fs.download_file(file_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to read sandbox file {file_path}: {exc}") from exc

    try:
        json_data = json.loads(data_bytes.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSON in {file_path}: {exc}") from exc

    flattened_keys = []

    def walk(obj: Any, prefix: str, depth: int):
        if depth > max_depth:
            return

        if isinstance(obj, dict):
            keys = list(obj.keys())[:max_keys]
            for k in keys:
                full = f"{prefix}.{k}" if prefix else k
                flattened_keys.append(full)
                walk(obj[k], full, depth + 1)

        elif isinstance(obj, list) and obj:
            # Inspect only index 0 (structure)
            full = f"{prefix}[]" if prefix else "[]"
            flattened_keys.append(full)
            walk(obj[0], full, depth + 1)

        # primitives are ignored except their path already added above

    walk(json_data, prefix="", depth=1)

    result = {
        "file_path": file_path,
        "max_depth": max_depth,
        "max_keys": max_keys,
        "structure": flattened_keys
    }
    logger.info("inspect_json_keys", extra={"agent": "filesystem", "phase": "inspect_json_keys", "path": str(file_path)})
    return result

def inspect_json_value(
    file_path: str,
    key_path: str,
    max_preview: int = 300
) -> Dict[str, Any]:
    """
    Retrieve a JSON value at the given flattened key path.
    
    Automatically detects if path is local (contains Windows/Unix absolute paths)
    or sandbox-relative (starts with 'workspace/').

    - Path format should match inspect_json_keys() output.
    - Dot notation for nested fields (e.g. "a.b.c").
    - Array example access:
        * "columns[]"      -> sample element at index 0
        * "columns[:10]"   -> slice up to 10 elements
        * "columns[3:6]"   -> slice [3, 6)
        * "columns[5:]"    -> slice from 5 onward (capped at 50 elements)
        * "[:20]"          -> slice on top-level array
    - Returns a minified JSON/string preview, truncated by max_preview chars.
    """
    # Check if path is local absolute path
    local_path = Path(file_path)
    if local_path.is_absolute() and local_path.exists():
        # Read from local filesystem
        try:
            data_bytes = local_path.read_bytes()
            json_data = json.loads(data_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:
            raise RuntimeError(f"Failed to load local JSON {file_path}: {exc}") from exc
    else:
        # Read from sandbox
        sandbox = DaytonaSandboxSingleton().get_sandbox()
        try:
            data_bytes = sandbox.fs.download_file(file_path)
            json_data = json.loads(data_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:
            raise RuntimeError(f"Failed to load sandbox JSON: {exc}") from exc

    parts = key_path.split(".")
    current: Any = json_data

    slice_pattern = re.compile(r"^(?P<key>.*)\[(?P<slice>[0-9]*:[0-9]*)\]$")
    index_pattern = re.compile(r"^(?P<key>.*)\[(?P<index>[0-9]+)\]$")

    for part in parts:
        # Legacy syntax: "key[]" -> first element
        if part.endswith("[]") and not slice_pattern.match(part):
            key = part[:-2]
            # Navigate dict if key present
            if key:
                if not isinstance(current, dict):
                    return {"error": f"Path '{key}' not found: not a dict."}
                current = current.get(key)
                if not isinstance(current, list):
                    return {"error": f"'{key}' is not a list."}
            else:
                # top-level array
                if not isinstance(current, list):
                    return {"error": "Value is not a list."}

            if not current:
                return {"value": None, "note": "empty array"}
            current = current[0]
            continue

        # Slice syntax: key[start:end]
        m_slice = slice_pattern.match(part)
        if m_slice:
            key = m_slice.group("key")
            slice_spec = m_slice.group("slice")

            # Navigate dict key if present
            if key:
                if not isinstance(current, dict):
                    return {"error": f"Path '{key}' not found: not a dict."}
                current = current.get(key)
                if not isinstance(current, list):
                    return {"error": f"'{key}' is not a list."}
            else:
                # top-level array
                if not isinstance(current, list):
                    return {"error": "Value is not a list."}

            # Parse start:end
            start_str, end_str = slice_spec.split(":")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else len(current)

            if start < 0:
                start = 0
            if end < start:
                end = start

            # Hard cap number of elements
            if end - start > SLICE_LIMIT:
                end = start + SLICE_LIMIT

            current = current[start:end]
            continue

        # Optional: index syntax key[3] -> single element
        m_index = index_pattern.match(part)
        if m_index:
            key = m_index.group("key")
            idx = int(m_index.group("index"))

            if key:
                if not isinstance(current, dict):
                    return {"error": f"Path '{key}' not found: not a dict."}
                current = current.get(key)
                if not isinstance(current, list):
                    return {"error": f"'{key}' is not a list."}
            else:
                if not isinstance(current, list):
                    return {"error": "Value is not a list."}

            if idx < 0 or idx >= len(current):
                return {"error": f"Index {idx} out of range."}
            current = current[idx]
            continue

        # Normal dict key
        if not isinstance(current, dict):
            return {"error": f"Cannot descend into non-dict at '{part}'."}
        if part not in current:
            return {"error": f"Key '{part}' not found."}
        current = current[part]

    # ----- Minify result for LLM -----
    if isinstance(current, (dict, list)):
        try:
            raw_str = json.dumps(current, separators=(",", ":"), ensure_ascii=False)
        except TypeError:
            raw_str = repr(current)
    else:
        try:
            raw_str = json.dumps(current, ensure_ascii=False)
        except TypeError:
            raw_str = repr(current)

    if len(raw_str) > max_preview:
        raw_str = raw_str[:max_preview] + "... (truncated)"

    logger.info("inspect_json_value", extra={"agent": "filesystem", "phase": "inspect_json_value", "path": str(file_path)})
    return {"value": raw_str}


run_python_tool = FunctionTool(func=run_python)
inspect_directory_tool = FunctionTool(func=inspect_directory)
read_snippet_tool = FunctionTool(func=read_snippet)
write_data_profile_tool = FunctionTool(func=write_data_profile)
write_cleaning_summary_tool = FunctionTool(func=write_cleaning_summary)
write_metrics_summary_tool = FunctionTool(func=write_metrics_summary)
inspect_json_keys_tool = FunctionTool(func=inspect_json_keys)
inspect_json_value_tool = FunctionTool(func=inspect_json_value)