"""
Tests for MCP Filesystem Server integration.

Tests the create_filesystem_toolset() factory function for creating
McpToolset instances that connect to the MCP filesystem server.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.backend.filesystem_mcp import (
    FILESYSTEM_MCP_PACKAGE,
    SAMPLE_DASHBOARD_ROOT,
    ALLOWED_DIRECTORIES,
    EXPOSED_TOOLS,
    CONNECTION_TIMEOUT,
    create_filesystem_toolset,
    create_filesystem_toolset_with_run_dir,
)


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateFilesystemToolset:
    """Tests for create_filesystem_toolset()."""
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_correct_filter(self, mock_toolset_class):
        """Test that create_filesystem_toolset creates toolset with correct filter."""
        create_filesystem_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        
        assert call_kwargs["tool_filter"] == EXPOSED_TOOLS
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_npx_command(self, mock_toolset_class):
        """Test that create_filesystem_toolset uses npx command."""
        create_filesystem_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        
        # Check that the server_params specify npx
        assert connection_params.server_params.command == "npx"
        assert "-y" in connection_params.server_params.args
        assert FILESYSTEM_MCP_PACKAGE in connection_params.server_params.args
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_allowed_paths(self, mock_toolset_class):
        """Test that create_filesystem_toolset includes allowed directories."""
        create_filesystem_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        # Check that allowed directories are in args
        for allowed_dir in ALLOWED_DIRECTORIES:
            assert str(allowed_dir) in args
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_additional_paths(self, mock_toolset_class):
        """Test that additional_paths are added to allowed directories."""
        extra_path = Path("/extra/path")
        create_filesystem_toolset(additional_paths=[extra_path])
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        assert str(extra_path) in args
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_custom_filter(self, mock_toolset_class):
        """Test that custom tool_filter overrides default."""
        custom_filter = ["read_file", "list_directory"]
        create_filesystem_toolset(tool_filter=custom_filter)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        
        assert call_kwargs["tool_filter"] == custom_filter
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_timeout(self, mock_toolset_class):
        """Test that create_filesystem_toolset sets connection timeout."""
        create_filesystem_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        
        assert connection_params.timeout == CONNECTION_TIMEOUT
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_returns_toolset_instance(self, mock_toolset_class):
        """Test that create_filesystem_toolset returns the McpToolset instance."""
        mock_toolset = MagicMock()
        mock_toolset_class.return_value = mock_toolset
        
        result = create_filesystem_toolset()
        
        assert result is mock_toolset


class TestCreateFilesystemToolsetWithRunDir:
    """Tests for create_filesystem_toolset_with_run_dir()."""
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_adds_run_dir_to_paths(self, mock_toolset_class):
        """Test that run directory is added to allowed paths."""
        run_dir = "runs/run_123"
        create_filesystem_toolset_with_run_dir(run_dir)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        # The path gets converted via Path(), so check for the resolved path
        assert str(Path(run_dir)) in args
    
    @patch("src.tools.backend.filesystem_mcp.McpToolset")
    def test_accepts_path_object(self, mock_toolset_class):
        """Test that Path objects are accepted for run_dir."""
        run_dir = Path("runs/run_456")
        create_filesystem_toolset_with_run_dir(run_dir)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        assert str(run_dir) in args


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""
    
    def test_exposed_tools_contains_read_file(self):
        """Test that EXPOSED_TOOLS contains read_file."""
        assert "read_file" in EXPOSED_TOOLS
    
    def test_exposed_tools_contains_write_file(self):
        """Test that EXPOSED_TOOLS contains write_file."""
        assert "write_file" in EXPOSED_TOOLS
    
    def test_exposed_tools_contains_edit_file(self):
        """Test that EXPOSED_TOOLS contains edit_file."""
        assert "edit_file" in EXPOSED_TOOLS
    
    def test_exposed_tools_contains_list_directory(self):
        """Test that EXPOSED_TOOLS contains list_directory."""
        assert "list_directory" in EXPOSED_TOOLS
    
    def test_exposed_tools_contains_directory_tree(self):
        """Test that EXPOSED_TOOLS contains directory_tree."""
        assert "directory_tree" in EXPOSED_TOOLS
    
    def test_package_name_correct(self):
        """Test package name is correct."""
        assert FILESYSTEM_MCP_PACKAGE == "@modelcontextprotocol/server-filesystem"
    
    def test_timeout_value_reasonable(self):
        """Test that timeout value is reasonable."""
        assert CONNECTION_TIMEOUT >= 10  # At least 10 seconds
    
    def test_allowed_directories_count(self):
        """Test that we have the expected number of allowed directories."""
        assert len(ALLOWED_DIRECTORIES) == 3  # api, models, lib (no data - read-only)
    
    def test_allowed_directories_under_sample_dashboard(self):
        """Test that all allowed directories are under sample-dashboard."""
        for directory in ALLOWED_DIRECTORIES:
            assert str(directory).startswith(str(SAMPLE_DASHBOARD_ROOT))


# ============================================================================
# Module Export Tests
# ============================================================================


class TestModuleExports:
    """Tests for module exports via __init__.py."""
    
    def test_exports_from_init(self):
        """Test that key items are exported from __init__.py."""
        from src.tools.backend import (
            create_filesystem_toolset,
            create_filesystem_toolset_with_run_dir,
            FILESYSTEM_MCP_PACKAGE,
            SAMPLE_DASHBOARD_ROOT,
            ALLOWED_DIRECTORIES,
            FILESYSTEM_EXPOSED_TOOLS,
            FILESYSTEM_CONNECTION_TIMEOUT,
        )
        
        assert create_filesystem_toolset is not None
        assert create_filesystem_toolset_with_run_dir is not None
        assert FILESYSTEM_MCP_PACKAGE is not None
        assert SAMPLE_DASHBOARD_ROOT is not None
        assert ALLOWED_DIRECTORIES is not None
        assert FILESYSTEM_EXPOSED_TOOLS is not None
        assert FILESYSTEM_CONNECTION_TIMEOUT is not None
