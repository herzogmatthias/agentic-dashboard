"""
Tests for data access tools (get_sample_rows, inspect_json_preview, copy_data_to_project, load_context_for_backend).
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.tools.conftest import make_tool_context
from src.tools.backend_dev.data_access import (
    MAX_SAMPLE_ROWS,
    get_sample_rows,
    copy_data_to_project,
)
from src.tools.shared import (
    TOKEN_THRESHOLD,
    inspect_json_preview,
    _count_tokens,
    _minify_json,
)
from src.agents.utils import load_context_for_backend


class TestGetSampleRows:
    """Tests for the get_sample_rows tool."""
    
    def test_max_sample_rows_constant(self):
        """MAX_SAMPLE_ROWS should be 1 to avoid token bloat."""
        assert MAX_SAMPLE_ROWS == 1
    
    def test_read_csv_default_rows(self, temp_csv: Path):
        """Should read 1 row by default (MAX_SAMPLE_ROWS)."""
        # Patch _validate_path to allow temp directory
        with patch("src.tools.backend_dev.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), tool_context=None)
            
            assert "error" not in result
            assert result["total_rows_sampled"] == 1
            assert len(result["rows"]) == 1
    
    def test_read_csv_respects_max_limit(self, temp_csv: Path):
        """Should cap rows at MAX_SAMPLE_ROWS even if more requested."""
        with patch("src.tools.backend_dev.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), num_rows=100, tool_context=None)
            
            assert "error" not in result
            # Should be capped at MAX_SAMPLE_ROWS
            assert result["total_rows_sampled"] <= MAX_SAMPLE_ROWS
    
    def test_read_csv_returns_columns(self, temp_csv: Path):
        """Should return column names."""
        with patch("src.tools.backend_dev.data_access._validate_path") as mock_validate:
            mock_validate.return_value = (True, temp_csv, "")
            
            result = get_sample_rows(str(temp_csv), tool_context=None)
            
            assert "columns" in result
            assert result["columns"] == ["col_a", "col_b", "col_c"]
    
    def test_read_csv_returns_dicts(self, temp_csv: Path):
        """Rows should be dictionaries with column keys."""
        with patch("src.tools.backend_dev.data_access._validate_path") as mock_validate:
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
        
        with patch("src.tools.backend_dev.data_access._validate_path") as mock_validate:
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
    """Tests for the inspect_json_preview tool and _minify_json helper."""
    
    def test_token_threshold_constant(self):
        """TOKEN_THRESHOLD should be 1000."""
        assert TOKEN_THRESHOLD == 1000
    
    def test_count_tokens_basic(self):
        """Should count tokens approximately."""
        result = _count_tokens("hello world")
        assert result >= 1
    
    def test_minify_json_truncates_depth(self):
        """Should truncate at max depth."""
        deep = {"a": {"b": {"c": {"d": "value"}}}}
        result = _minify_json(deep, max_depth=2)
        assert result["a"]["b"] == "{...}"
    
    def test_minify_json_keeps_first_array_element(self):
        """Should keep only first array element."""
        data = {"items": [1, 2, 3, 4, 5]}
        result = _minify_json(data, max_depth=3)
        assert result["items"] == [1]
    
    def test_inspect_json_full_content(self, temp_run_dir: Path):
        """Should return full content for small files."""
        profile_path = temp_run_dir / "data_profile.json"
        tc = make_tool_context({"run_dir": str(temp_run_dir)})
        
        result = inspect_json_preview(str(profile_path), tool_context=tc)
        
        assert "error" not in result
        assert "content" in result
        assert result["truncated"] is False
    
    def test_inspect_json_truncated_content(self, tmp_path: Path):
        """Should truncate large files."""
        # Create a large JSON file
        large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}
        large_json = tmp_path / "large.json"
        large_json.write_text(json.dumps(large_data), encoding="utf-8")
        
        tc = make_tool_context({"run_dir": str(tmp_path)})
        
        result = inspect_json_preview(str(large_json), tool_context=tc)
        
        assert "error" not in result
        assert "content" in result
        # Large file should be truncated
        assert result["truncated"] is True
    
    def test_inspect_json_not_found(self, tmp_path: Path):
        """Should return error for missing file."""
        tc = make_tool_context({"run_dir": str(tmp_path)})
        
        result = inspect_json_preview("nonexistent.json", tool_context=tc)
        
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_inspect_json_invalid_json(self, tmp_path: Path):
        """Should return error for invalid JSON."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{invalid json}", encoding="utf-8")
        
        tc = make_tool_context({"run_dir": str(tmp_path)})
        
        result = inspect_json_preview(str(bad_json), tool_context=tc)
        
        assert "error" in result
        assert "Invalid JSON" in result["error"]


class TestLoadContextForBackend:
    """Tests for the load_context_for_backend helper function."""
    
    def test_load_context_with_all_files(self, temp_run_dir: Path):
        """Should load all available context files."""
        # Create metrics_summary.json too
        metrics = {"key_metrics": [{"name": "test", "value": 123}]}
        (temp_run_dir / "metrics_summary.json").write_text(json.dumps(metrics), encoding="utf-8")
        
        result = load_context_for_backend(temp_run_dir)
        
        assert "dashboard_concept" in result
        assert "data_profile" in result
        assert "metrics_summary" in result
    
    def test_load_context_missing_files(self, tmp_path: Path):
        """Should handle missing files gracefully."""
        result = load_context_for_backend(tmp_path)
        
        # Should return empty dict, not error
        assert "dashboard_concept" not in result
        assert "data_profile" not in result
    
    def test_load_context_returns_minified_json(self, temp_run_dir: Path):
        """Should return minified JSON strings."""
        result = load_context_for_backend(temp_run_dir)
        
        # Should be valid JSON strings
        if "dashboard_concept" in result:
            parsed = json.loads(result["dashboard_concept"])
            assert "goal" in parsed
        
        if "data_profile" in result:
            parsed = json.loads(result["data_profile"])
            assert "dataset_overview" in parsed


class TestCopyDataToProject:
    """Tests for the copy_data_to_project callback helper function."""
    
    def test_copy_creates_destination_dir(self, temp_run_dir: Path, tmp_path: Path):
        """Should create destination directory if it doesn't exist."""
        # Mock SAMPLE_DASHBOARD_ROOT to use temp path
        dest_root = tmp_path / "sample-dashboard"
        
        with patch("src.tools.backend_dev.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
            state = {"run_dir": str(temp_run_dir)}
            
            result = copy_data_to_project(state=state)
            
            assert "error" not in result
            assert (dest_root / "data").exists()
    
    def test_copy_transfers_files(self, temp_run_dir: Path, tmp_path: Path):
        """Should copy all files from cleaned directory."""
        dest_root = tmp_path / "sample-dashboard"
        
        with patch("src.tools.backend_dev.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
            state = {"run_dir": str(temp_run_dir)}
            
            result = copy_data_to_project(state=state)
            
            assert "error" not in result
            assert result["total_files"] == 1
            assert (dest_root / "data" / "cleaned.csv").exists()
    
    def test_copy_returns_file_summary(self, temp_run_dir: Path, tmp_path: Path):
        """Should return summary of copied files."""
        dest_root = tmp_path / "sample-dashboard"
        
        with patch("src.tools.backend_dev.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
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
        
        with patch("src.tools.backend_dev.data_access.SAMPLE_DASHBOARD_ROOT", dest_root):
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
