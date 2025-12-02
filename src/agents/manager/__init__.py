"""
Manager Agent - Root entry point for the multi-agent dashboard building system.

The ManagerAgent is a custom BaseAgent that:
1. Manages sub-agents (orchestrator, data_analysis, planner)
2. Intercepts delegation tool calls and routes to appropriate sub-agents
3. Maintains action summaries for each sub-agent across turns
4. Handles the streaming sub-agent pattern with synthetic tool responses
"""

from src.agents.manager.agent import ManagerAgent, create_manager_agent

__all__ = ["ManagerAgent", "create_manager_agent"]
