"""
Validation tools for the Backend Dev Agent.

Provides tools for:
- Running ESLint on the sample-dashboard project
- Running TypeScript type-check for fast type verification
- Running Next.js build for full compilation (internal use)

Also provides internal helper _check_typescript_syntax() used by creation tools.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.tools.backend_dev.filesystem import SAMPLE_DASHBOARD_ROOT

logger = get_logger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Timeout limits (seconds)
LINT_TIMEOUT = 120  # 2 minutes for lint
TYPE_CHECK_TIMEOUT = 120  # 2 minutes for type-check
BUILD_TIMEOUT = 180  # 3 minutes for full build (internal use)
SYNTAX_CHECK_TIMEOUT = 10
OPENAPI_CHECK_TIMEOUT = 120

# Output truncation limits (characters)
LINT_OUTPUT_LIMIT = 5000
TYPE_CHECK_OUTPUT_LIMIT = 8000
BUILD_OUTPUT_LIMIT = 10000
OPENAPI_OUTPUT_LIMIT = 8000


# ============================================================================
# TypeScript Syntax Validation
# ============================================================================


def _check_typescript_syntax(content: str, filename: str = "check.ts") -> tuple[bool, str]:
    """
    Check TypeScript content for syntax errors.
    
    NOTE: Syntax validation via tsc is DISABLED because standalone file checking
    cannot resolve imports (e.g., from '@/lib/...' or 'next/server'), causing
    false positives. Rely on run_lint() and run_build() for full validation.
    
    Args:
        content: TypeScript code to validate.
        filename: Filename hint for error messages.
        
    Returns:
        Tuple of (is_valid, error_message).
        Always returns (True, "") - validation is deferred to lint/build.
    """
    # Syntax validation disabled - tsc cannot resolve imports in standalone files
    # Use run_lint() and run_build() after file creation for full validation
    return True, ""


def _check_typescript_syntax_full(content: str, filename: str = "check.ts") -> tuple[bool, str]:
    """
    Full TypeScript syntax check using tsc (currently unused).
    
    This function is preserved for potential future use but is not called
    because tsc cannot resolve module imports in standalone temp files.
    
    Args:
        content: TypeScript code to validate.
        filename: Filename hint for error messages.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        # Create a temporary file with the content
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ts",
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Run tsc with --noEmit to check syntax without generating output
            # Using npx to ensure we use the project's TypeScript version
            # shell=True is required on Windows to find npx in PATH
            result = subprocess.run(
                [
                    "npx",
                    "tsc",
                    "--noEmit",
                    "--skipLibCheck",  # Skip checking node_modules types for speed
                    "--allowJs",
                    "--esModuleInterop",
                    "--moduleResolution", "node",
                    "--target", "ES2020",
                    "--module", "ESNext",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=SYNTAX_CHECK_TIMEOUT,
                cwd=str(SAMPLE_DASHBOARD_ROOT),
                shell=True,  # Required on Windows for npx
            )
            
            if result.returncode == 0:
                return True, ""
            
            # Parse and clean up error messages
            errors = result.stdout + result.stderr
            # Replace temp file path with the intended filename for clarity
            errors = errors.replace(tmp_path, filename)
            
            # Extract just the error lines (skip verbose tsc output)
            error_lines = []
            for line in errors.split("\n"):
                if line.strip() and ("error TS" in line or line.startswith(" ")):
                    error_lines.append(line)
            
            error_msg = "\n".join(error_lines[:10])  # Limit to first 10 error lines
            if len(error_lines) > 10:
                error_msg += f"\n... and {len(error_lines) - 10} more errors"
            
            return False, error_msg.strip() or "TypeScript syntax check failed"
            
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
    except subprocess.TimeoutExpired:
        return False, f"TypeScript syntax check timed out after {SYNTAX_CHECK_TIMEOUT}s"
    except FileNotFoundError:
        # tsc/npx not found - skip syntax check but log warning
        logger.warning("npx/tsc not found, skipping syntax validation")
        return True, ""  # Allow creation to proceed
    except Exception as exc:
        logger.error("Syntax check error", extra={"error": str(exc)})
        return False, f"Syntax check failed: {exc}"


# ============================================================================
# NPM Command Helpers
# ============================================================================


def _truncate_output(output: str, limit: int) -> tuple[str, bool]:
    """Truncate output to limit, returning (truncated_output, was_truncated)."""
    if len(output) <= limit:
        return output, False
    return output[:limit] + f"\n\n... (truncated, {len(output) - limit} chars omitted)", True


def _run_npm_command(
    command: str,
    timeout: int,
    output_limit: int,
) -> dict[str, Any]:
    """
    Run an npm command in the sample-dashboard directory.
    
    Args:
        command: The npm script to run (e.g., "lint", "build").
        timeout: Maximum seconds to wait for completion.
        output_limit: Maximum characters for stdout/stderr.
        
    Returns:
        Dictionary with exit_code, stdout, stderr, passed, truncated.
    """
    try:
        result = subprocess.run(
            ["npm", "run", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SAMPLE_DASHBOARD_ROOT),
            shell=True,  # Required on Windows for npm
        )
        
        stdout, stdout_truncated = _truncate_output(result.stdout, output_limit)
        stderr, stderr_truncated = _truncate_output(result.stderr, output_limit)
        
        return {
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "passed": result.returncode == 0,
            "truncated": stdout_truncated or stderr_truncated,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "passed": False,
            "truncated": False,
            "timeout": True,
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "npm not found. Ensure Node.js is installed and in PATH.",
            "passed": False,
            "truncated": False,
        }
    except Exception as exc:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command failed: {exc}",
            "passed": False,
            "truncated": False,
        }


# ============================================================================
# Tool Implementations
# ============================================================================


def run_lint(tool_context: ToolContext | None = None) -> dict[str, Any]:
    """
    Run ESLint on the sample-dashboard project.
    
    Executes `npm run lint` in the sample-dashboard directory.
    Use this after creating or modifying files to check for linting errors.
    """
    logger.info("Running lint", extra={"project": str(SAMPLE_DASHBOARD_ROOT)})
    
    result = _run_npm_command("lint", LINT_TIMEOUT, LINT_OUTPUT_LIMIT)
    result["project_path"] = str(SAMPLE_DASHBOARD_ROOT)
    
    if result["passed"]:
        logger.info("Lint passed")
    else:
        logger.warning("Lint failed", extra={"exit_code": result["exit_code"]})
    
    return result


def run_type_check(tool_context: ToolContext | None = None) -> dict[str, Any]:
    """
    Run TypeScript type-check on the sample-dashboard project.
    
    Executes `npm run type-check` in the sample-dashboard directory.
    Faster than a full build - only checks types without compiling.
    Use this after creating or modifying files to verify type correctness.
    """
    logger.info("Running type-check", extra={"project": str(SAMPLE_DASHBOARD_ROOT)})
    
    result = _run_npm_command("type-check", TYPE_CHECK_TIMEOUT, TYPE_CHECK_OUTPUT_LIMIT)
    result["project_path"] = str(SAMPLE_DASHBOARD_ROOT)
    
    if result["passed"]:
        logger.info("Type-check passed")
    else:
        logger.warning("Type-check failed", extra={"exit_code": result["exit_code"]})
    
    return result


def run_build(tool_context: ToolContext | None = None) -> dict[str, Any]:
    """
    Run Next.js build on the sample-dashboard project.
    
    Executes `npm run build` for full TypeScript type checking and compilation.
    Slower than lint (~30-60s) but catches type errors and import issues.
    """
    logger.info("Running build", extra={"project": str(SAMPLE_DASHBOARD_ROOT)})
    
    result = _run_npm_command("build", BUILD_TIMEOUT, BUILD_OUTPUT_LIMIT)
    result["project_path"] = str(SAMPLE_DASHBOARD_ROOT)
    
    if result["passed"]:
        logger.info("Build passed")
    else:
        logger.warning("Build failed", extra={"exit_code": result["exit_code"]})
    
    return result


def run_check_openapi(tool_context: ToolContext | None = None) -> dict[str, Any]:
    """
    Run the OpenAPI consistency check for Hono routes.
    
    Executes `npm run check-openapi` in the backend project. Ensures all routes
    are registered via `register(app)` and included in the OpenAPI registry.
    """
    logger.info("Running check-openapi", extra={"project": str(SAMPLE_DASHBOARD_ROOT)})
    result = _run_npm_command("check-openapi", OPENAPI_CHECK_TIMEOUT, OPENAPI_OUTPUT_LIMIT)
    result["project_path"] = str(SAMPLE_DASHBOARD_ROOT)
    if result["passed"]:
        logger.info("OpenAPI check passed")
    else:
        logger.warning("OpenAPI check failed", extra={"exit_code": result["exit_code"]})
    return result


# ============================================================================
# Tool Exports
# ============================================================================

run_lint_tool = FunctionTool(func=run_lint)
run_type_check_tool = FunctionTool(func=run_type_check)

# run_build is kept for internal/manual use but not exposed as a tool
# Use run_type_check_tool for faster type verification
run_build_tool = FunctionTool(func=run_build)  # Internal use only
run_check_openapi_tool = FunctionTool(func=run_check_openapi)
