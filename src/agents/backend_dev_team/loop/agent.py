"""
Backend Dev Loop Agent - Custom ADK agent for the Dev → Tester → QA cycle.

This is a custom BaseAgent that provides fine-grained control over routing:
- Route artifacts: Dev → Tester → QA (full cycle)
- Helper artifacts: Dev → Tester only (skip QA)
- Smart routing: If Tester/QA fails → immediately route back to Dev

Flow:
    Planner injects artifact → Loop(Dev ↔ Tester ↔ QA) → Result in state → Planner reads result
"""

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as gt
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.agents.backend_dev_team.loop.tools import (
    MAX_ITERATIONS,
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_LOOP_RESULT,
    STATE_KEY_LOOP_ITERATION,
    STATE_KEY_DEV_RESULT,
    STATE_KEY_TESTER_RESULT,
    STATE_KEY_QA_RESULT,
    STATE_KEY_LOOP_ERROR,
)
from src.agents.backend_dev_team.loop.callbacks import (
    initialize_dev_state,
    STATE_KEY_PREVIOUS_SUMMARIES,
)
from src.agents.backend_dev_team.dev import create_backend_dev_agent
from src.models.backend_dev import BackendDevResult

logger = get_logger(__name__)

# Model for Tester/QA sub-agents
SUB_AGENT_MODEL = "openai/gpt-4.1-mini-2025-04-14"


# =============================================================================
# Structured Output Schemas for Tester and QA agents
# =============================================================================

class TesterResult(BaseModel):
    """Structured output from the Tester Agent."""
    success: bool = Field(description="Whether test creation was successful")
    tests_passed: bool = Field(description="Whether all tests pass")
    test_files: list[str] = Field(default_factory=list, description="List of test file paths")
    test_count: int = Field(default=0, description="Number of tests created")
    failure_message: str | None = Field(default=None, description="Test failure details if any")
    error_message: str | None = Field(default=None, description="Error message if failed to create tests")


class QAResult(BaseModel):
    """Structured output from the QA Agent."""
    passed: bool = Field(description="Whether QA validation passed")
    issues: list[str] = Field(default_factory=list, description="List of issues found")
    recommendations: list[str] = Field(default_factory=list, description="Suggestions for improvement")
    error_message: str | None = Field(default=None, description="Error message if QA failed to run")


# =============================================================================
# Sub-agent instruction builders (Tester and QA)
# =============================================================================

def _build_tester_agent_instruction() -> str:
    """Build instruction for the Tester Agent."""
    return """
# Tester Agent

You create and run tests for backend artifacts implemented by the Dev Agent.

## Your Task
1. Review the artifact in `current_artifact` state
2. Check the implementation in `dev_result` state
3. Create tests for the implementation
4. Run the tests

## Important
- Create meaningful tests that verify the implementation
- Run the tests and report if they pass or fail
- If tests fail, provide clear failure messages

## Output Format
You MUST respond with a JSON object matching this schema:
{
    "success": true/false,
    "tests_passed": true/false,
    "test_files": ["path/to/test1.ts", ...],
    "test_count": 5,
    "failure_message": "Only if tests_passed is false - describe what failed",
    "error_message": "Only if success is false - could not create tests"
}
"""


def _build_qa_agent_instruction() -> str:
    """Build instruction for the QA Agent."""
    return """
# QA Agent

You validate that the implementation meets requirements and follows best practices.

## Your Task
1. Review `current_artifact` for requirements
2. Check `dev_result` for implementation details
3. Check `tester_result` for test coverage
4. Validate quality, correctness, and completeness

## Validation Checklist
- Does the implementation match the artifact spec?
- Are edge cases handled?
- Is error handling proper?
- Are tests comprehensive enough?
- Does the code follow best practices?

## Output Format
You MUST respond with a JSON object matching this schema:
{
    "passed": true/false,
    "issues": ["Issue 1", "Issue 2", ...],
    "recommendations": ["Recommendation 1", ...],
    "error_message": "Only if QA could not run properly"
}
"""


# =============================================================================
# Sub-agent factories
# =============================================================================

def create_dev_agent() -> LlmAgent:
    """
    Create the Backend Dev Agent.
    
    Uses create_backend_dev_agent() which provides:
    - Full tools (create_api, create_model, create_helper, MCP filesystem, etc.)
    - PlanReActPlanner for structured reasoning
    - BackendDevResult output schema
    - Dynamic instruction provider that reads from state
    
    We add output_key so the result goes to STATE_KEY_DEV_RESULT for loop checking.
    
    Note: State initialization happens ONCE at the start of _run_async_impl,
    NOT on every Dev Agent invocation.
    """
    agent = create_backend_dev_agent()
    # Set output_key so Loop Agent can read dev_result from state
    agent.output_key = STATE_KEY_DEV_RESULT
    return agent


def create_tester_agent() -> LlmAgent:
    """Create the Tester Agent with structured output."""
    return LlmAgent(
        name="backend_tester",
        model=LiteLlm(model=SUB_AGENT_MODEL),
        instruction=_build_tester_agent_instruction(),
        output_schema=TesterResult,
        output_key=STATE_KEY_TESTER_RESULT,
    )


def create_qa_agent() -> LlmAgent:
    """Create the QA Agent with structured output."""
    return LlmAgent(
        name="backend_qa",
        model=LiteLlm(model=SUB_AGENT_MODEL),
        instruction=_build_qa_agent_instruction(),
        output_schema=QAResult,
        output_key=STATE_KEY_QA_RESULT,
    )


# =============================================================================
# Custom Loop Agent
# =============================================================================

class BackendDevLoopAgent(BaseAgent):
    """
    Custom agent for the Dev → Tester → QA loop with smart routing.
    
    Routing Logic:
    - Route artifacts: Dev → Tester → QA (full cycle)
    - Helper artifacts: Dev → Tester only (skip QA)
    - If Dev fails: Exit loop with failure
    - If Tester fails (tests don't pass): Route back to Dev immediately
    - If QA fails: Route back to Dev immediately
    - Loop continues until success or max_iterations reached
    
    State Requirements (input):
        - current_artifact: The artifact to process
        - run_dir: Path to run directory (for dashboard_concept, cleaned data)
        
    State Output:
        - loop_result: "pass" | "fail" | "max_iterations"
        - loop_iteration: Number of cycles executed
        - dev_result, tester_result, qa_result: Sub-agent outputs
        - previous_summaries: Updated with completed artifact summary
    """
    
    dev_agent: LlmAgent
    tester_agent: LlmAgent
    qa_agent: LlmAgent
    max_iterations: int = MAX_ITERATIONS
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(
        self,
        name: str = "backend_loop",
        dev_agent: LlmAgent | None = None,
        tester_agent: LlmAgent | None = None,
        qa_agent: LlmAgent | None = None,
        max_iterations: int = MAX_ITERATIONS,
        **kwargs,
    ):
        """Initialize the Backend Dev Loop Agent."""
        _dev = dev_agent or create_dev_agent()
        _tester = tester_agent or create_tester_agent()
        _qa = qa_agent or create_qa_agent()
        
        super().__init__(
            name=name,
            sub_agents=[_dev, _tester, _qa],
            **kwargs,
        )
        
        object.__setattr__(self, "dev_agent", _dev)
        object.__setattr__(self, "tester_agent", _tester)
        object.__setattr__(self, "qa_agent", _qa)
        object.__setattr__(self, "max_iterations", max_iterations)
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Execute the Dev → Tester → QA loop with smart routing."""
        state = ctx.session.state
        
        # Get artifact from state
        artifact = state.get(STATE_KEY_CURRENT_ARTIFACT)
        if not artifact:
            logger.error("No artifact in state - cannot proceed")
            state[STATE_KEY_LOOP_RESULT] = "fail"
            state[STATE_KEY_LOOP_ERROR] = "No artifact provided in state"
            yield self._create_status_event("Error: No artifact to process")
            return
        
        artifact_id = artifact.get("id", "unknown")
        artifact_kind = artifact.get("kind", "route")
        needs_qa = artifact_kind == "route"
        
        logger.info(
            f"Starting loop for {artifact_id} (kind={artifact_kind}, needs_qa={needs_qa})",
            extra={"agent": self.name, "artifact_id": artifact_id}
        )
        
        # =================================================================
        # INITIALIZE STATE ONCE before the loop starts
        # This sets workspace_root, metrics_ref_context, cleaned_data_files
        # =================================================================
        initialize_dev_state(state, artifact)
        
        # Initialize iteration counter
        state[STATE_KEY_LOOP_ITERATION] = 0
        
        for iteration in range(1, self.max_iterations + 1):
            state[STATE_KEY_LOOP_ITERATION] = iteration
            
            logger.info(
                f"Iteration {iteration}/{self.max_iterations} for {artifact_id}",
                extra={"agent": self.name, "iteration": iteration}
            )
            
            # --- DEV PHASE ---
            logger.info(f"[{artifact_id}] Running Dev Agent...")
            async for event in self.dev_agent.run_async(ctx):
                yield event
            
            dev_result = state.get(STATE_KEY_DEV_RESULT)
            if not self._check_dev_success(dev_result):
                logger.warning(f"[{artifact_id}] Dev Agent failed - exiting loop")
                state[STATE_KEY_LOOP_RESULT] = "fail"
                state[STATE_KEY_LOOP_ERROR] = "Dev Agent failed to implement"
                yield self._create_status_event(f"Dev failed for {artifact_id}")
                return
            
            # --- TESTER PHASE ---
            logger.info(f"[{artifact_id}] Running Tester Agent...")
            async for event in self.tester_agent.run_async(ctx):
                yield event
            
            tester_result = state.get(STATE_KEY_TESTER_RESULT)
            if not self._check_tester_success(tester_result):
                logger.info(f"[{artifact_id}] Tests failed - routing back to Dev")
                yield self._create_status_event(
                    f"Tests failed for {artifact_id}, routing back to Dev (iteration {iteration})"
                )
                continue
            
            # --- QA PHASE (only for routes) ---
            if needs_qa:
                logger.info(f"[{artifact_id}] Running QA Agent...")
                async for event in self.qa_agent.run_async(ctx):
                    yield event
                
                qa_result = state.get(STATE_KEY_QA_RESULT)
                if not self._check_qa_success(qa_result):
                    logger.info(f"[{artifact_id}] QA failed - routing back to Dev")
                    yield self._create_status_event(
                        f"QA failed for {artifact_id}, routing back to Dev (iteration {iteration})"
                    )
                    continue
            
            # --- SUCCESS ---
            logger.info(f"[{artifact_id}] Loop completed successfully!")
            state[STATE_KEY_LOOP_RESULT] = "pass"
            self._append_dev_summary_to_state(state, dev_result, artifact_id)
            yield self._create_status_event(
                f"SUCCESS: {artifact_id} completed in {iteration} iteration(s)"
            )
            return
        
        # --- MAX ITERATIONS REACHED ---
        logger.warning(f"[{artifact_id}] Max iterations ({self.max_iterations}) reached")
        state[STATE_KEY_LOOP_RESULT] = "max_iterations"
        state[STATE_KEY_LOOP_ERROR] = f"Max iterations ({self.max_iterations}) reached"
        yield self._create_status_event(f"FAILED: {artifact_id} - max iterations reached")
    
    def _check_dev_success(self, dev_result: dict | BackendDevResult | None) -> bool:
        """Check if Dev Agent succeeded (status='success')."""
        if dev_result is None:
            return False
        if isinstance(dev_result, dict):
            return dev_result.get("status") == "success"
        return dev_result.status == "success"
    
    def _check_tester_success(self, tester_result: dict | TesterResult | None) -> bool:
        """Check if Tester Agent succeeded AND tests passed."""
        if tester_result is None:
            return False
        if isinstance(tester_result, dict):
            return tester_result.get("success", False) and tester_result.get("tests_passed", False)
        return tester_result.success and tester_result.tests_passed
    
    def _check_qa_success(self, qa_result: dict | QAResult | None) -> bool:
        """Check if QA Agent passed."""
        if qa_result is None:
            return False
        if isinstance(qa_result, dict):
            return qa_result.get("passed", False)
        return qa_result.passed
    
    def _append_dev_summary_to_state(
        self,
        state: dict,
        dev_result: dict | BackendDevResult | None,
        artifact_id: str,
    ) -> None:
        """Extract summary from DevReport and append to previous_summaries."""
        if dev_result is None:
            return
        
        summary = None
        if isinstance(dev_result, dict):
            report = dev_result.get("report", {})
            if isinstance(report, dict):
                summary = report.get("summary")
            if not summary:
                summary = dev_result.get("summary")
        elif hasattr(dev_result, "report") and dev_result.report:
            summary = dev_result.report.summary
        
        if not summary:
            summary = f"Completed {artifact_id}"
        
        if STATE_KEY_PREVIOUS_SUMMARIES not in state:
            state[STATE_KEY_PREVIOUS_SUMMARIES] = []
        
        state[STATE_KEY_PREVIOUS_SUMMARIES].append(f"[{artifact_id}] {summary}")
    
    def _create_status_event(self, message: str) -> Event:
        """Create a status event from this agent."""
        return Event(
            author=self.name,
            content=gt.Content(role="model", parts=[gt.Part.from_text(text=message)]),
        )


# =============================================================================
# Factory functions
# =============================================================================

def create_loop_agent(
    dev_agent: LlmAgent | None = None,
    tester_agent: LlmAgent | None = None,
    qa_agent: LlmAgent | None = None,
    max_iterations: int = MAX_ITERATIONS,
) -> BackendDevLoopAgent:
    """Create a Backend Dev Loop Agent."""
    return BackendDevLoopAgent(
        name="backend_loop",
        dev_agent=dev_agent,
        tester_agent=tester_agent,
        qa_agent=qa_agent,
        max_iterations=max_iterations,
    )


def get_loop_agent() -> BackendDevLoopAgent:
    """Get a configured Loop Agent instance with default sub-agents."""
    return create_loop_agent()


__all__ = [
    "BackendDevLoopAgent",
    "create_loop_agent",
    "get_loop_agent",
    "create_dev_agent",
    "create_tester_agent",
    "create_qa_agent",
    "TesterResult",
    "QAResult",
    "SUB_AGENT_MODEL",
    "MAX_ITERATIONS",
]

