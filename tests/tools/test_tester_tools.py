"""
Unit tests for Testing Agent tools.

Tests the tester tools:
- create_test
- run_npm_test
- read_dev_report
- read_backend_manifest
- get_tester_tools

Also tests shared tools used by tester:
- delete_file
- file_exists
- get_sample_rows
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.tester import (
    create_test,
    create_test_tool,
    run_npm_test,
    run_npm_test_tool,
    read_dev_report,
    read_dev_report_tool,
    read_backend_manifest,
    read_backend_manifest_tool,
    get_tester_tools,
    TESTS_ROOT,
    SAMPLE_DASHBOARD_ROOT,
    TEST_TIMEOUT,
)

from src.tools.shared import (
    delete_file,
    delete_file_tool,
    file_exists,
    file_exists_tool,
    get_sample_rows,
    get_sample_rows_tool,
    DEFAULT_MAX_SAMPLE_ROWS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_tool_context():
    """Create a mock ToolContext."""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


@pytest.fixture
def mock_tool_context_with_run_dir(temp_dir):
    """Create a mock ToolContext with run_dir set."""
    ctx = MagicMock()
    ctx.state = {"run_dir": str(temp_dir)}
    return ctx


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_dev_report_in_run_dir(temp_dir):
    """Create a sample DevReport JSON file in the run_dir structure."""
    # Create dev_reports directory
    dev_reports_dir = temp_dir / "dev_reports"
    dev_reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_data = {
        "artifact_id": "sales_summary",
        "artifact_type": "route",
        "status": "success",
        "summary": "Created sales summary API route",
        "current_state": {
            "code_path": "src/app/api/sales/route.ts",
            "dependent_code_paths": [],
            "exports": ["GET"],
        },
        "changes": {
            "files_created": ["src/app/api/sales/route.ts"],
            "files_modified": [],
            "files_deleted": [],
        },
        "files_changed": [
            {"path": "src/app/api/sales/route.ts", "action": "created", "description": "Main route handler"}
        ],
        "dependencies": [],
        "lint_passed": True,
        "type_check_passed": True,
        "timestamp": "2025-01-01T12:00:00Z",
    }
    
    report_path = dev_reports_dir / "sales_summary.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f)
    
    return report_path, temp_dir


@pytest.fixture
def sample_backend_manifest(temp_dir):
    """Create a sample backend manifest JSON file."""
    manifest_data = {
        "artifacts": [
            {"id": "sales_summary", "status": "success", "type": "route"},
            {"id": "data_utils", "status": "success", "type": "helper"},
        ],
        "total_artifacts": 2,
        "completed": 2,
        "failed": 0,
    }
    
    manifest_path = temp_dir / "backend_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)
    
    return manifest_path, temp_dir


@pytest.fixture
def sample_csv(temp_dir):
    """Create a sample CSV file."""
    csv_content = """id,name,value,category
1,Item A,100,Electronics
2,Item B,200,Clothing
3,Item C,150,Electronics
"""
    csv_path = temp_dir / "test_data.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_content)
    return csv_path


# =============================================================================
# create_test Tests
# =============================================================================

class TestCreateTest:
    """Tests for create_test tool."""

    def test_create_test_validates_describe_block(self, mock_tool_context):
        """Test that tests must have a describe block."""
        invalid_content = """
import { GET } from '@/app/api/sales/route';

test('should work', () => {
    expect(true).toBe(true);
});
"""
        result = create_test(
            name="sales_summary",
            content=invalid_content,
            test_type="api",
            tool_context=mock_tool_context,
        )
        
        assert result["success"] is False
        assert "describe" in result["error"].lower()

    def test_create_test_validates_test_block(self, mock_tool_context):
        """Test that tests must have test or it blocks."""
        invalid_content = """
describe('Sales API', () => {
    // No tests here
});
"""
        result = create_test(
            name="sales_summary",
            content=invalid_content,
            test_type="api",
            tool_context=mock_tool_context,
        )
        
        assert result["success"] is False
        assert "test" in result["error"].lower() or "it" in result["error"].lower()

    def test_create_test_validates_expect(self, mock_tool_context):
        """Test that tests must have expect assertions."""
        invalid_content = """
describe('Sales API', () => {
    it('should do something', () => {
        console.log('no assertions');
    });
});
"""
        result = create_test(
            name="sales_summary",
            content=invalid_content,
            test_type="api",
            tool_context=mock_tool_context,
        )
        
        assert result["success"] is False
        assert "expect" in result["error"].lower()

    def test_create_test_rejects_invalid_test_type(self, mock_tool_context):
        """Test that invalid test types are rejected."""
        valid_content = """
describe('Test', () => {
    it('works', () => {
        expect(true).toBe(true);
    });
});
"""
        result = create_test(
            name="test",
            content=valid_content,
            test_type="invalid",
            tool_context=mock_tool_context,
        )
        
        assert result["success"] is False
        assert "Invalid test_type" in result["error"]

    def test_create_test_normalizes_name(self, mock_tool_context):
        """Test that test names are normalized (removes .test.ts suffix)."""
        valid_content = """
describe('Test', () => {
    it('works', () => {
        expect(true).toBe(true);
    });
});
"""
        # Mock the file write to avoid actual filesystem operations
        with patch("src.tools.tester.creation._validate_test_path") as mock_validate:
            mock_path = TESTS_ROOT / "api" / "sales.test.ts"
            mock_validate.return_value = (True, mock_path, "")
            
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Path, "mkdir"):
                    with patch.object(Path, "write_text"):
                        result = create_test(
                            name="sales.test.ts",  # Should be normalized
                            content=valid_content,
                            test_type="api",
                            tool_context=mock_tool_context,
                        )
                        
                        # Check that the path was normalized
                        assert "sales.test.ts" in result.get("path", "") or result["success"]


# =============================================================================
# run_npm_test Tests
# =============================================================================

class TestRunNpmTest:
    """Tests for run_npm_test tool."""

    @patch("src.tools.tester.testing.subprocess.run")
    def test_run_npm_test_success(self, mock_run, mock_tool_context):
        """Test successful test execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Test Suites: 1 passed, 1 total\nTests: 3 passed, 3 total",
            stderr="",
        )
        
        result = run_npm_test(tool_context=mock_tool_context)
        
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "3 passed" in result["output"]

    @patch("src.tools.tester.testing.subprocess.run")
    def test_run_npm_test_with_pattern(self, mock_run, mock_tool_context):
        """Test running tests with a pattern filter."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="PASS tests/api/sales.test.ts",
            stderr="",
        )
        
        result = run_npm_test(test_pattern="sales", tool_context=mock_tool_context)
        
        assert result["success"] is True
        assert "sales" in result["command"]

    @patch("src.tools.tester.testing.subprocess.run")
    def test_run_npm_test_failure(self, mock_run, mock_tool_context):
        """Test failed test execution."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="FAIL tests/api/sales.test.ts\n  ✕ should return 200",
            stderr="",
        )
        
        result = run_npm_test(tool_context=mock_tool_context)
        
        assert result["success"] is False
        assert result["exit_code"] == 1
        assert result["tests_failed"] is True

    @patch("src.tools.tester.testing.subprocess.run")
    def test_run_npm_test_timeout(self, mock_run, mock_tool_context):
        """Test handling of timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm test", timeout=TEST_TIMEOUT)
        
        result = run_npm_test(tool_context=mock_tool_context)
        
        assert result["success"] is False
        assert "timed out" in result["error"].lower()


# =============================================================================
# read_dev_report Tests
# =============================================================================

class TestReadDevReport:
    """Tests for read_dev_report tool."""

    def test_read_dev_report_success(self, sample_dev_report_in_run_dir):
        """Test successful DevReport reading."""
        report_path, run_dir = sample_dev_report_in_run_dir
        
        ctx = MagicMock()
        ctx.state = {"run_dir": str(run_dir)}
        
        result = read_dev_report("sales_summary", tool_context=ctx)
        
        assert "error" not in result
        assert "report" in result
        assert result["report"]["artifact_id"] == "sales_summary"
        assert result["report"]["status"] == "success"

    def test_read_dev_report_not_found(self, temp_dir):
        """Test handling of missing artifact report."""
        ctx = MagicMock()
        ctx.state = {"run_dir": str(temp_dir)}
        
        result = read_dev_report("nonexistent_artifact", tool_context=ctx)
        
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_read_dev_report_no_tool_context(self):
        """Test handling of missing tool context."""
        result = read_dev_report("sales_summary", tool_context=None)
        
        assert "error" in result
        assert "Tool context not provided" in result["error"]

    def test_read_dev_report_no_run_dir(self, mock_tool_context):
        """Test handling of missing run_dir in state."""
        result = read_dev_report("sales_summary", tool_context=mock_tool_context)
        
        assert "error" in result
        assert "run_dir" in result["error"].lower()


# =============================================================================
# read_backend_manifest Tests
# =============================================================================

class TestReadBackendManifest:
    """Tests for read_backend_manifest tool."""

    def test_read_backend_manifest_success(self, sample_backend_manifest):
        """Test successful manifest reading."""
        manifest_path, run_dir = sample_backend_manifest
        
        ctx = MagicMock()
        ctx.state = {"run_dir": str(run_dir)}
        
        result = read_backend_manifest(tool_context=ctx)
        
        assert "error" not in result
        assert "manifest" in result
        assert result["manifest"]["total_artifacts"] == 2

    def test_read_backend_manifest_not_found(self, temp_dir):
        """Test handling of missing manifest."""
        ctx = MagicMock()
        ctx.state = {"run_dir": str(temp_dir)}
        
        result = read_backend_manifest(tool_context=ctx)
        
        assert "error" in result
        assert "not found" in result["error"].lower()


# =============================================================================
# Shared Tools Tests (delete_file, file_exists, get_sample_rows)
# =============================================================================

class TestDeleteFile:
    """Tests for delete_file shared tool."""

    def test_delete_file_success(self, temp_dir, mock_tool_context):
        """Test successful file deletion with allowed path."""
        test_file = temp_dir / "to_delete.txt"
        test_file.write_text("content")
        
        # Pass the temp_dir as an allowed path
        result = delete_file(
            str(test_file),
            allowed_paths=[str(temp_dir)],
            tool_context=mock_tool_context,
        )
        
        assert result["deleted"] is True
        assert not test_file.exists()

    def test_delete_file_blocked_path(self, mock_tool_context):
        """Test that paths outside allowed directories are blocked."""
        result = delete_file(
            "/etc/important_file",
            allowed_paths=["/tmp"],
            tool_context=mock_tool_context,
        )
        
        assert result["deleted"] is False
        assert "not in allowed" in result["error"].lower()

    def test_delete_file_not_found(self, temp_dir, mock_tool_context):
        """Test deleting non-existent file."""
        nonexistent = temp_dir / "nonexistent.txt"
        
        result = delete_file(
            str(nonexistent),
            allowed_paths=[str(temp_dir)],
            tool_context=mock_tool_context,
        )
        
        assert result["deleted"] is False
        assert "does not exist" in result["error"].lower()


class TestFileExists:
    """Tests for file_exists shared tool."""

    def test_file_exists_true(self, temp_dir, mock_tool_context):
        """Test checking existing file."""
        test_file = temp_dir / "exists.txt"
        test_file.write_text("content")
        
        result = file_exists(str(test_file), tool_context=mock_tool_context)
        
        assert result["exists"] is True

    def test_file_exists_false(self, temp_dir, mock_tool_context):
        """Test checking non-existing file."""
        nonexistent = temp_dir / "nonexistent.txt"
        
        result = file_exists(str(nonexistent), tool_context=mock_tool_context)
        
        assert result["exists"] is False


class TestGetSampleRows:
    """Tests for get_sample_rows shared tool."""

    def test_get_sample_rows_default_limit(self, sample_csv, mock_tool_context):
        """Test that default limit is applied."""
        from unittest.mock import patch
        
        # Mock path validation to allow temp directory
        with patch("src.tools.shared.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, sample_csv, "")
            
            result = get_sample_rows(
                str(sample_csv),
                num_rows=10,  # Ask for more than default
                max_rows=DEFAULT_MAX_SAMPLE_ROWS,
                tool_context=mock_tool_context,
            )
        
        assert "error" not in result
        assert len(result["rows"]) <= DEFAULT_MAX_SAMPLE_ROWS

    def test_get_sample_rows_returns_columns(self, sample_csv, mock_tool_context):
        """Test that column names are returned."""
        from unittest.mock import patch
        
        with patch("src.tools.shared.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, sample_csv, "")
            
            result = get_sample_rows(
                str(sample_csv),
                num_rows=1,
                max_rows=5,
                tool_context=mock_tool_context,
            )
        
        assert "columns" in result
        assert "id" in result["columns"]
        assert "name" in result["columns"]

    def test_get_sample_rows_not_csv(self, temp_dir, mock_tool_context):
        """Test that non-CSV files are rejected."""
        from unittest.mock import patch
        
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("not a csv")
        
        with patch("src.tools.shared.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, txt_file, "")
            
            result = get_sample_rows(
                str(txt_file),
                num_rows=1,
                max_rows=5,
                tool_context=mock_tool_context,
            )
        
        assert "error" in result
        assert "not a csv" in result["error"].lower()


# =============================================================================
# get_tester_tools Tests
# =============================================================================

class TestGetTesterTools:
    """Tests for get_tester_tools factory function."""

    def test_get_tester_tools_returns_list(self):
        """Test that get_tester_tools returns a list."""
        tools = get_tester_tools()
        
        assert isinstance(tools, list)
        assert len(tools) >= 5  # At minimum: create_test, run_npm_test, read_dev_report, read_backend_manifest, and some shared tools

    def test_get_tester_tools_contains_expected_tools(self):
        """Test that all expected tools are included."""
        tools = get_tester_tools()
        
        # Check tool names by looking at the wrapped function names
        tool_names = [t.func.__name__ for t in tools]
        
        assert "create_test" in tool_names
        assert "run_npm_test" in tool_names
        assert "read_dev_report" in tool_names
        assert "read_backend_manifest" in tool_names
        # Shared tools
        assert "get_sample_rows" in tool_names
        assert "delete_file" in tool_names
        assert "file_exists" in tool_names

    def test_tools_are_function_tools(self):
        """Test that all tools are FunctionTool instances."""
        from google.adk.tools.function_tool import FunctionTool
        
        tools = get_tester_tools()
        
        for tool in tools:
            assert isinstance(tool, FunctionTool)


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_test_timeout_reasonable(self):
        """Test that TEST_TIMEOUT is a reasonable value."""
        assert TEST_TIMEOUT >= 60  # At least 1 minute
        assert TEST_TIMEOUT <= 600  # No more than 10 minutes

    def test_default_max_sample_rows(self):
        """Test that DEFAULT_MAX_SAMPLE_ROWS is a sensible default."""
        assert DEFAULT_MAX_SAMPLE_ROWS >= 1
        assert DEFAULT_MAX_SAMPLE_ROWS <= 10

    def test_tests_root_path(self):
        """Test that TESTS_ROOT is set correctly."""
        assert TESTS_ROOT == SAMPLE_DASHBOARD_ROOT / "tests"
