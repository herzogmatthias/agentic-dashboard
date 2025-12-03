"""
Tests for the backend manifest writing tool.

Tests the write_backend_manifest tool which persists the BackendManifest
to the run directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.models.backend_manifest import (
    BackendManifest,
    DataSourceInfo,
    ModelInfo,
    QueryParam,
    RouteInfo,
    ValidationResult,
)
from src.tools.backend.manifest import (
    write_backend_manifest,
    write_backend_manifest_tool,
    DEV_OUTPUT_DIR,
    MANIFEST_FILENAME,
    _ensure_created_at,
    _validate_manifest,
)


# ============================================================================
# Test Fixtures
# ============================================================================


def _tc(state: dict):
    """Create a mock tool context with state."""
    return SimpleNamespace(state=state)


def _valid_manifest_dict(run_id: str = "run_test_123") -> dict:
    """Return a valid manifest dictionary for testing dict helpers."""
    return {
        "run_id": run_id,
        "data_source": {
            "original_path": f"runs/{run_id}/cleaned/data.csv",
            "project_path": "data/cleaned.csv",
            "row_count": 1000,
            "columns": ["id", "name", "value"]
        },
        "models": [
            {
                "name": "TestModel",
                "file_path": "models/TestModel.ts",
                "description": "Test model for unit tests",
                "exports": ["TestRecord", "TestResponse"]
            }
        ],
        "routes": [
            {
                "path": "/api/test",
                "file_path": "app/api/test/route.ts",
                "method": "GET",
                "description": "Test endpoint",
                "serves_visual_ids": ["kpi_1"],
                "query_params": [
                    {
                        "name": "filter",
                        "type": "string",
                        "required": False,
                        "description": "Filter parameter"
                    }
                ],
                "response_schema": "TestResponse"
            }
        ],
        "validation": {
            "lint_passed": True,
            "build_passed": True,
            "errors": None
        },
        "notes": ["Test note"]
    }


def _valid_manifest(
    run_id: str = "run_test_123",
    lint_passed: bool = True,
    build_passed: bool = True,
    errors: list[str] | None = None,
) -> BackendManifest:
    """Return a valid BackendManifest instance for testing."""
    return BackendManifest(
        run_id=run_id,
        # Don't pass created_at - let default_factory generate it
        data_source=DataSourceInfo(
            original_path=f"runs/{run_id}/cleaned/data.csv",
            project_path="data/cleaned.csv",
            row_count=1000,
            columns=["id", "name", "value"]
        ),
        models=[
            ModelInfo(
                name="TestModel",
                file_path="models/TestModel.ts",
                description="Test model for unit tests",
                exports=["TestRecord", "TestResponse"]
            )
        ],
        routes=[
            RouteInfo(
                path="/api/test",
                file_path="app/api/test/route.ts",
                method="GET",
                description="Test endpoint",
                serves_visual_ids=["kpi_1"],
                query_params=[
                    QueryParam(
                        name="filter",
                        type="string",
                        required=False,
                        description="Filter parameter"
                    )
                ],
                response_schema="TestResponse"
            )
        ],
        validation=ValidationResult(
            lint_passed=lint_passed,
            build_passed=build_passed,
            errors=errors
        ),
        notes=["Test note"]
    )


# ============================================================================
# Helper Function Tests (for dict-based helpers)
# ============================================================================


class TestEnsureCreatedAt:
    """Tests for _ensure_created_at dict helper."""
    
    def test_adds_created_at_when_missing(self):
        """Test that created_at is added when not present."""
        manifest = {"run_id": "test"}
        result = _ensure_created_at(manifest)
        
        assert "created_at" in result
        assert result["created_at"] is not None
    
    def test_adds_created_at_when_empty(self):
        """Test that created_at is added when empty string."""
        manifest = {"run_id": "test", "created_at": ""}
        result = _ensure_created_at(manifest)
        
        assert result["created_at"] != ""
    
    def test_preserves_existing_created_at(self):
        """Test that existing created_at is preserved."""
        manifest = {"run_id": "test", "created_at": "2025-01-01T00:00:00"}
        result = _ensure_created_at(manifest)
        
        assert result["created_at"] == "2025-01-01T00:00:00"


class TestValidateManifest:
    """Tests for _validate_manifest dict helper."""
    
    def test_validates_valid_manifest(self):
        """Test that valid manifest passes validation."""
        manifest = _valid_manifest_dict()
        result = _validate_manifest(manifest)
        
        assert result.run_id == "run_test_123"
        assert result.data_source.row_count == 1000
    
    def test_raises_on_missing_required_fields(self):
        """Test that missing required fields raise ValueError."""
        manifest = {"run_id": "test"}  # Missing data_source, validation
        
        with pytest.raises(ValueError, match="validation failed"):
            _validate_manifest(manifest)
    
    def test_raises_on_invalid_data_source(self):
        """Test that invalid data_source raises ValueError."""
        manifest = _valid_manifest_dict()
        manifest["data_source"]["row_count"] = -1  # Invalid: must be >= 0
        
        with pytest.raises(ValueError, match="validation failed"):
            _validate_manifest(manifest)


# ============================================================================
# Write Manifest Tool Tests
# ============================================================================


class TestWriteBackendManifest:
    """Tests for write_backend_manifest tool."""
    
    def test_writes_manifest_to_dev_directory(self, tmp_path):
        """Test that manifest is written to {run_dir}/dev/backend_manifest.json."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest()
        
        result = write_backend_manifest(manifest, _tc(state))
        
        assert result["success"] is True
        manifest_path = tmp_path / DEV_OUTPUT_DIR / MANIFEST_FILENAME
        assert manifest_path.exists()
    
    def test_returns_path_in_result(self, tmp_path):
        """Test that result includes the manifest path."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest()
        
        result = write_backend_manifest(manifest, _tc(state))
        
        assert result["path"] is not None
        assert MANIFEST_FILENAME in result["path"]
    
    def test_creates_dev_directory_if_missing(self, tmp_path):
        """Test that dev directory is created if it doesn't exist."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest()
        
        # Ensure dev directory doesn't exist
        dev_dir = tmp_path / DEV_OUTPUT_DIR
        assert not dev_dir.exists()
        
        result = write_backend_manifest(manifest, _tc(state))
        
        assert result["success"] is True
        assert dev_dir.exists()
    
    def test_auto_populates_created_at(self, tmp_path):
        """Test that created_at is auto-populated if not provided."""
        state = {"run_dir": str(tmp_path)}
        # Don't set created_at - let the default factory handle it
        manifest = _valid_manifest()
        
        result = write_backend_manifest(manifest, _tc(state))
        
        assert result["success"] is True
        
        # Read back and verify created_at exists
        manifest_path = tmp_path / DEV_OUTPUT_DIR / MANIFEST_FILENAME
        written = json.loads(manifest_path.read_text())
        assert "created_at" in written
        assert written["created_at"] is not None
    
    def test_updates_state_with_manifest_path(self, tmp_path):
        """Test that backend_manifest_path is set in state."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest()
        
        write_backend_manifest(manifest, _tc(state))
        
        assert "backend_manifest_path" in state
        assert MANIFEST_FILENAME in state["backend_manifest_path"]
    
    def test_sets_backend_status_success(self, tmp_path):
        """Test that backend_status is 'success' when validation passes."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest(lint_passed=True, build_passed=True)
        
        write_backend_manifest(manifest, _tc(state))
        
        assert state["backend_status"] == "success"
    
    def test_sets_backend_status_partial_lint_only(self, tmp_path):
        """Test that backend_status is 'partial' when only lint passes."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest(lint_passed=True, build_passed=False, errors=["Build failed"])
        
        write_backend_manifest(manifest, _tc(state))
        
        assert state["backend_status"] == "partial"
    
    def test_sets_backend_status_partial_build_only(self, tmp_path):
        """Test that backend_status is 'partial' when only build passes."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest(lint_passed=False, build_passed=True, errors=["Lint failed"])
        
        write_backend_manifest(manifest, _tc(state))
        
        assert state["backend_status"] == "partial"
    
    def test_sets_backend_status_failed(self, tmp_path):
        """Test that backend_status is 'failed' when both fail."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest(lint_passed=False, build_passed=False, errors=["Both failed"])
        
        write_backend_manifest(manifest, _tc(state))
        
        assert state["backend_status"] == "failed"
    
    def test_fails_when_run_dir_missing(self):
        """Test that write fails when run_dir is not in state."""
        state = {}
        manifest = _valid_manifest()
        
        result = write_backend_manifest(manifest, _tc(state))
        
        assert result["success"] is False
    
    def test_fails_when_context_is_none(self):
        """Test that write fails when tool_context is None."""
        manifest = _valid_manifest()
        
        result = write_backend_manifest(manifest, None)
        
        assert result["success"] is False
    
    def test_writes_valid_json(self, tmp_path):
        """Test that written file is valid JSON."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest()
        
        write_backend_manifest(manifest, _tc(state))
        
        manifest_path = tmp_path / DEV_OUTPUT_DIR / MANIFEST_FILENAME
        content = manifest_path.read_text()
        parsed = json.loads(content)  # Should not raise
        
        assert parsed["run_id"] == "run_test_123"
    
    def test_manifest_contains_all_fields(self, tmp_path):
        """Test that all fields are written to manifest."""
        state = {"run_dir": str(tmp_path)}
        manifest = _valid_manifest()
        
        write_backend_manifest(manifest, _tc(state))
        
        manifest_path = tmp_path / DEV_OUTPUT_DIR / MANIFEST_FILENAME
        written = json.loads(manifest_path.read_text())
        
        assert "created_at" in written
        assert "run_id" in written
        assert "data_source" in written
        assert "models" in written
        assert "routes" in written
        assert "validation" in written
        assert "notes" in written


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""
    
    def test_dev_output_dir_is_dev(self):
        """Test that DEV_OUTPUT_DIR is 'dev'."""
        assert DEV_OUTPUT_DIR == "dev"
    
    def test_manifest_filename_is_json(self):
        """Test that MANIFEST_FILENAME ends with .json."""
        assert MANIFEST_FILENAME.endswith(".json")
        assert MANIFEST_FILENAME == "backend_manifest.json"


# ============================================================================
# Module Export Tests
# ============================================================================


class TestModuleExports:
    """Tests for module exports via __init__.py."""
    
    def test_exports_from_init(self):
        """Test that key items are exported from __init__.py."""
        from src.tools.backend import (
            write_backend_manifest,
            write_backend_manifest_tool,
            DEV_OUTPUT_DIR,
            MANIFEST_FILENAME,
        )
        
        assert write_backend_manifest is not None
        assert write_backend_manifest_tool is not None
        assert DEV_OUTPUT_DIR == "dev"
        assert MANIFEST_FILENAME == "backend_manifest.json"
    
    def test_tool_is_function_tool(self):
        """Test that write_backend_manifest_tool is a FunctionTool."""
        from google.adk.tools import FunctionTool
        from src.tools.backend import write_backend_manifest_tool
        
        assert isinstance(write_backend_manifest_tool, FunctionTool)
