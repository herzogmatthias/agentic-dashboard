"""
Test file creation tools for the Testing Agent.

Provides tools for creating Jest test files within the sample-dashboard
Next.js project. Follows conventions:
- API route tests: tests/api/{artifact_id}.test.ts
- Helper tests: tests/lib/{helper_name}.test.ts
- Model tests: tests/models/{model_name}.test.ts
"""
from __future__ import annotations

import re
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.tools.tester.filesystem import (
    SAMPLE_DASHBOARD_ROOT,
    TESTS_ROOT,
    _validate_test_path,
    _get_relative_test_path,
)

logger = get_logger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _validate_test_structure(content: str, filename: str) -> tuple[bool, str]:
    """
    Validate that test content has proper Jest structure.
    
    Args:
        content: TypeScript test file content.
        filename: Name of the test file for error messages.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    # Check for at least one describe block
    if not re.search(r'describe\s*\(', content):
        return False, f"Test file '{filename}' must contain at least one describe() block"
    
    # Check for at least one test or it block
    if not re.search(r'(?:test|it)\s*\(', content):
        return False, f"Test file '{filename}' must contain at least one test() or it() block"
    
    # Check for expect statements
    if not re.search(r'expect\s*\(', content):
        return False, f"Test file '{filename}' must contain at least one expect() assertion"
    
    return True, ""


def _check_typescript_syntax(content: str, filename: str) -> tuple[bool, str]:
    """
    Basic TypeScript/Jest syntax validation.
    
    Args:
        content: TypeScript test file content.
        filename: Name of the file for error messages.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    # Check for basic syntax issues
    errors = []
    
    # Check balanced braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    if open_braces != close_braces:
        errors.append(f"Unbalanced braces: {open_braces} '{{' vs {close_braces} '}}'")
    
    # Check balanced parentheses
    open_parens = content.count('(')
    close_parens = content.count(')')
    if open_parens != close_parens:
        errors.append(f"Unbalanced parentheses: {open_parens} '(' vs {close_parens} ')'")
    
    # Check for common issues
    if 'import ' in content and 'from' not in content and '{' not in content.split('import')[1].split('\n')[0]:
        # This is a loose check - just flagging potential issues
        pass
    
    if errors:
        return False, "; ".join(errors)
    
    return True, ""


# ============================================================================
# Tool Implementations
# ============================================================================


def create_test(
    name: str,
    content: str,
    test_type: str = "api",
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Create a new Jest test file in the tests directory.
    
    Creates file at:
    - test_type="api" → tests/api/{name}.test.ts (for API route tests)
    - test_type="lib" → tests/lib/{name}.test.ts (for helper/utility tests)
    - test_type="models" → tests/models/{name}.test.ts (for model tests)
    
    Test files must contain:
    - At least one describe() block
    - At least one test() or it() block
    - At least one expect() assertion
    
    Args:
        name: Name of the test file (without .test.ts extension).
              For API tests, use the artifact_id (e.g., "sales_summary").
              For lib tests, use the helper name (e.g., "data_utils").
        content: TypeScript/Jest test content for the file.
        test_type: Type of test file - "api", "lib", or "models" (default: "api").
    """
    # Normalize the name
    name = name.strip().replace(".test.ts", "").replace(".ts", "")
    
    # Validate test_type
    valid_types = ["api", "lib", "models"]
    if test_type not in valid_types:
        return {
            "success": False,
            "error": f"Invalid test_type '{test_type}'. Must be one of: {', '.join(valid_types)}",
            "name": name,
        }
    
    # Construct the full path based on test_type
    test_dir = TESTS_ROOT / test_type
    full_path = test_dir / f"{name}.test.ts"
    
    # Validate the path is within allowed scope
    is_valid, resolved_path, error = _validate_test_path(str(full_path), allow_new=True)
    if not is_valid:
        logger.warning("create_test blocked", extra={"path": str(full_path), "error": error})
        return {"success": False, "error": error, "path": str(full_path)}
    
    # Check if file already exists
    if resolved_path.exists():
        return {
            "success": False,
            "error": f"Test file already exists: {resolved_path}. Use delete_file first if you need to replace it, or edit it.",
            "path": str(resolved_path),
        }
    
    # Validate test structure
    is_valid_structure, structure_error = _validate_test_structure(content, f"{name}.test.ts")
    if not is_valid_structure:
        logger.warning("create_test structure check failed", extra={"test_name": name})
        return {
            "success": False,
            "error": f"Test structure error - file not created:\n{structure_error}",
            "path": str(full_path),
        }
    
    # Validate TypeScript syntax
    syntax_valid, syntax_errors = _check_typescript_syntax(content, f"{name}.test.ts")
    if not syntax_valid:
        logger.warning("create_test syntax check failed", extra={"test_name": name})
        return {
            "success": False,
            "error": f"Syntax error - file not created:\n{syntax_errors}",
            "path": str(full_path),
            "syntax_errors": syntax_errors,
        }
    
    try:
        # Create parent directories if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(content, encoding="utf-8")
        
        relative_path = _get_relative_test_path(resolved_path)
        
        logger.info(
            "create_test success",
            extra={"agent": "tester", "path": relative_path, "test_type": test_type},
        )
        
        return {
            "success": True,
            "path": str(resolved_path),
            "relative_path": relative_path,
            "test_type": test_type,
            "message": f"Created test file at {relative_path}",
        }
        
    except Exception as exc:
        logger.error("create_test failed", extra={"path": str(full_path), "error": str(exc)})
        return {
            "success": False,
            "error": f"Failed to create test file: {exc}",
            "path": str(full_path),
        }


# ============================================================================
# Tool Exports
# ============================================================================

create_test_tool = FunctionTool(func=create_test)
