"""
Test execution tools for the Testing Agent.

Provides tools for running Jest tests via npm test.
"""
from __future__ import annotations

import subprocess
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.tools.tester.filesystem import SAMPLE_DASHBOARD_ROOT

logger = get_logger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Timeout for test execution in seconds
TEST_TIMEOUT = 120


# ============================================================================
# Tool Implementations
# ============================================================================


def run_npm_test(
    test_pattern: str | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Run Jest tests via npm test in the sample-dashboard project.
    
    Executes: npm test [-- --testPathPattern=<pattern>]
    
    Returns test output including pass/fail status. Use the output to determine:
    - Which tests passed/failed
    - Error messages and stack traces for failures
    - Total test counts
    
    Args:
        test_pattern: Optional test file pattern to filter which tests run.
                      Examples:
                      - "sales" → runs tests matching *sales*
                      - "api/sales" → runs tests in tests/api/ matching *sales*
                      - None → runs all tests
    """
    # Build the command
    cmd = ["npm", "test"]
    
    if test_pattern:
        # Add the testPathPattern flag for Jest
        cmd.extend(["--", f"--testPathPattern={test_pattern}"])
    
    try:
        logger.info(
            "run_npm_test starting",
            extra={
                "agent": "tester",
                "pattern": test_pattern,
                "cwd": str(SAMPLE_DASHBOARD_ROOT),
            },
        )
        
        result = subprocess.run(
            cmd,
            cwd=str(SAMPLE_DASHBOARD_ROOT),
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT,
            shell=True,  # Required on Windows for npm
        )
        
        # Combine stdout and stderr for full output
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        
        # Parse basic test results from output
        tests_passed = "Tests:" in output and ("passed" in output.lower() or "✓" in output)
        tests_failed = result.returncode != 0 or "fail" in output.lower() or "✗" in output
        
        # Try to extract test counts
        test_summary = {}
        if "Tests:" in output:
            # Jest output format: "Tests: X passed, Y failed, Z total"
            import re
            counts = re.search(r'Tests:\s*(\d+)\s*passed', output)
            if counts:
                test_summary["passed"] = int(counts.group(1))
            counts = re.search(r'(\d+)\s*failed', output)
            if counts:
                test_summary["failed"] = int(counts.group(1))
            counts = re.search(r'(\d+)\s*total', output)
            if counts:
                test_summary["total"] = int(counts.group(1))
        
        logger.info(
            "run_npm_test completed",
            extra={
                "agent": "tester",
                "pattern": test_pattern,
                "exit_code": result.returncode,
                "passed": tests_passed,
            },
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "output": output[:10000],  # Truncate very long output
            "tests_passed": tests_passed and not tests_failed,
            "tests_failed": tests_failed,
            "test_summary": test_summary if test_summary else None,
            "command": " ".join(cmd),
        }
        
    except subprocess.TimeoutExpired:
        logger.error(
            "run_npm_test timeout",
            extra={"agent": "tester", "pattern": test_pattern, "timeout": TEST_TIMEOUT},
        )
        return {
            "success": False,
            "error": f"Test execution timed out after {TEST_TIMEOUT} seconds",
            "command": " ".join(cmd),
        }
    except Exception as exc:
        logger.error(
            "run_npm_test failed",
            extra={"agent": "tester", "pattern": test_pattern, "error": str(exc)},
        )
        return {
            "success": False,
            "error": f"Failed to run tests: {exc}",
            "command": " ".join(cmd),
        }


# ============================================================================
# Tool Exports
# ============================================================================

run_npm_test_tool = FunctionTool(func=run_npm_test)
