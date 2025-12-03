"""
Tests for data access tools (get_sample_rows, read_data_profile, read_dashboard_concept, copy_data_to_project).
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.tools.conftest import make_tool_context
from src.tools.backend.data_access import (
    MAX_SAMPLE_ROWS,
    get_sample_rows,
    read_data_profile,
    read_dashboard_concept,
    copy_data_to_project,
)


class TestGetSampleRows:
    """Tests for the get_sample_rows tool."""
    
    def test_max_sample_rows_constant(self):
        """MAX_SAMPLE_ROWS should be 1 to avoid token bloat."""
        assert MAX_SAMPLE_ROWS == 1
    
    def test_read_csv_default_rows(self, temp_csv: Path):
        """Should read 1 row by default (MAX_SAMPLE_ROWS)."""
        # Patch _validate_path to allow temp directory
        with patch("src.tools.backend.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), tool_context=None)
            
            assert "error" not in result
            assert result["total_rows_sampled"] == 1
            assert len(result["rows"]) == 1
    
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


class TestReadDataProfile:
    """Tests for the read_data_profile tool."""
    
    def test_read_profile_from_run_dir(self, temp_run_dir: Path):
        """Should read data profile from run directory."""
        tc = make_tool_context({"run_dir": str(temp_run_dir)})
        
        result = read_data_profile(tool_context=tc)
        
        assert "error" not in result
        assert "content" in result
        assert "Data Profile" in result["content"]
    
    def test_read_profile_from_explicit_path(self, temp_run_dir: Path):
        """Should use data_profile_path from state if provided."""
        profile_path = temp_run_dir / "data_profile.md"
        tc = make_tool_context({"data_profile_path": str(profile_path)})
        
        result = read_data_profile(tool_context=tc)
        
        assert "error" not in result
        assert "content" in result
    
    def test_read_profile_missing_state(self):
        """Should return error if no run_dir or path in state."""
        tc = make_tool_context({})
        
        result = read_data_profile(tool_context=tc)
        
        assert "error" in result
    
    def test_read_profile_no_context(self):
        """Should return error if no tool context provided."""
        result = read_data_profile(tool_context=None)
        
        assert "error" in result


class TestReadDashboardConcept:
    """Tests for the read_dashboard_concept tool."""
    
    def test_read_concept_from_run_dir(self, temp_run_dir: Path):
        """Should read dashboard concept from run directory as minified JSON string."""
        tc = make_tool_context({"run_dir": str(temp_run_dir)})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" not in result
        assert "concept" in result
        # concept is now a minified JSON string
        import json
        concept = json.loads(result["concept"])
        assert concept["goal"] == "Sales Dashboard"
        assert len(concept["kpis"]) == 1
    
    def test_read_concept_from_explicit_path(self, temp_run_dir: Path):
        """Should use dashboard_spec_path from state if provided."""
        concept_path = temp_run_dir / "planner" / "dashboard_concept.json"
        tc = make_tool_context({"dashboard_spec_path": str(concept_path)})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" not in result
        assert "concept" in result
        # concept is a minified JSON string
        assert isinstance(result["concept"], str)
    
    def test_read_concept_invalid_json(self, tmp_path: Path):
        """Should return error for invalid JSON."""
        planner_dir = tmp_path / "planner"
        planner_dir.mkdir()
        bad_json = planner_dir / "dashboard_concept.json"
        bad_json.write_text("{invalid json}", encoding="utf-8")
        
        tc = make_tool_context({"run_dir": str(tmp_path)})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" in result
        assert "Invalid JSON" in result["error"]
    
    def test_read_concept_missing_state(self):
        """Should return error if no run_dir or path in state."""
        tc = make_tool_context({})
        
        result = read_dashboard_concept(tool_context=tc)
        
        assert "error" in result


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
        # Create empty cleaned directory (at root level, not under data_analysis)
        run_dir = tmp_path / "run"
        cleaned_dir = run_dir / "cleaned"
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
