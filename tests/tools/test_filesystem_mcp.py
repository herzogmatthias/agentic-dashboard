"""
Tests for MCP Filesystem Server integration.

Tests the create_filesystem_toolset() factory function for creating
McpToolset instances that connect to the MCP filesystem server.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.shared.filesystem_mcp import (
    FILESYSTEM_MCP_PACKAGE,
    CONNECTION_TIMEOUT,
    ALL_FILESYSTEM_TOOLS,
    FULL_ACCESS_TOOLS,
    READ_TOOLS,
    create_filesystem_toolset,
    create_backend_dev_filesystem_toolset,
    create_tester_filesystem_toolset,
)
from src.tools.utils import (
    SAMPLE_DASHBOARD_ROOT,
    BACKEND_DEV_ALLOWED_PATHS,
    TESTER_ALLOWED_PATHS,
)

# Aliases for backward compatibility with tests
ALLOWED_DIRECTORIES = BACKEND_DEV_ALLOWED_PATHS
EXPOSED_TOOLS = FULL_ACCESS_TOOLS


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateFilesystemToolset:
    """Tests for create_filesystem_toolset()."""
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_correct_filter(self, mock_toolset_class):
        """Test that create_filesystem_toolset creates toolset with correct filter."""
        create_filesystem_toolset(allowed_paths=ALLOWED_DIRECTORIES)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        
        assert call_kwargs["tool_filter"] == FULL_ACCESS_TOOLS
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_npx_command(self, mock_toolset_class):
        """Test that create_filesystem_toolset uses npx command."""
        create_filesystem_toolset(allowed_paths=ALLOWED_DIRECTORIES)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        
        # Check that the server_params specify npx
        assert connection_params.server_params.command == "npx"
        assert "-y" in connection_params.server_params.args
        assert FILESYSTEM_MCP_PACKAGE in connection_params.server_params.args
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_allowed_paths(self, mock_toolset_class):
        """Test that create_filesystem_toolset includes allowed directories."""
        create_filesystem_toolset(allowed_paths=ALLOWED_DIRECTORIES)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        # Check that allowed directories are in args
        for allowed_dir in ALLOWED_DIRECTORIES:
            assert str(allowed_dir) in args
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_custom_filter(self, mock_toolset_class):
        """Test that custom tool_filter overrides default."""
        custom_filter = ["read_file", "list_directory"]
        create_filesystem_toolset(allowed_paths=ALLOWED_DIRECTORIES, tool_filter=custom_filter)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        
        assert call_kwargs["tool_filter"] == custom_filter
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_creates_toolset_with_timeout(self, mock_toolset_class):
        """Test that create_filesystem_toolset sets connection timeout."""
        create_filesystem_toolset(allowed_paths=ALLOWED_DIRECTORIES)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        
        assert connection_params.timeout == CONNECTION_TIMEOUT
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_returns_toolset_instance(self, mock_toolset_class):
        """Test that create_filesystem_toolset returns the McpToolset instance."""
        mock_toolset = MagicMock()
        mock_toolset_class.return_value = mock_toolset
        
        result = create_filesystem_toolset(allowed_paths=ALLOWED_DIRECTORIES)
        
        assert result is mock_toolset


class TestCreateBackendDevFilesystemToolset:
    """Tests for create_backend_dev_filesystem_toolset()."""
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_uses_backend_dev_allowed_paths(self, mock_toolset_class):
        """Test that backend dev toolset uses correct allowed paths."""
        create_backend_dev_filesystem_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        # Check that backend dev allowed directories are in args
        for allowed_dir in BACKEND_DEV_ALLOWED_PATHS:
            assert str(allowed_dir) in args
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_adds_run_dir_to_paths(self, mock_toolset_class):
        """Test that run directory is added to allowed paths."""
        run_dir = "runs/run_123"
        create_backend_dev_filesystem_toolset(run_dir=run_dir)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        # The path gets converted via Path(), so check for the resolved path
        assert str(Path(run_dir)) in args


class TestCreateTesterFilesystemToolset:
    """Tests for create_tester_filesystem_toolset()."""
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_uses_tester_allowed_paths(self, mock_toolset_class):
        """Test that tester toolset uses correct allowed paths."""
        create_tester_filesystem_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        # Check that tester allowed directories are in args
        for allowed_dir in TESTER_ALLOWED_PATHS:
            assert str(allowed_dir) in args
    
    @patch("src.tools.shared.filesystem_mcp.McpToolset")
    def test_adds_run_dir_to_paths(self, mock_toolset_class):
        """Test that run directory is added to allowed paths."""
        run_dir = "runs/run_456"
        create_tester_filesystem_toolset(run_dir=run_dir)
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        args = connection_params.server_params.args
        
        # The path gets converted via Path(), so check for the resolved path
        assert str(Path(run_dir)) in args


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""
    
    def test_full_access_tools_contains_read_file(self):
        """Test that FULL_ACCESS_TOOLS contains read_file."""
        assert "read_file" in FULL_ACCESS_TOOLS
    
    def test_full_access_tools_contains_write_file(self):
        """Test that FULL_ACCESS_TOOLS contains write_file."""
        assert "write_file" in FULL_ACCESS_TOOLS
    
    def test_full_access_tools_contains_edit_file(self):
        """Test that FULL_ACCESS_TOOLS contains edit_file."""
        assert "edit_file" in FULL_ACCESS_TOOLS
    
    def test_full_access_tools_contains_list_directory(self):
        """Test that FULL_ACCESS_TOOLS contains list_directory."""
        assert "list_directory" in FULL_ACCESS_TOOLS
    
    def test_full_access_tools_contains_directory_tree(self):
        """Test that FULL_ACCESS_TOOLS contains directory_tree."""
        assert "directory_tree" in FULL_ACCESS_TOOLS
    
    def test_read_tools_subset_of_all_tools(self):
        """Test that READ_TOOLS is a subset of ALL_FILESYSTEM_TOOLS."""
        for tool in READ_TOOLS:
            assert tool in ALL_FILESYSTEM_TOOLS
    
    def test_full_access_tools_subset_of_all_tools(self):
        """Test that FULL_ACCESS_TOOLS is a subset of ALL_FILESYSTEM_TOOLS."""
        for tool in FULL_ACCESS_TOOLS:
            assert tool in ALL_FILESYSTEM_TOOLS
    
    def test_package_name_correct(self):
        """Test package name is correct."""
        assert FILESYSTEM_MCP_PACKAGE == "@modelcontextprotocol/server-filesystem"
    
    def test_timeout_value_reasonable(self):
        """Test that timeout value is reasonable."""
        assert CONNECTION_TIMEOUT >= 10  # At least 10 seconds
    
    def test_backend_dev_allowed_directories_count(self):
        """Test that we have expected number of backend dev allowed directories."""
        # Should have api, models, lib, data
        assert len(BACKEND_DEV_ALLOWED_PATHS) >= 3
    
    def test_tester_allowed_directories_count(self):
        """Test that we have expected number of tester allowed directories."""
        # Should have tests, api (read), lib (read), data (read)
        assert len(TESTER_ALLOWED_PATHS) >= 3
    
    def test_allowed_directories_under_sample_dashboard(self):
        """Test that all backend dev directories are under sample-dashboard."""
        for directory in BACKEND_DEV_ALLOWED_PATHS:
            assert str(directory).startswith(str(SAMPLE_DASHBOARD_ROOT))


# ============================================================================
# Module Export Tests
# ============================================================================


class TestModuleExports:
    """Tests for module exports via __init__.py."""
    
    def test_exports_from_shared_init(self):
        """Test that key items are exported from shared __init__.py."""
        from src.tools.shared import (
            create_filesystem_toolset,
            create_backend_dev_filesystem_toolset,
            create_tester_filesystem_toolset,
            FILESYSTEM_MCP_PACKAGE,
            READ_TOOLS,
            FULL_ACCESS_TOOLS,
            ALL_FILESYSTEM_TOOLS,
            CONNECTION_TIMEOUT,
        )
        
        assert create_filesystem_toolset is not None
        assert create_backend_dev_filesystem_toolset is not None
        assert create_tester_filesystem_toolset is not None
        assert FILESYSTEM_MCP_PACKAGE is not None
        assert READ_TOOLS is not None
        assert FULL_ACCESS_TOOLS is not None
        assert ALL_FILESYSTEM_TOOLS is not None
        assert CONNECTION_TIMEOUT is not None
    
    def test_exports_from_utils_init(self):
        """Test that path constants are exported from utils __init__.py."""
        from src.tools.utils import (
            SAMPLE_DASHBOARD_ROOT,
            BACKEND_DEV_ALLOWED_PATHS,
            TESTER_ALLOWED_PATHS,
            TESTS_ROOT,
            validate_path,
            get_relative_path,
        )
        
        assert SAMPLE_DASHBOARD_ROOT is not None
        assert BACKEND_DEV_ALLOWED_PATHS is not None
        assert TESTER_ALLOWED_PATHS is not None
        assert TESTS_ROOT is not None
        assert validate_path is not None
        assert get_relative_path is not None
    
    def test_exports_from_backend_dev_init(self):
        """Test that filesystem-related items are exported from backend_dev __init__.py."""
        from src.tools.backend_dev import (
            create_backend_dev_filesystem_toolset,
            get_backend_dev_mcp_toolset,
            FILESYSTEM_MCP_PACKAGE,
            SAMPLE_DASHBOARD_ROOT,
            ALLOWED_DIRECTORIES,
            FILESYSTEM_EXPOSED_TOOLS,
            FILESYSTEM_CONNECTION_TIMEOUT,
        )
        
        assert create_backend_dev_filesystem_toolset is not None
        assert get_backend_dev_mcp_toolset is not None
        assert FILESYSTEM_MCP_PACKAGE is not None
        assert SAMPLE_DASHBOARD_ROOT is not None
        assert ALLOWED_DIRECTORIES is not None
        assert FILESYSTEM_EXPOSED_TOOLS is not None
        assert FILESYSTEM_CONNECTION_TIMEOUT is not None
    
    def test_exports_from_tester_init(self):
        """Test that filesystem-related items are exported from tester __init__.py."""
        from src.tools.tester import (
            create_tester_filesystem_toolset,
            get_tester_mcp_toolset,
            SAMPLE_DASHBOARD_ROOT,
            TESTS_ROOT,
            TESTER_ALLOWED_PATHS,
        )
        
        assert create_tester_filesystem_toolset is not None
        assert get_tester_mcp_toolset is not None
        assert SAMPLE_DASHBOARD_ROOT is not None
        assert TESTS_ROOT is not None
        assert TESTER_ALLOWED_PATHS is not None
