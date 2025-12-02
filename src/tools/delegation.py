"""
Delegation tools for the Manager Agent pattern.

These are dummy functions that the orchestrator sees as tools.
The Manager intercepts calls to these tools and routes to the appropriate sub-agent.

The tools:
1. delegate_data_analysis - Route to Data Analysis Agent
2. delegate_planner - Route to Planner Agent
3. summarize_actions - Track actions taken by sub-agents across turns

The Manager intercepts delegate_* calls and:
- Writes task_description to tmp:data_analysis_task or tmp:planner_task
- Runs the sub-agent
- Returns the sub-agent's final output as the tool response
"""

from typing import Any, Dict, List
from google.adk.tools import FunctionTool, ToolContext

from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# DUMMY DELEGATION TOOLS (Intercepted by Manager)
# ============================================================================

def delegate_data_analysis(task_description: str) -> str:
    """
    Delegate a task to the Data Analysis Agent.
    
    The Data Analysis Agent will:
    - Profile and clean the dataset
    - Generate data_profile.md and cleaning_summary.md
    - Optionally perform additional statistical analyses
    - Return a structured DataAnalysisOutput
    
    Args:
        task_description: Detailed instructions for the Data Analysis Agent.
            Should include:
            - What analysis is needed
            - Any specific cleaning requirements
            - Reference to user goals if relevant
    
    Returns:
        The Data Analysis Agent's final response with analysis results.
        
    """
    return "dummy"


def delegate_planner(task_description: str) -> str:
    """
    Delegate a task to the Planner Agent.
    
    The Planner Agent will:
    - Read data analysis artifacts (data_profile.md, cleaning_summary.md)
    - Design a dashboard concept based on user goals
    - Generate dashboard.json specification
    - Return a structured PlannerOutput
    
    Args:
        task_description: Complete handoff message for the Planner Agent.
            Should include:
            - User goals (goal, audience, use_case, constraints)
            - Data context summary from Data Analysis Agent
            - Any specific dashboard requirements
    
    Returns:
        The Planner Agent's final response with dashboard specification.
        
    """
    return "dummy"


# ============================================================================
# SUMMARIZE ACTIONS TOOL (For sub-agent context across turns)
# ============================================================================

# Map agent names to their summary state keys
AGENT_SUMMARY_KEYS = {
    "data_analysis_agent": "data_analysis_summaries",
    "planner_agent": "planner_summaries",
}


def summarize_actions(
    summary: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """
    Record a summary of actions taken by the current agent.
    
    This tool is called by sub-agents (data_analysis, planner) at the end of their
    turn to record what they did. These summaries are stored in session state and
    injected into subsequent turns to provide context.
    
    The agent type is automatically inferred from the invocation context.
    
    Args:
        summary: A concise summary of actions taken during this turn.
            Should include:
            - Tools that were used
            - Artifacts that were created
            - Key decisions or findings
            - Any issues or follow-ups needed
    
    Returns:
        Dictionary with:
        - success: bool indicating if summary was recorded
        - agent_name: The name of the agent that recorded the summary
        - message: Status message
        - total_summaries: Number of summaries for this agent
    """
    # Infer agent name from invocation context
    agent_name = tool_context._invocation_context.agent.name
    
    # Determine the state key based on agent name
    state_key = AGENT_SUMMARY_KEYS.get(agent_name)
    
    if state_key is None:
        return {
            "success": False,
            "agent_name": agent_name,
            "message": f"Agent '{agent_name}' is not configured for action summaries. "
                      f"Allowed agents: {list(AGENT_SUMMARY_KEYS.keys())}",
            "total_summaries": 0
        }
    
    state = tool_context.state
    
    # Initialize if not present
    if state_key not in state:
        state[state_key] = []
    
    # Append the new summary
    summaries: List[str] = state[state_key]
    summaries.append(summary)
    state[state_key] = summaries
    
    logger.info(
        f"Recorded action summary for {agent_name}",
        extra={
            "agent": agent_name,
            "phase": "summarize_actions",
            "summary_count": len(summaries)
        }
    )
    
    return {
        "success": True,
        "agent_name": agent_name,
        "message": f"Summary recorded for {agent_name}",
        "total_summaries": len(summaries)
    }


# ============================================================================
# TOOL INSTANCES
# ============================================================================

# Dummy delegation tools (intercepted by Manager)
delegate_data_analysis_tool = FunctionTool(func=delegate_data_analysis)
delegate_planner_tool = FunctionTool(func=delegate_planner)

# Summarize actions tool (actually executed, updates state)
summarize_actions_tool = FunctionTool(func=summarize_actions)
