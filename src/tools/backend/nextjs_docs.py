"""
Next.js Documentation MCP integration for the Backend Agent.

Provides access to official Next.js documentation via the Next.js DevTools MCP server.
https://github.com/vercel/next-devtools-mcp

Usage:
    # Option 1: Let agent call init (automatic)
    from src.tools.backend.nextjs_docs import create_nextjs_docs_toolset
    
    agent = LlmAgent(
        model="gemini-2.0-flash",
        name="backend_agent",
        instruction="Call 'init' before using 'nextjs_docs'.",
        tools=[create_nextjs_docs_toolset()],
    )
    
    # Option 2: Call init manually before agent runs (recommended)
    from src.tools.backend.nextjs_docs import create_nextjs_docs_toolset, call_init
    
    toolset = create_nextjs_docs_toolset()
    await call_init(toolset)  # Pre-initialize, no ToolContext needed
    
    agent = LlmAgent(
        model="gemini-2.0-flash",
        name="backend_agent",
        tools=[toolset],  # Now only 'nextjs_docs' is needed
    )

Note:
    - McpToolset manages connection lifecycle automatically
    - call_init() can pre-initialize the MCP server before agent runs
    - After init, only 'nextjs_docs' tool is needed by the agent
"""
from __future__ import annotations

from typing import Any

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters


# ============================================================================
# Constants
# ============================================================================

# Next.js DevTools MCP server NPM package
NEXTJS_DEVTOOLS_PACKAGE = "next-devtools-mcp@latest"

# Tools exposed to the agent (init must be called first by the agent)
EXPOSED_TOOLS = ["init", "nextjs_docs"]

# Connection timeout (seconds)
CONNECTION_TIMEOUT = 30


# ============================================================================
# Toolset Factory
# ============================================================================


def create_nextjs_docs_toolset() -> McpToolset:
    """
    Create a McpToolset for Next.js documentation access.
    
    Returns an McpToolset that can be added directly to an agent's tools list.
    The toolset exposes 'init' and 'nextjs_docs' tools from the Next.js DevTools MCP server.
    
    Note: Either call `call_init(toolset)` before agent runs, or instruct
    the agent to call 'init' first.
    
    Returns:
        McpToolset configured for next-devtools-mcp.
    
    Example:
        # Option 1: Manual pre-initialization (recommended)
        toolset = create_nextjs_docs_toolset()
        await call_init(toolset)
        agent = LlmAgent(tools=[toolset])
        
        # Option 2: Let agent call init
        agent = LlmAgent(
            instruction="Call 'init' before 'nextjs_docs'.",
            tools=[create_nextjs_docs_toolset()],
        )
    """
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", NEXTJS_DEVTOOLS_PACKAGE],
            ),
            timeout=CONNECTION_TIMEOUT,
        ),
        tool_filter=EXPOSED_TOOLS,
    )


# ============================================================================
# Manual Initialization Helper
# ============================================================================


async def call_init(toolset: McpToolset) -> dict[str, Any]:
    """
    Manually call the 'init' tool on a McpToolset.
    
    This allows pre-initialization of the MCP server before the agent runs,
    which can be more convenient than having the agent call init.
    
    Args:
        toolset: A McpToolset created by create_nextjs_docs_toolset().
    
    Returns:
        The result from the init tool call.
    
    Raises:
        ValueError: If 'init' tool is not found in the toolset.
    
    Example:
        toolset = create_nextjs_docs_toolset()
        result = await call_init(toolset)
        print(f"Initialized: {result}")
        # Now use toolset with agent - init already done
    """
    # Get all tools from the toolset
    tools = await toolset.get_tools()
    
    # Find the init tool
    init_tool = None
    for tool in tools:
        if tool.name == "init":
            init_tool = tool
            break
    
    if init_tool is None:
        raise ValueError("'init' tool not found in toolset")
    
    # Call init with empty args (no ToolContext needed for init)
    # McpTool.run_async accepts args and tool_context
    result = await init_tool.run_async(args={}, tool_context=None)  # type: ignore
    return result
