"""
Tester Agent package.

The Tester Agent writes tests for backend artifacts to verify they meet
the expected behavior defined in the artifact specification.
"""

from src.agents.backend_dev_team.tester.agent import (
    create_tester_agent,
    get_tester_agent,
    tester_instruction_provider,
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_WORKSPACE_ROOT,
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_DEV_RESULT,
    STATE_KEY_DEV_REPORT_PATH,
    STATE_KEY_PREVIOUS_TEST_SUMMARY,
    STATE_KEY_CLEANED_DATA_FILES,
    STATE_KEY_TESTER_RESULT,
    TESTER_MODEL,
)

from src.agents.backend_dev_team.tester.prompts import (
    build_tester_prompt,
    ROUTE_TEST_PATTERNS,
    HELPER_TEST_PATTERNS,
    MINIMAL_TEST_PROMPT,
)


__all__ = [
    # Agent factory
    "create_tester_agent",
    "get_tester_agent",
    # Instruction provider
    "tester_instruction_provider",
    # Prompts
    "build_tester_prompt",
    "ROUTE_TEST_PATTERNS",
    "HELPER_TEST_PATTERNS",
    "MINIMAL_TEST_PROMPT",
    # State keys
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_CURRENT_ARTIFACT",
    "STATE_KEY_DEV_RESULT",
    "STATE_KEY_DEV_REPORT_PATH",
    "STATE_KEY_PREVIOUS_TEST_SUMMARY",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_TESTER_RESULT",
    # Constants
    "TESTER_MODEL",
]
