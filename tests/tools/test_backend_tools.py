"""
Test cases for Backend Agent tools.

These tests verify the filesystem and data access tools work correctly
against the sample-dashboard project structure.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from src.tools.backend.filesystem import (
    ALLOWED_PATHS,
    SAMPLE_DASHBOARD_ROOT,
    _validate_path,
    _resolve_allowed_paths,
    _get_relative_display_path,
    read_file,
    inspect_dir,
    search_content,
)
from src.tools.backend.data_access import (
    MAX_SAMPLE_ROWS,
    get_sample_rows,
    read_data_profile,
    read_dashboard_concept,
    copy_data_to_project,
)


# =============================================================================
# Test Fixtures
# =============================================================================


def _make_tool_context(state: dict[str, Any]) -> SimpleNamespace:
    """Create a mock ToolContext with the given state."""
    return SimpleNamespace(state=state)


@pytest.fixture
def sample_dashboard_path() -> Path:
    """Return the path to the sample-dashboard project."""
    return SAMPLE_DASHBOARD_ROOT


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    """Create a temporary run directory structure for testing."""
    # Create data_analysis subdirectories
    data_analysis = tmp_path / "data_analysis"
    cleaned_dir = data_analysis / "cleaned"
    cleaned_dir.mkdir(parents=True)
    
    # Create sample data profile
    profile_path = data_analysis / "data_profile.md"
    profile_path.write_text("# Data Profile\n\n- Rows: 100\n- Columns: 5", encoding="utf-8")
    
    # Create sample cleaned CSV
    csv_path = cleaned_dir / "cleaned.csv"
    csv_path.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300", encoding="utf-8")
    
    # Create planner subdirectory with dashboard concept
    planner_dir = tmp_path / "planner"
    planner_dir.mkdir(parents=True)
    
    concept = {
        "goal": "Sales Dashboard",
        "kpis": [{"name": "total_revenue", "formula": "SUM(revenue)"}],
        "visuals": [{"id": "chart1", "type": "bar"}],
    }
    concept_path = planner_dir / "dashboard_concept.json"
    concept_path.write_text(json.dumps(concept), encoding="utf-8")
    
    return tmp_path


@pytest.fixture
def temp_csv(tmp_path: Path) -> Path:
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"
    rows = ["col_a,col_b,col_c"]
    for i in range(10):
        rows.append(f"val_{i},data_{i},{i * 100}")
    csv_path.write_text("\n".join(rows), encoding="utf-8")
    return csv_path


# =============================================================================
# Path Validation Tests
# =============================================================================


class TestPathValidation:
    """Tests for path validation and scoping."""
    
    def test_allowed_paths_configuration(self):
        """Verify ALLOWED_PATHS contains expected paths."""
        assert len(ALLOWED_PATHS) > 0
        # Check for sample-dashboard paths
        assert any("sample-dashboard" in p for p in ALLOWED_PATHS)
        # Check for run_dir placeholders
        assert any("{run_dir}" in p for p in ALLOWED_PATHS)
    
    def test_resolve_allowed_paths_without_run_dir(self):
        """Paths without {run_dir} should resolve, placeholders should be skipped."""
        resolved = _resolve_allowed_paths(run_dir=None)
        # Static paths should be included
        static_paths = [p for p in ALLOWED_PATHS if "{run_dir}" not in p]
        assert len(resolved) == len(static_paths)
    
    def test_resolve_allowed_paths_with_run_dir(self, tmp_path: Path):
        """Paths with {run_dir} should be resolved when run_dir is provided."""
        resolved = _resolve_allowed_paths(run_dir=str(tmp_path))
        # Should include both static and resolved dynamic paths
        assert len(resolved) == len(ALLOWED_PATHS)
    
    def test_validate_path_allowed_api_directory(self, sample_dashboard_path: Path):
        """Paths under sample-dashboard/src/app/api should be allowed."""
        test_path = sample_dashboard_path / "src" / "app" / "api" / "test" / "route.ts"
        is_valid, resolved, error = _validate_path(test_path, run_dir=None, allow_new=True)
        assert is_valid is True
        assert error == ""
    
    def test_validate_path_allowed_models_directory(self, sample_dashboard_path: Path):
        """Paths under sample-dashboard/src/models should be allowed."""
        test_path = sample_dashboard_path / "src" / "models" / "TestModel.ts"
        is_valid, resolved, error = _validate_path(test_path, run_dir=None, allow_new=True)
        assert is_valid is True
    
    def test_validate_path_allowed_data_directory(self, sample_dashboard_path: Path):
        """Paths under sample-dashboard/data should be allowed."""
        test_path = sample_dashboard_path / "data" / "cleaned" / "data.csv"
        is_valid, resolved, error = _validate_path(test_path, run_dir=None, allow_new=True)
        assert is_valid is True
    
    def test_validate_path_blocked_outside_allowed(self):
        """Paths outside allowed directories should be blocked."""
        test_path = Path("C:/Windows/System32/config.sys")
        is_valid, resolved, error = _validate_path(test_path, run_dir=None)
        assert is_valid is False
        assert "not in allowed locations" in error
    
    def test_validate_path_blocked_project_root(self, sample_dashboard_path: Path):
        """Files in project root (not in allowed subdirs) should be blocked."""
        test_path = sample_dashboard_path / "package.json"
        is_valid, resolved, error = _validate_path(test_path, run_dir=None)
        assert is_valid is False
        assert "not in allowed locations" in error
    
    def test_validate_path_with_run_dir_artifacts(self, temp_run_dir: Path):
        """Run directory artifacts should be accessible when run_dir is set."""
        profile_path = temp_run_dir / "data_analysis" / "data_profile.md"
        is_valid, resolved, error = _validate_path(profile_path, run_dir=str(temp_run_dir))
        assert is_valid is True
    
    def test_get_relative_display_path(self, sample_dashboard_path: Path):
        """Display paths should be relative to sample-dashboard when possible."""
        full_path = sample_dashboard_path / "src" / "app" / "api" / "route.ts"
        relative = _get_relative_display_path(full_path)
        assert relative == "src\\app\\api\\route.ts" or relative == "src/app/api/route.ts"


# =============================================================================
# read_file Tests
# =============================================================================


class TestReadFile:
    """Tests for the read_file tool."""
    
    def test_read_existing_file(self, sample_dashboard_path: Path):
        """Should read existing files in allowed paths."""
        # This test requires the sample-dashboard to have a sales model
        model_path = sample_dashboard_path / "src" / "models" / "sales.ts"
        if not model_path.exists():
            pytest.skip("Sample sales.ts model not found")
        
        result = read_file(str(model_path), tool_context=None)
        
        assert "error" not in result
        assert "content" in result
        assert result["total_lines"] > 0
        assert "SaleRecord" in result["content"]
    
    def test_read_file_with_line_range(self, sample_dashboard_path: Path):
        """Should return only specified line range."""
        model_path = sample_dashboard_path / "src" / "models" / "sales.ts"
        if not model_path.exists():
            pytest.skip("Sample sales.ts model not found")
        
        result = read_file(str(model_path), from_line=1, to_line=5, tool_context=None)
        
        assert "error" not in result
        assert result["lines_returned"] <= 5
        assert result["lines_returned"] < result["total_lines"]
    
    def test_read_file_blocked_path(self, sample_dashboard_path: Path):
        """Should return error for disallowed paths."""
        blocked_path = sample_dashboard_path / "package.json"
        
        result = read_file(str(blocked_path), tool_context=None)
        
        assert "error" in result
        assert "not in allowed locations" in result["error"]
    
    def test_read_nonexistent_file(self, sample_dashboard_path: Path):
        """Should return error for non-existent files."""
        fake_path = sample_dashboard_path / "src" / "models" / "nonexistent.ts"
        
        result = read_file(str(fake_path), tool_context=None)
        
        assert "error" in result
    
    def test_read_file_with_run_dir_context(self, temp_run_dir: Path):
        """Should read files from run directory when context is provided."""
        tc = _make_tool_context({"run_dir": str(temp_run_dir)})
        profile_path = temp_run_dir / "data_analysis" / "data_profile.md"
        
        result = read_file(str(profile_path), tool_context=tc)
        
        assert "error" not in result
        assert "Data Profile" in result["content"]


# =============================================================================
# inspect_dir Tests
# =============================================================================


class TestInspectDir:
    """Tests for the inspect_dir tool."""
    
    def test_inspect_api_directory(self, sample_dashboard_path: Path):
        """Should list contents of api directory."""
        api_path = sample_dashboard_path / "src" / "app" / "api"
        if not api_path.exists():
            pytest.skip("API directory not found")
        
        result = inspect_dir(str(api_path), tool_context=None)
        
        assert "error" not in result
        assert "entries" in result
        assert isinstance(result["entries"], list)
    
    def test_inspect_models_directory(self, sample_dashboard_path: Path):
        """Should list contents of models directory."""
        models_path = sample_dashboard_path / "src" / "models"
        if not models_path.exists():
            pytest.skip("Models directory not found")
        
        result = inspect_dir(str(models_path), tool_context=None)
        
        assert "error" not in result
        assert "entries" in result
        # Check that sales.ts is listed
        names = [e["name"] for e in result["entries"]]
        assert "sales.ts" in names
    
    def test_inspect_directory_entries_have_metadata(self, sample_dashboard_path: Path):
        """Directory entries should include name, is_dir, and size_bytes for files."""
        models_path = sample_dashboard_path / "src" / "models"
        if not models_path.exists():
            pytest.skip("Models directory not found")
        
        result = inspect_dir(str(models_path), tool_context=None)
        
        for entry in result["entries"]:
            assert "name" in entry
            assert "is_dir" in entry
            if not entry["is_dir"]:
                assert "size_bytes" in entry
    
    def test_inspect_blocked_directory(self, sample_dashboard_path: Path):
        """Should return error for directories outside allowed paths."""
        blocked_path = sample_dashboard_path / "node_modules"
        
        result = inspect_dir(str(blocked_path), tool_context=None)
        
        assert "error" in result
    
    def test_inspect_nonexistent_directory(self, sample_dashboard_path: Path):
        """Should return error for non-existent directories."""
        fake_path = sample_dashboard_path / "src" / "nonexistent"
        
        result = inspect_dir(str(fake_path), tool_context=None)
        
        assert "error" in result


# =============================================================================
# search_content Tests
# =============================================================================


class TestSearchContent:
    """Tests for the search_content tool."""
    
    def test_search_simple_string(self, sample_dashboard_path: Path):
        """Should find simple string matches."""
        result = search_content("NextResponse", tool_context=None)
        
        assert "error" not in result
        assert result["total_matches"] > 0
        assert len(result["matches"]) > 0
    
    def test_search_regex_pattern(self, sample_dashboard_path: Path):
        """Should support regex patterns."""
        result = search_content(r"export\s+type", tool_context=None)
        
        assert "error" not in result
        # Should find type exports in models
        assert result["total_matches"] > 0
    
    def test_search_with_file_pattern(self, sample_dashboard_path: Path):
        """Should filter by file pattern."""
        result = search_content("SaleRecord", path_pattern="*.ts", tool_context=None)
        
        assert "error" not in result
        # All matches should be in .ts files
        for match in result["matches"]:
            assert match["file"].endswith(".ts")
    
    def test_search_no_matches(self, sample_dashboard_path: Path):
        """Should return empty matches for non-existent patterns."""
        result = search_content("xyznonexistentpattern123", tool_context=None)
        
        assert "error" not in result
        assert result["total_matches"] == 0
        assert len(result["matches"]) == 0
    
    def test_search_invalid_regex(self):
        """Should return error for invalid regex patterns."""
        result = search_content("[invalid(regex", tool_context=None)
        
        assert "error" in result
        assert "Invalid regex" in result["error"]
    
    def test_search_respects_max_results(self, sample_dashboard_path: Path):
        """Should respect max_results parameter."""
        result = search_content("import", max_results=3, tool_context=None)
        
        assert len(result["matches"]) <= 3
        if result["total_matches"] > 3:
            assert result["truncated"] is True


# =============================================================================
# get_sample_rows Tests
# =============================================================================


class TestGetSampleRows:
    """Tests for the get_sample_rows tool."""
    
    def test_max_sample_rows_constant(self):
        """MAX_SAMPLE_ROWS should be 5."""
        assert MAX_SAMPLE_ROWS == 5
    
    def test_read_csv_default_rows(self, temp_csv: Path):
        """Should read 5 rows by default."""
        # Patch _validate_path to allow temp directory
        with patch("src.tools.backend.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), tool_context=None)
            
            assert "error" not in result
            assert result["total_rows_sampled"] == 5
            assert len(result["rows"]) == 5
    
    def test_read_csv_respects_max_limit(self, temp_csv: Path):
        """Should cap rows at MAX_SAMPLE_ROWS even if more requested."""
        with patch("src.tools.backend.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), num_rows=100, tool_context=None)
            
            assert "error" not in result
            # Should be capped at MAX_SAMPLE_ROWS
            assert result["total_rows_sampled"] <= MAX_SAMPLE_ROWS
    
    def test_read_csv_returns_columns(self, temp_csv: Path):
        """Should return column names."""
        with patch("src.tools.backend.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), tool_context=None)
            
            assert "columns" in result
            assert result["columns"] == ["col_a", "col_b", "col_c"]
    
    def test_read_csv_returns_dicts(self, temp_csv: Path):
        """Rows should be dictionaries with column keys."""
        with patch("src.tools.backend.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), num_rows=2, tool_context=None)
            
            assert "rows" in result
            for row in result["rows"]:
                assert isinstance(row, dict)
                assert "col_a" in row
                assert "col_b" in row
                assert "col_c" in row
    
    def test_read_csv_blocked_path(self):
        """Should return error for disallowed paths."""
        result = get_sample_rows("C:/Windows/System32/test.csv", tool_context=None)
        
        assert "error" in result
        assert "not in allowed locations" in result["error"]
    
    def test_read_non_csv_file(self, tmp_path: Path):
        """Should return error for non-CSV files."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a csv")
        
        with patch("src.tools.backend.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, txt_file, "")
            
            result = get_sample_rows(str(txt_file), tool_context=None)
            
            assert "error" in result
            assert "Not a CSV file" in result["error"]
    
    def test_read_sample_dashboard_csv(self, sample_dashboard_path: Path):
        """Should read CSV from sample-dashboard data directory."""
        csv_path = sample_dashboard_path / "data" / "cleaned" / "sales.csv"
        if not csv_path.exists():
            pytest.skip("Sample sales.csv not found")
        
        result = get_sample_rows(str(csv_path), tool_context=None)
        
        assert "error" not in result
        assert "columns" in result
        assert len(result["rows"]) <= MAX_SAMPLE_ROWS


# =============================================================================
# read_data_profile Tests
# =============================================================================


class TestReadDataProfile:
    """Tests for the read_data_profile tool."""
    
    def test_read_profile_from_run_dir(self, temp_run_dir: Path):
        """Should read data profile from run directory."""
        tc = _make_tool_context({"run_dir": str(temp_run_dir)})
        
        result = read_data_profile(tool_context=tc)
        
        assert "error" not in result
        assert "content" in result
        assert "Data Profile" in result["content"]
    
    def test_read_profile_from_explicit_path(self, temp_run_dir: Path):
        """Should use data_profile_path from state if provided."""
        profile_path = temp_run_dir / "data_analysis" / "data_profile.md"
        tc = _make_tool_context({"data_profile_path": str(profile_path)})
        
        result = read_data_profile(tool_context=tc)
        
        assert "error" not in result
        assert "content" in result
    
    def test_read_profile_missing_state(self):
        """Should return error if no run_dir or path in state."""
        tc = _make_tool_context({})
        
        result = read_data_profile(tool_context=tc)
        
        assert "error" in result
    
    def test_read_profile_no_context(self):
        """Should return error if no tool context provided."""
        result = read_data_profile(tool_context=None)
        
        assert "error" in result


# =============================================================================
# read_dashboard_concept Tests
# =============================================================================


class TestReadDashboardConcept:
    """Tests for the read_dashboard_concept tool."""
    
    def test_read_concept_from_run_dir(self, temp_run_dir: Path):
        """Should read dashboard concept from run directory."""
        tc = _make_tool_context({"run_dir": str(temp_run_dir)})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" not in result
        assert "concept" in result
        assert result["concept"]["goal"] == "Sales Dashboard"
        assert len(result["concept"]["kpis"]) == 1
    
    def test_read_concept_from_explicit_path(self, temp_run_dir: Path):
        """Should use dashboard_spec_path from state if provided."""
        concept_path = temp_run_dir / "planner" / "dashboard_concept.json"
        tc = _make_tool_context({"dashboard_spec_path": str(concept_path)})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" not in result
        assert "concept" in result
    
    def test_read_concept_invalid_json(self, tmp_path: Path):
        """Should return error for invalid JSON."""
        planner_dir = tmp_path / "planner"
        planner_dir.mkdir()
        bad_json = planner_dir / "dashboard_concept.json"
        bad_json.write_text("{invalid json}", encoding="utf-8")
        
        tc = _make_tool_context({"run_dir": str(tmp_path)})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" in result
        assert "Invalid JSON" in result["error"]
    
    def test_read_concept_missing_state(self):
        """Should return error if no run_dir or path in state."""
        tc = _make_tool_context({})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" in result


# =============================================================================
# copy_data_to_project Tests (Callback Helper)
# =============================================================================


class TestCopyDataToProject:
    """Tests for the copy_data_to_project callback helper function."""
    
    def test_copy_creates_destination_dir(self, temp_run_dir: Path, tmp_path: Path):
        """Should create destination directory if it doesn't exist."""
        # Mock SAMPLE_DASHBOARD_ROOT to use temp path
        dest_root = tmp_path / "sample-dashboard"
        
        with patch("src.tools.backend.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
            state = {"run_dir": str(temp_run_dir)}
            
            result = copy_data_to_project(state=state)
            
            assert "error" not in result
            assert (dest_root / "data").exists()
    
    def test_copy_transfers_files(self, temp_run_dir: Path, tmp_path: Path):
        """Should copy all files from cleaned directory."""
        dest_root = tmp_path / "sample-dashboard"
        
        with patch("src.tools.backend.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
            state = {"run_dir": str(temp_run_dir)}
            
            result = copy_data_to_project(state=state)
            
            assert "error" not in result
            assert result["total_files"] == 1
            assert (dest_root / "data" / "cleaned.csv").exists()
    
    def test_copy_returns_file_summary(self, temp_run_dir: Path, tmp_path: Path):
        """Should return summary of copied files."""
        dest_root = tmp_path / "sample-dashboard"
        
        with patch("src.tools.backend.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
            state = {"run_dir": str(temp_run_dir)}
            
            result = copy_data_to_project(state=state)
            
            assert "copied_files" in result
            assert len(result["copied_files"]) == 1
            assert "source" in result["copied_files"][0]
            assert "destination" in result["copied_files"][0]
            assert "filename" in result["copied_files"][0]
    
    def test_copy_empty_source_returns_warning(self, tmp_path: Path):
        """Should return warning if source directory is empty."""
        # Create empty cleaned directory
        run_dir = tmp_path / "run"
        cleaned_dir = run_dir / "data_analysis" / "cleaned"
        cleaned_dir.mkdir(parents=True)
        
        dest_root = tmp_path / "sample-dashboard"
        
        with patch("src.tools.backend.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
            state = {"run_dir": str(run_dir)}
            
            result = copy_data_to_project(state=state)
            
            assert "warning" in result
            assert result["total_files"] == 0
    
    def test_copy_missing_state(self):
        """Should return error if no run_dir or path in state."""
        state = {}
        
        result = copy_data_to_project(state=state)
        
        assert "error" in result
    
    def test_copy_nonexistent_source(self, tmp_path: Path):
        """Should return error if source directory doesn't exist."""
        state = {"run_dir": str(tmp_path / "nonexistent")}
        
        result = copy_data_to_project(state=state)
        
        assert "error" in result


# =============================================================================
# Creation Tools Tests
# =============================================================================


from src.tools.backend.creation import (
    create_api,
    create_model,
    add_utility,
    _parse_imports,
    _merge_imports,
    _format_imports,
    _validate_typescript_exports,
)


def _patch_allowed_paths_for_temp(dest_root: Path) -> list[str]:
    """Generate ALLOWED_PATHS list for a temporary test directory."""
    return [
        str(dest_root / "src" / "app" / "api"),
        str(dest_root / "src" / "models"),
        str(dest_root / "src" / "lib"),
        str(dest_root / "data"),
    ]


class TestCreateApi:
    """Tests for the create_api tool."""
    
    def test_create_api_basic_route(self, tmp_path: Path):
        """Should create a new API route file."""
        dest_root = tmp_path / "sample-dashboard"
        api_dir = dest_root / "src" / "app" / "api"
        api_dir.mkdir(parents=True)
        
        content = '''import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({ message: "Hello" });
}
'''
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_api(route_path="hello/route.ts", content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    assert "hello/route.ts" in result["relative_path"]
                    assert (api_dir / "hello" / "route.ts").exists()
                    assert (api_dir / "hello" / "route.ts").read_text() == content
    
    def test_create_api_nested_route(self, tmp_path: Path):
        """Should create nested route directories."""
        dest_root = tmp_path / "sample-dashboard"
        api_dir = dest_root / "src" / "app" / "api"
        api_dir.mkdir(parents=True)
        
        content = 'export async function GET() { return Response.json({}); }'
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_api(
                        route_path="products/[id]/reviews/route.ts",
                        content=content,
                        tool_context=tc,
                    )
                    
                    assert result["success"] is True
                    assert (api_dir / "products" / "[id]" / "reviews" / "route.ts").exists()
    
    def test_create_api_fails_if_exists(self, tmp_path: Path):
        """Should fail if the file already exists."""
        dest_root = tmp_path / "sample-dashboard"
        api_dir = dest_root / "src" / "app" / "api" / "existing"
        api_dir.mkdir(parents=True)
        
        existing_file = api_dir / "route.ts"
        existing_file.write_text("// existing content")
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_api(
                        route_path="existing/route.ts",
                        content="// new content",
                        tool_context=tc,
                    )
                    
                    assert result["success"] is False
                    assert "already exists" in result["error"]
                    assert "patch_file" in result["error"]
    
    def test_create_api_requires_ts_extension(self, tmp_path: Path):
        """Should require .ts or .tsx extension."""
        dest_root = tmp_path / "sample-dashboard"
        (dest_root / "src" / "app" / "api").mkdir(parents=True)
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_api(
                        route_path="test/route.js",
                        content="// content",
                        tool_context=tc,
                    )
                    
                    assert result["success"] is False
                    assert ".ts" in result["error"]


class TestCreateModel:
    """Tests for the create_model tool."""
    
    def test_create_model_with_interface(self, tmp_path: Path):
        """Should create model file with interface export."""
        dest_root = tmp_path / "sample-dashboard"
        models_dir = dest_root / "src" / "models"
        models_dir.mkdir(parents=True)
        
        content = '''export interface Product {
  id: string;
  name: string;
  price: number;
}
'''
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_model(name="product", content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    assert "product.ts" in result["relative_path"]
                    assert (models_dir / "product.ts").exists()
    
    def test_create_model_with_type_export(self, tmp_path: Path):
        """Should accept type exports."""
        dest_root = tmp_path / "sample-dashboard"
        (dest_root / "src" / "models").mkdir(parents=True)
        
        content = 'export type Status = "active" | "inactive";'
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_model(name="status", content=content, tool_context=tc)
                    
                    assert result["success"] is True
    
    def test_create_model_strips_ts_extension(self, tmp_path: Path):
        """Should strip .ts extension from name if provided."""
        dest_root = tmp_path / "sample-dashboard"
        (dest_root / "src" / "models").mkdir(parents=True)
        
        content = 'export const VERSION = "1.0.0";'
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_model(name="config.ts", content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    assert "config.ts" in result["relative_path"]
                    # Should not create config.ts.ts
                    assert not (dest_root / "src" / "models" / "config.ts.ts").exists()
    
    def test_create_model_fails_without_export(self, tmp_path: Path):
        """Should fail if content doesn't export anything."""
        dest_root = tmp_path / "sample-dashboard"
        (dest_root / "src" / "models").mkdir(parents=True)
        
        content = '''interface InternalOnly {
  id: string;
}
const private_value = 42;
'''
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_model(name="internal", content=content, tool_context=tc)
                    
                    assert result["success"] is False
                    assert "export" in result["error"].lower()
    
    def test_create_model_fails_if_exists(self, tmp_path: Path):
        """Should fail if model file already exists."""
        dest_root = tmp_path / "sample-dashboard"
        models_dir = dest_root / "src" / "models"
        models_dir.mkdir(parents=True)
        
        (models_dir / "existing.ts").write_text("export interface Existing {}")
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = create_model(
                        name="existing",
                        content="export interface New {}",
                        tool_context=tc,
                    )
                    
                    assert result["success"] is False
                    assert "already exists" in result["error"]


class TestAddUtility:
    """Tests for the add_utility tool."""
    
    def test_add_utility_to_empty_file(self, tmp_path: Path):
        """Should create file with imports and content if it doesn't exist."""
        dest_root = tmp_path / "sample-dashboard"
        lib_dir = dest_root / "src" / "lib"
        lib_dir.mkdir(parents=True)
        
        imports = ['import { parse } from "papaparse";']
        content = '''export function parseCSV(data: string) {
  return parse(data);
}'''
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = add_utility(imports=imports, content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    
                    file_content = (lib_dir / "data-utils.ts").read_text()
                    assert 'import { parse } from "papaparse"' in file_content
                    assert "parseCSV" in file_content
    
    def test_add_utility_merges_imports(self, tmp_path: Path):
        """Should merge imports with existing imports."""
        dest_root = tmp_path / "sample-dashboard"
        lib_dir = dest_root / "src" / "lib"
        lib_dir.mkdir(parents=True)
        
        # Existing file with some imports
        existing = '''import { existingFunc } from "existing-lib";

export function existingUtility() {
  return existingFunc();
}
'''
        (lib_dir / "data-utils.ts").write_text(existing)
        
        imports = ['import { newFunc } from "new-lib";']
        content = '''export function newUtility() {
  return newFunc();
}'''
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = add_utility(imports=imports, content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    
                    file_content = (lib_dir / "data-utils.ts").read_text()
                    # Both imports should be present
                    assert "existing-lib" in file_content
                    assert "new-lib" in file_content
                    # Both functions should be present
                    assert "existingUtility" in file_content
                    assert "newUtility" in file_content
    
    def test_add_utility_deduplicates_imports(self, tmp_path: Path):
        """Should deduplicate imports from same module."""
        dest_root = tmp_path / "sample-dashboard"
        lib_dir = dest_root / "src" / "lib"
        lib_dir.mkdir(parents=True)
        
        existing = '''import { funcA } from "shared-lib";

export function utilA() {}
'''
        (lib_dir / "data-utils.ts").write_text(existing)
        
        # New import from same module
        imports = ['import { funcB } from "shared-lib";']
        content = 'export function utilB() {}'
        allowed_paths = _patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = _make_tool_context({})
                    
                    result = add_utility(imports=imports, content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    
                    file_content = (lib_dir / "data-utils.ts").read_text()
                    # Should have merged import: { funcA, funcB }
                    assert "funcA" in file_content
                    assert "funcB" in file_content
                    # Should only have one import statement from shared-lib
                    assert file_content.count("shared-lib") == 1


class TestImportParsing:
    """Tests for import parsing helper functions."""
    
    def test_parse_named_imports(self):
        """Should parse named imports correctly."""
        content = '''import { a, b, c } from "module";

export function test() {}
'''
        imports, remaining = _parse_imports(content)
        
        assert "module" in imports
        assert {"a", "b", "c"} == imports["module"]
    
    def test_parse_default_import(self):
        """Should parse default imports."""
        content = '''import React from "react";

export function Component() {}
'''
        imports, remaining = _parse_imports(content)
        
        assert "react" in imports
        assert "default:React" in imports["react"]
    
    def test_parse_star_import(self):
        """Should parse star imports."""
        content = '''import * as utils from "./utils";

export const x = 1;
'''
        imports, remaining = _parse_imports(content)
        
        assert "./utils" in imports
        assert "* as utils" in imports["./utils"]
    
    def test_merge_imports_combines_same_module(self):
        """Should merge imports from same module."""
        existing = {"module": {"a", "b"}}
        new = {"module": {"c", "d"}}
        
        merged = _merge_imports(existing, new)
        
        assert merged["module"] == {"a", "b", "c", "d"}
    
    def test_merge_imports_adds_new_modules(self):
        """Should add imports from new modules."""
        existing = {"module-a": {"a"}}
        new = {"module-b": {"b"}}
        
        merged = _merge_imports(existing, new)
        
        assert "module-a" in merged
        assert "module-b" in merged
    
    def test_format_imports_named(self):
        """Should format named imports correctly."""
        imports = {"module": {"a", "b"}}
        
        formatted = _format_imports(imports)
        
        assert 'import { a, b } from "module";' in formatted
    
    def test_validate_exports_interface(self):
        """Should validate interface exports."""
        content = "export interface Test { id: string; }"
        
        is_valid, error = _validate_typescript_exports(content)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_exports_type(self):
        """Should validate type exports."""
        content = 'export type Status = "a" | "b";'
        
        is_valid, error = _validate_typescript_exports(content)
        
        assert is_valid is True
    
    def test_validate_exports_const(self):
        """Should validate const exports."""
        content = "export const VALUE = 42;"
        
        is_valid, error = _validate_typescript_exports(content)
        
        assert is_valid is True
    
    def test_validate_exports_fails_no_export(self):
        """Should fail if no exports."""
        content = "const internal = 42;"
        
        is_valid, error = _validate_typescript_exports(content)
        
        assert is_valid is False
        assert "export" in error.lower()

