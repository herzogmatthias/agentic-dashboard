"""
Tests for path validation and scoping in backend tools.
"""
from pathlib import Path

from src.tools.backend.filesystem import (
    ALLOWED_PATHS,
    _validate_path,
    _resolve_allowed_paths,
    _get_relative_display_path,
)


class TestPathValidation:
    """Tests for path validation and scoping."""
    
    def test_allowed_paths_configuration(self):
        """Verify ALLOWED_PATHS contains expected paths."""
        assert len(ALLOWED_PATHS) > 0
        # Check for sample-dashboard paths
        assert any("sample-dashboard" in p for p in ALLOWED_PATHS)
    
    def test_resolve_allowed_paths_without_run_dir(self):
        """All static paths should resolve when no run_dir provided."""
        resolved = _resolve_allowed_paths(run_dir=None)
        # All paths are now static (no {run_dir} placeholders)
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
    
    def test_get_relative_display_path(self, sample_dashboard_path: Path):
        """Display paths should be relative to sample-dashboard when possible."""
        full_path = sample_dashboard_path / "src" / "app" / "api" / "route.ts"
        relative = _get_relative_display_path(full_path)
        assert relative == "src\\app\\api\\route.ts" or relative == "src/app/api/route.ts"
