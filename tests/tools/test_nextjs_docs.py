"""
Tests for Next.js documentation MCP integration.

Tests the create_nextjs_docs_toolset() factory function for creating
McpToolset instances that connect to the Next.js DevTools MCP server,
and the call_init() helper for manual initialization.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.backend_dev.nextjs_docs import (
    NEXTJS_DEVTOOLS_PACKAGE,
    EXPOSED_TOOLS,
    CONNECTION_TIMEOUT,
    create_nextjs_docs_toolset,
    call_init,
)


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateNextjsDocsToolset:
    """Tests for create_nextjs_docs_toolset()."""
    
    @patch("src.tools.backend_dev.nextjs_docs.McpToolset")
    def test_creates_toolset_with_correct_filter(self, mock_toolset_class):
        """Test that create_nextjs_docs_toolset creates toolset with correct filter."""
        create_nextjs_docs_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        
        assert call_kwargs["tool_filter"] == EXPOSED_TOOLS
    
    @patch("src.tools.backend_dev.nextjs_docs.McpToolset")
    def test_creates_toolset_with_npx_command(self, mock_toolset_class):
        """Test that create_nextjs_docs_toolset uses npx command."""
        create_nextjs_docs_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        
        # Check that the server_params specify npx
        assert connection_params.server_params.command == "npx"
        assert "-y" in connection_params.server_params.args
        assert NEXTJS_DEVTOOLS_PACKAGE in connection_params.server_params.args
    
    @patch("src.tools.backend_dev.nextjs_docs.McpToolset")
    def test_creates_toolset_with_timeout(self, mock_toolset_class):
        """Test that create_nextjs_docs_toolset sets connection timeout."""
        create_nextjs_docs_toolset()
        
        mock_toolset_class.assert_called_once()
        call_kwargs = mock_toolset_class.call_args.kwargs
        connection_params = call_kwargs["connection_params"]
        
        assert connection_params.timeout == CONNECTION_TIMEOUT
    
    @patch("src.tools.backend_dev.nextjs_docs.McpToolset")
    def test_returns_toolset_instance(self, mock_toolset_class):
        """Test that create_nextjs_docs_toolset returns the McpToolset instance."""
        mock_toolset = MagicMock()
        mock_toolset_class.return_value = mock_toolset
        
        result = create_nextjs_docs_toolset()
        
        assert result is mock_toolset


# ============================================================================
# call_init() Tests
# ============================================================================


class TestCallInit:
    """Tests for call_init() helper function."""
    
    @pytest.mark.asyncio
    async def test_call_init_finds_and_calls_init_tool(self):
        """Test that call_init finds the init tool and calls it."""
        # Create mock tools
        mock_init_tool = MagicMock()
        mock_init_tool.name = "init"
        mock_init_tool.run_async = AsyncMock(return_value={"status": "initialized"})
        
        mock_docs_tool = MagicMock()
        mock_docs_tool.name = "nextjs_docs"
        
        # Create mock toolset
        mock_toolset = MagicMock()
        mock_toolset.get_tools = AsyncMock(return_value=[mock_init_tool, mock_docs_tool])
        
        result = await call_init(mock_toolset)
        
        # Verify get_tools was called
        mock_toolset.get_tools.assert_awaited_once()
        
        # Verify init tool's run_async was called with empty args
        mock_init_tool.run_async.assert_awaited_once_with(args={}, tool_context=None)
        
        # Verify result
        assert result == {"status": "initialized"}
    
    @pytest.mark.asyncio
    async def test_call_init_raises_if_init_not_found(self):
        """Test that call_init raises ValueError if init tool not found."""
        # Create mock tools without init
        mock_docs_tool = MagicMock()
        mock_docs_tool.name = "nextjs_docs"
        
        mock_toolset = MagicMock()
        mock_toolset.get_tools = AsyncMock(return_value=[mock_docs_tool])
        
        with pytest.raises(ValueError, match="'init' tool not found"):
            await call_init(mock_toolset)
    
    @pytest.mark.asyncio
    async def test_call_init_raises_if_no_tools(self):
        """Test that call_init raises ValueError if toolset has no tools."""
        mock_toolset = MagicMock()
        mock_toolset.get_tools = AsyncMock(return_value=[])
        
        with pytest.raises(ValueError, match="'init' tool not found"):
            await call_init(mock_toolset)


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""
    
    def test_exposed_tools_contains_init(self):
        """Test that EXPOSED_TOOLS contains init (required first)."""
        assert "init" in EXPOSED_TOOLS
    
    def test_exposed_tools_contains_nextjs_docs(self):
        """Test that EXPOSED_TOOLS contains nextjs_docs."""
        assert "nextjs_docs" in EXPOSED_TOOLS
    
    def test_exposed_tools_length(self):
        """Test that EXPOSED_TOOLS has exactly 2 tools."""
        assert len(EXPOSED_TOOLS) == 2
    
    def test_package_name_is_latest(self):
        """Test that package uses @latest tag."""
        assert "@latest" in NEXTJS_DEVTOOLS_PACKAGE
    
    def test_package_name_correct(self):
        """Test package name is correct."""
        assert NEXTJS_DEVTOOLS_PACKAGE == "next-devtools-mcp@latest"
    
    def test_timeout_value_reasonable(self):
        """Test that timeout value is reasonable."""
        assert CONNECTION_TIMEOUT >= 10  # At least 10 seconds


# ============================================================================
# Module Export Tests
# ============================================================================


class TestModuleExports:
    """Tests for module exports via __init__.py."""
    
    def test_exports_from_init(self):
        """Test that key items are exported from __init__.py."""
        from src.tools.backend_dev import (
            create_nextjs_docs_toolset,
            call_nextjs_init,
            NEXTJS_DEVTOOLS_PACKAGE,
            NEXTJS_EXPOSED_TOOLS,
            NEXTJS_CONNECTION_TIMEOUT,
        )
        
        assert create_nextjs_docs_toolset is not None
        assert call_nextjs_init is not None
        assert NEXTJS_DEVTOOLS_PACKAGE is not None
        assert NEXTJS_EXPOSED_TOOLS is not None
        assert NEXTJS_CONNECTION_TIMEOUT is not None
