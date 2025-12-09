"""Data models for the system"""

from src.models.backend_dev import (
    DevCurrentState,
    DevChanges,
    DevReport,
    BackendDevInput,
    BackendDevResult,
)

from src.models.testing_agent import (
    TestCurrentState,
    TestChanges,
    TestExecutionResult,
    TestReport,
    TestAgentInput,
    TestAgentResult,
)

__all__ = [
    # Backend Dev models
    "DevCurrentState",
    "DevChanges",
    "DevReport",
    "BackendDevInput",
    "BackendDevResult",
    # Testing Agent models
    "TestCurrentState",
    "TestChanges",
    "TestExecutionResult",
    "TestReport",
    "TestAgentInput",
    "TestAgentResult",
]
