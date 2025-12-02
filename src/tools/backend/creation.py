"""
File creation tools for the Backend Agent.

Provides tools for creating API routes, TypeScript models, and extending
utility files within the sample-dashboard Next.js project.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from src.core.logging import get_logger
from src.tools.backend.filesystem import SAMPLE_DASHBOARD_ROOT, _validate_path

logger = get_logger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_imports(content: str) -> tuple[dict[str, set[str]], str]:
    """
    Parse TypeScript import statements from file content.
    
    Args:
        content: TypeScript file content.
        
    Returns:
        Tuple of:
        - imports_dict: Dict mapping module path -> set of named imports
        - remaining_content: Content after all imports
    """
    imports_dict: dict[str, set[str]] = {}
    lines = content.split("\n")
    last_import_idx = -1
    
    # Regex patterns for different import styles
    # import { a, b } from "module"
    named_import_pattern = re.compile(
        r'^import\s+\{\s*([^}]+)\s*\}\s+from\s+["\']([^"\']+)["\'];?\s*$'
    )
    # import * as name from "module"
    star_import_pattern = re.compile(
        r'^import\s+\*\s+as\s+(\w+)\s+from\s+["\']([^"\']+)["\'];?\s*$'
    )
    # import name from "module"
    default_import_pattern = re.compile(
        r'^import\s+(\w+)\s+from\s+["\']([^"\']+)["\'];?\s*$'
    )
    # import "module" (side-effect import)
    side_effect_pattern = re.compile(
        r'^import\s+["\']([^"\']+)["\'];?\s*$'
    )
    
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        
        # Check for named imports
        match = named_import_pattern.match(stripped)
        if match:
            names_str, module = match.groups()
            names = {n.strip() for n in names_str.split(",") if n.strip()}
            if module not in imports_dict:
                imports_dict[module] = set()
            imports_dict[module].update(names)
            last_import_idx = idx
            continue
        
        # Check for star imports (keep as special marker)
        match = star_import_pattern.match(stripped)
        if match:
            alias, module = match.groups()
            # Store star imports specially with * prefix
            if module not in imports_dict:
                imports_dict[module] = set()
            imports_dict[module].add(f"* as {alias}")
            last_import_idx = idx
            continue
        
        # Check for default imports
        match = default_import_pattern.match(stripped)
        if match:
            name, module = match.groups()
            if module not in imports_dict:
                imports_dict[module] = set()
            imports_dict[module].add(f"default:{name}")  # Mark as default
            last_import_idx = idx
            continue
        
        # Check for side-effect imports
        match = side_effect_pattern.match(stripped)
        if match:
            module = match.group(1)
            if module not in imports_dict:
                imports_dict[module] = set()
            # Empty set means side-effect import
            last_import_idx = idx
            continue
        
        # If we hit a non-import, non-empty line after seeing imports, stop
        if last_import_idx >= 0 and not stripped.startswith("//"):
            break
    
    # Get remaining content after imports
    if last_import_idx >= 0:
        remaining_content = "\n".join(lines[last_import_idx + 1:]).lstrip("\n")
    else:
        remaining_content = content
    
    return imports_dict, remaining_content


def _merge_imports(
    existing: dict[str, set[str]],
    new: dict[str, set[str]],
) -> dict[str, set[str]]:
    """
    Merge two import dictionaries, combining named imports from same modules.
    
    Args:
        existing: Existing imports dict.
        new: New imports to merge.
        
    Returns:
        Merged imports dict.
    """
    merged = {k: set(v) for k, v in existing.items()}
    
    for module, names in new.items():
        if module not in merged:
            merged[module] = set()
        merged[module].update(names)
    
    return merged


def _format_imports(imports_dict: dict[str, set[str]]) -> str:
    """
    Format imports dictionary back into TypeScript import statements.
    
    Args:
        imports_dict: Dict mapping module path -> set of named imports.
        
    Returns:
        Formatted import statements string.
    """
    lines: list[str] = []
    
    # Sort modules for consistent output
    for module in sorted(imports_dict.keys()):
        names = imports_dict[module]
        
        if not names:
            # Side-effect import
            lines.append(f'import "{module}";')
            continue
        
        # Separate default, star, and named imports
        default_imports = [n.replace("default:", "") for n in names if n.startswith("default:")]
        star_imports = [n for n in names if n.startswith("* as ")]
        named_imports = sorted(n for n in names if not n.startswith("default:") and not n.startswith("* as "))
        
        # Handle star imports
        for star in star_imports:
            lines.append(f'import {star} from "{module}";')
        
        # Handle default + named imports
        if default_imports and named_imports:
            default = default_imports[0]
            named = ", ".join(named_imports)
            lines.append(f'import {default}, {{ {named} }} from "{module}";')
        elif default_imports:
            lines.append(f'import {default_imports[0]} from "{module}";')
        elif named_imports:
            named = ", ".join(named_imports)
            lines.append(f'import {{ {named} }} from "{module}";')
    
    return "\n".join(lines)


def _parse_import_strings(imports: list[str]) -> dict[str, set[str]]:
    """
    Parse a list of import statement strings into imports dict.
    
    Args:
        imports: List of import statement strings.
        
    Returns:
        Imports dictionary.
    """
    combined = "\n".join(imports)
    imports_dict, _ = _parse_imports(combined)
    return imports_dict


def _validate_typescript_exports(content: str) -> tuple[bool, str]:
    """
    Validate that TypeScript content exports at least one type/interface/const.
    
    Args:
        content: TypeScript file content.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    # Look for export statements
    export_patterns = [
        r'export\s+(?:interface|type|const|function|class|enum)\s+\w+',
        r'export\s+\{[^}]+\}',
        r'export\s+default\s+',
    ]
    
    for pattern in export_patterns:
        if re.search(pattern, content):
            return True, ""
    
    return False, "Content must export at least one type, interface, const, function, class, or enum"


# ============================================================================
# Tool Implementations
# ============================================================================


def create_api(
    route_path: str,
    content: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Create a new API route file in the Next.js App Router structure.
    
    Creates file at: sample-dashboard/src/app/api/{route_path}
    
    The route_path should include the file name, e.g.:
    - "sales/route.ts" creates /api/sales endpoint
    - "products/[id]/route.ts" creates /api/products/[id] endpoint
    
    Args:
        route_path: Path within the api/ directory (e.g., "sales/route.ts").
        content: TypeScript content for the route file.
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - success: Whether the file was created
        - path: Full path to the created file
        - relative_path: Path relative to sample-dashboard
        - error: Error message if operation failed
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    # Normalize the route path
    route_path = route_path.lstrip("/\\")
    
    # Construct the full path
    api_root = SAMPLE_DASHBOARD_ROOT / "src" / "app" / "api"
    full_path = api_root / route_path
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = _validate_path(str(full_path), run_dir, allow_new=True)
    if not is_valid:
        logger.warning("create_api blocked", extra={"path": str(full_path), "error": error})
        return {"success": False, "error": error, "path": str(full_path)}
    
    # Check if file already exists
    if resolved_path.exists():
        return {
            "success": False,
            "error": f"File already exists: {resolved_path}. Use patch_file to modify existing files.",
            "path": str(resolved_path),
        }
    
    # Ensure route file is named correctly
    if not resolved_path.name.endswith((".ts", ".tsx")):
        return {
            "success": False,
            "error": f"API route file must have .ts or .tsx extension: {resolved_path.name}",
            "path": str(resolved_path),
        }
    
    try:
        # Create parent directories if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(content, encoding="utf-8")
        
        relative_path = f"src/app/api/{route_path}"
        logger.info(
            "create_api success",
            extra={"agent": "backend", "path": relative_path},
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "message": f"Created API route at {relative_path}",
        }
        
    except Exception as exc:
        logger.error("create_api failed", extra={"path": str(full_path), "error": str(exc)})
        return {
            "success": False,
            "error": f"Failed to create API route: {exc}",
            "path": str(full_path),
        }


def create_model(
    name: str,
    content: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Create a new TypeScript model file in the models directory.
    
    Creates file at: sample-dashboard/src/models/{name}.ts
    
    The content must export at least one type, interface, or const.
    
    Args:
        name: Name of the model file (without .ts extension).
        content: TypeScript content for the model file.
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - success: Whether the file was created
        - path: Full path to the created file
        - relative_path: Path relative to sample-dashboard
        - error: Error message if operation failed
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    # Normalize the model name
    name = name.strip().replace(".ts", "")
    
    # Construct the full path
    models_dir = SAMPLE_DASHBOARD_ROOT / "src" / "models"
    full_path = models_dir / f"{name}.ts"
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = _validate_path(str(full_path), run_dir, allow_new=True)
    if not is_valid:
        logger.warning("create_model blocked", extra={"path": str(full_path), "error": error})
        return {"success": False, "error": error, "path": str(full_path)}
    
    # Check if file already exists
    if resolved_path.exists():
        return {
            "success": False,
            "error": f"File already exists: {resolved_path}. Use patch_file to modify existing files.",
            "path": str(resolved_path),
        }
    
    # Validate that content exports something
    is_valid_content, validation_error = _validate_typescript_exports(content)
    if not is_valid_content:
        return {
            "success": False,
            "error": validation_error,
            "path": str(full_path),
        }
    
    try:
        # Create models directory if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(content, encoding="utf-8")
        
        relative_path = f"src/models/{name}.ts"
        logger.info(
            "create_model success",
            extra={"agent": "backend", "path": relative_path},
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "message": f"Created model at {relative_path}",
        }
        
    except Exception as exc:
        logger.error("create_model failed", extra={"path": str(full_path), "error": str(exc)})
        return {
            "success": False,
            "error": f"Failed to create model: {exc}",
            "path": str(full_path),
        }


def add_utility(
    imports: list[str],
    content: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Add utility functions to the data-utils.ts file.
    
    Reads existing content, merges import statements (deduplicating),
    and appends new utility content at the end.
    
    Args:
        imports: List of import statements to add (will be merged with existing).
                 e.g., ['import { parse } from "papaparse";']
        content: New utility function content to append.
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - success: Whether the file was updated
        - path: Full path to the file
        - imports_added: Number of new imports added
        - imports_merged: Number of imports merged with existing
        - error: Error message if operation failed
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    # Target file path
    utils_path = SAMPLE_DASHBOARD_ROOT / "src" / "lib" / "data-utils.ts"
    
    # Validate the path is within allowed scope (allow_new=True since we may create the file)
    is_valid, resolved_path, error = _validate_path(str(utils_path), run_dir, allow_new=True)
    if not is_valid:
        logger.warning("add_utility blocked", extra={"path": str(utils_path), "error": error})
        return {"success": False, "error": error, "path": str(utils_path)}
    
    try:
        # Read existing content
        if resolved_path.exists():
            existing_content = resolved_path.read_text(encoding="utf-8")
        else:
            # Create file if it doesn't exist
            existing_content = ""
        
        # Parse existing imports
        existing_imports, existing_body = _parse_imports(existing_content)
        
        # Parse new imports
        new_imports = _parse_import_strings(imports)
        
        # Count for reporting
        imports_before = sum(len(v) for v in existing_imports.values())
        
        # Merge imports
        merged_imports = _merge_imports(existing_imports, new_imports)
        
        imports_after = sum(len(v) for v in merged_imports.values())
        imports_added = imports_after - imports_before
        
        # Format merged imports
        imports_section = _format_imports(merged_imports)
        
        # Combine: imports + existing body + new content
        new_content_parts = []
        if imports_section:
            new_content_parts.append(imports_section)
        if existing_body.strip():
            new_content_parts.append(existing_body.rstrip())
        if content.strip():
            new_content_parts.append(content.strip())
        
        final_content = "\n\n".join(new_content_parts) + "\n"
        
        # Ensure parent directory exists
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write updated content
        resolved_path.write_text(final_content, encoding="utf-8")
        
        relative_path = "src/lib/data-utils.ts"
        logger.info(
            "add_utility success",
            extra={
                "agent": "backend",
                "path": relative_path,
                "imports_added": imports_added,
            },
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "imports_added": imports_added,
            "message": f"Updated {relative_path}: added {imports_added} import(s) and appended utility content",
        }
        
    except Exception as exc:
        logger.error("add_utility failed", extra={"path": str(utils_path), "error": str(exc)})
        return {
            "success": False,
            "error": f"Failed to update utilities: {exc}",
            "path": str(utils_path),
        }


# ============================================================================
# Tool Exports
# ============================================================================

create_api_tool = FunctionTool(func=create_api)
create_model_tool = FunctionTool(func=create_model)
add_utility_tool = FunctionTool(func=add_utility)
