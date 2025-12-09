"""
Loop Agent Package - Custom BaseAgent for Dev → Tester → QA cycle.

This package provides a custom agent with smart routing:
- Route artifacts: Dev → Tester → QA (full cycle)
- Helper artifacts: Dev → Tester only (skip QA)
- Smart routing: If Tester/QA fails → immediately route back to Dev

Flow:
    Planner injects artifact → Loop(Dev ↔ Tester ↔ QA) → Result in state → Planner reads result
"""

from src.agents.backend_dev_team.loop.agent import (
    # Main agent
    BackendDevLoopAgent,
    create_loop_agent,
    get_loop_agent,
    # Sub-agent factories
    create_qa_agent,
    # Structured output schema (QA only - Dev uses BackendDevResult, Tester uses TestAgentResult)
    QAResult,
    # Constants
    SUB_AGENT_MODEL,
)
from src.agents.backend_dev_team.loop.tools import (
    # Tool and FunctionTool wrapper
    exit_loop,
    exit_loop_tool,
    # State keys
    STATE_KEY_RUN_DIR,
    STATE_KEY_RUN_ID,
    STATE_KEY_BACKEND_TODO_LIST,
    STATE_KEY_BACKEND_TODOS_PATH,
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_CURRENT_ARTIFACT_ID,
    STATE_KEY_LOOP_RESULT,
    STATE_KEY_LOOP_ERROR,
    STATE_KEY_LOOP_ITERATION,
    STATE_KEY_QA_RESULT,
    STATE_KEY_DEV_REPORT_PATH,
    STATE_KEY_TEST_REPORT_PATH,
    STATE_KEY_RETRY_COUNT,
    STATE_KEY_PREVIOUS_TEST_SUMMARY,
    STATE_KEY_ESCALATION_REASON,
    # Constants
    MAX_ITERATIONS,
    MAX_TOTAL_RETRIES,
    # State helpers
    get_current_artifact,
    get_loop_result,
    set_loop_result,
    clear_loop_state,
    inject_artifact_to_state,
)
from src.agents.backend_dev_team.loop.callbacks import (
    STATE_KEY_WORKSPACE_ROOT,
    STATE_KEY_PREVIOUS_SUMMARIES,
    STATE_KEY_CLEANED_DATA_FILES,
    STATE_KEY_METRICS_REF_CONTEXT,
)

__all__ = [
    # Main agent class and factories
    "BackendDevLoopAgent",
    "create_loop_agent",
    "get_loop_agent",
    "create_loop_tester_agent",
    "create_qa_agent",
    # Structured output schema (QA only)
    "QAResult",
    # Tool and FunctionTool wrapper
    "exit_loop",
    "exit_loop_tool",
    # State keys
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_RUN_ID",
    "STATE_KEY_BACKEND_TODO_LIST",
    "STATE_KEY_BACKEND_TODOS_PATH",
    "STATE_KEY_CURRENT_ARTIFACT",
    "STATE_KEY_CURRENT_ARTIFACT_ID",
    "STATE_KEY_LOOP_RESULT",
    "STATE_KEY_LOOP_ERROR",
    "STATE_KEY_LOOP_ITERATION",
    "STATE_KEY_TESTER_RESULT",
    "STATE_KEY_QA_RESULT",
    "STATE_KEY_DEV_REPORT_PATH",
    "STATE_KEY_TEST_REPORT_PATH",
    "STATE_KEY_RETRY_COUNT",
    "STATE_KEY_PREVIOUS_TEST_SUMMARY",
    "STATE_KEY_ESCALATION_REASON",
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_PREVIOUS_SUMMARIES",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_METRICS_REF_CONTEXT",
    # Constants
    "MAX_ITERATIONS",
    "MAX_TOTAL_RETRIES",
    "SUB_AGENT_MODEL",
    # State helpers
    "get_current_artifact",
    "get_loop_result",
    "set_loop_result",
    "clear_loop_state",
    "inject_artifact_to_state",
]
