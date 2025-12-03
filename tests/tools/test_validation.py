"""
Tests for validation tools (run_lint, run_build) and internal syntax checking.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from src.tools.backend.validation import (
    run_lint,
    run_build,
    _check_typescript_syntax,
    LINT_TIMEOUT,
    BUILD_TIMEOUT,
    LINT_OUTPUT_LIMIT,
    BUILD_OUTPUT_LIMIT,
)


class TestCheckTypescriptSyntaxInternal:
    """Tests for the internal _check_typescript_syntax helper."""
    
    def test_timeout_handling(self):
        """Should handle subprocess timeout gracefully."""
        with patch("src.tools.backend.validation.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("tsc", 10)
            
            is_valid, errors = _check_typescript_syntax("export const x = 1;")
            
            assert is_valid is False
            assert "timed out" in errors.lower()
    
    def test_tsc_not_found(self):
        """Should gracefully handle missing tsc/npx."""
        with patch("src.tools.backend.validation.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("npx not found")
            
            is_valid, errors = _check_typescript_syntax("export const x = 1;")
            
            # Should allow creation to proceed if tsc is not available
            assert is_valid is True
            assert errors == ""
    
    def test_successful_check(self):
        """Should return success for valid TypeScript."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            is_valid, errors = _check_typescript_syntax("export const x = 1;")
            
            assert is_valid is True
            assert errors == ""
    
    def test_failed_check_with_errors(self):
        """Should return errors for invalid TypeScript."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "error TS1005: ';' expected."
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            is_valid, errors = _check_typescript_syntax("export const x = ")
            
            assert is_valid is False
            assert "error TS" in errors or errors


class TestRunLint:
    """Tests for the run_lint tool."""
    
    def test_lint_success(self):
        """Should return passed=True when lint succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "No lint errors found."
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            result = run_lint()
            
            assert result["passed"] is True
            assert result["exit_code"] == 0
            assert "project_path" in result
    
    def test_lint_failure(self):
        """Should return passed=False when lint fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "src/app/api/test/route.ts:5:10: 'unused' is defined but never used."
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            result = run_lint()
            
            assert result["passed"] is False
            assert result["exit_code"] == 1
            assert "unused" in result["stdout"]
    
    def test_lint_timeout(self):
        """Should handle lint timeout gracefully."""
        with patch("src.tools.backend.validation.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("npm", LINT_TIMEOUT)
            
            result = run_lint()
            
            assert result["passed"] is False
            assert "timeout" in result.get("stderr", "").lower() or result.get("timeout")
    
    def test_lint_npm_not_found(self):
        """Should handle missing npm gracefully."""
        with patch("src.tools.backend.validation.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("npm not found")
            
            result = run_lint()
            
            assert result["passed"] is False
            assert "npm not found" in result["stderr"]


class TestRunBuild:
    """Tests for the run_build tool."""
    
    def test_build_success(self):
        """Should return passed=True when build succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Build completed successfully."
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            result = run_build()
            
            assert result["passed"] is True
            assert result["exit_code"] == 0
            assert "project_path" in result
    
    def test_build_failure(self):
        """Should return passed=False when build fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Type error: Property 'foo' does not exist on type 'Bar'."
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            result = run_build()
            
            assert result["passed"] is False
            assert result["exit_code"] == 1
            assert "foo" in result["stderr"]
    
    def test_build_timeout(self):
        """Should handle build timeout gracefully."""
        with patch("src.tools.backend.validation.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("npm", BUILD_TIMEOUT)
            
            result = run_build()
            
            assert result["passed"] is False
            assert "timeout" in result.get("stderr", "").lower() or result.get("timeout")


class TestOutputTruncation:
    """Tests for output truncation behavior."""
    
    def test_lint_output_truncated(self):
        """Should truncate lint output exceeding limit."""
        long_output = "x" * (LINT_OUTPUT_LIMIT + 1000)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = long_output
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            result = run_lint()
            
            assert result["truncated"] is True
            assert len(result["stdout"]) < len(long_output)
            assert "truncated" in result["stdout"]
    
    def test_build_output_truncated(self):
        """Should truncate build output exceeding limit."""
        long_output = "y" * (BUILD_OUTPUT_LIMIT + 1000)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = long_output
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            result = run_build()
            
            assert result["truncated"] is True
            assert len(result["stdout"]) < len(long_output)
    
    def test_short_output_not_truncated(self):
        """Should not truncate output within limits."""
        short_output = "Short output"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = short_output
        mock_result.stderr = ""
        
        with patch("src.tools.backend.validation.subprocess.run", return_value=mock_result):
            result = run_lint()
            
            assert result["truncated"] is False
            assert result["stdout"] == short_output


class TestConstants:
    """Tests for validation constants."""
    
    def test_lint_timeout_reasonable(self):
        """Lint timeout should be reasonable (30-120 seconds)."""
        assert 30 <= LINT_TIMEOUT <= 120
    
    def test_build_timeout_reasonable(self):
        """Build timeout should be reasonable (60-300 seconds)."""
        assert 60 <= BUILD_TIMEOUT <= 300
    
    def test_output_limits_reasonable(self):
        """Output limits should be reasonable."""
        assert LINT_OUTPUT_LIMIT >= 1000
        assert BUILD_OUTPUT_LIMIT >= LINT_OUTPUT_LIMIT
