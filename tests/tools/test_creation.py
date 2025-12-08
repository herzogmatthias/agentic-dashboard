"""
Tests for file creation tools (create_api, create_model).
"""
from pathlib import Path
from unittest.mock import patch

from tests.tools.conftest import make_tool_context, patch_allowed_paths_for_temp
from src.tools.backend_dev.creation import (
    create_api,
    create_model,
    _validate_typescript_exports,
)


class TestCreateApi:
    """Tests for the create_api tool."""
    
    def test_create_api_basic_route(self, tmp_path: Path):
        """Should create a new API route file using Next.js route notation."""
        dest_root = tmp_path / "sample-dashboard"
        api_dir = dest_root / "src" / "app" / "api"
        api_dir.mkdir(parents=True)
        
        content = '''import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({ message: "Hello" });
}
'''
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    # Use Next.js route notation (just the path, route.ts is auto-appended)
                    result = create_api(route_path="hello", content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    assert result["relative_path"] == "src/app/api/hello/route.ts"
                    assert result["endpoint"] == "/api/hello"
                    assert (api_dir / "hello" / "route.ts").exists()
                    assert (api_dir / "hello" / "route.ts").read_text() == content
    
    def test_create_api_nested_route(self, tmp_path: Path):
        """Should create nested route directories using Next.js dynamic route notation."""
        dest_root = tmp_path / "sample-dashboard"
        api_dir = dest_root / "src" / "app" / "api"
        api_dir.mkdir(parents=True)
        
        content = 'export async function GET() { return Response.json({}); }'
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    # Use Next.js route notation (e.g., products/[id]/reviews)
                    result = create_api(
                        route_path="products/[id]/reviews",
                        content=content,
                        tool_context=tc,
                    )
                    
                    assert result["success"] is True
                    assert result["relative_path"] == "src/app/api/products/[id]/reviews/route.ts"
                    assert result["endpoint"] == "/api/products/[id]/reviews"
                    assert (api_dir / "products" / "[id]" / "reviews" / "route.ts").exists()
    
    def test_create_api_fails_if_exists(self, tmp_path: Path):
        """Should fail if the file already exists and suggest MCP edit_file."""
        dest_root = tmp_path / "sample-dashboard"
        api_dir = dest_root / "src" / "app" / "api" / "existing"
        api_dir.mkdir(parents=True)
        
        existing_file = api_dir / "route.ts"
        existing_file.write_text("// existing content")
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    # Use Next.js notation (just "existing", not "existing/route.ts")
                    result = create_api(
                        route_path="existing",
                        content="// new content",
                        tool_context=tc,
                    )
                    
                    assert result["success"] is False
                    assert "already exists" in result["error"]
                    assert "MCP filesystem edit_file" in result["error"]
    
    def test_create_api_strips_route_ts_suffix(self, tmp_path: Path):
        """Should handle backward compatibility when route.ts suffix is provided."""
        dest_root = tmp_path / "sample-dashboard"
        api_dir = dest_root / "src" / "app" / "api"
        api_dir.mkdir(parents=True)
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        content = 'export async function GET() { return Response.json({}); }'
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    # Even if route.ts is provided, it should be stripped and re-added
                    result = create_api(
                        route_path="test/route.ts",
                        content=content,
                        tool_context=tc,
                    )
                    
                    assert result["success"] is True
                    assert result["relative_path"] == "src/app/api/test/route.ts"
                    assert result["endpoint"] == "/api/test"
                    # Should NOT create test/route.ts/route.ts
                    assert (api_dir / "test" / "route.ts").exists()
                    assert not (api_dir / "test" / "route.ts" / "route.ts").exists()


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
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    result = create_model(name="product", content=content, tool_context=tc)
                    
                    assert result["success"] is True
                    assert "product.ts" in result["relative_path"]
                    assert (models_dir / "product.ts").exists()
    
    def test_create_model_with_type_export(self, tmp_path: Path):
        """Should accept type exports."""
        dest_root = tmp_path / "sample-dashboard"
        (dest_root / "src" / "models").mkdir(parents=True)
        
        content = 'export type Status = "active" | "inactive";'
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    result = create_model(name="status", content=content, tool_context=tc)
                    
                    assert result["success"] is True
    
    def test_create_model_strips_ts_extension(self, tmp_path: Path):
        """Should strip .ts extension from name if provided."""
        dest_root = tmp_path / "sample-dashboard"
        (dest_root / "src" / "models").mkdir(parents=True)
        
        content = 'export const VERSION = "1.0.0";'
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
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
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    result = create_model(name="internal", content=content, tool_context=tc)
                    
                    assert result["success"] is False
                    assert "export" in result["error"].lower()
    
    def test_create_model_fails_if_exists(self, tmp_path: Path):
        """Should fail if model file already exists."""
        dest_root = tmp_path / "sample-dashboard"
        models_dir = dest_root / "src" / "models"
        models_dir.mkdir(parents=True)
        
        (models_dir / "existing.ts").write_text("export interface Existing {}")
        allowed_paths = patch_allowed_paths_for_temp(dest_root)
        
        with patch("src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT", dest_root):
            with patch("src.tools.backend_dev.filesystem.SAMPLE_DASHBOARD_ROOT", dest_root):
                with patch("src.tools.backend_dev.filesystem.ALLOWED_PATHS", allowed_paths):
                    tc = make_tool_context({})
                    
                    result = create_model(
                        name="existing",
                        content="export interface New {}",
                        tool_context=tc,
                    )
                    
                    assert result["success"] is False
                    assert "already exists" in result["error"]


class TestValidateTypescriptExports:
    """Tests for the _validate_typescript_exports helper function."""
    
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
