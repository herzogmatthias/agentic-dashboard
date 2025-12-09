"""
Backend Dev Loop Agent - Custom ADK agent for the Dev → Tester → QA cycle.

This is a custom BaseAgent that provides fine-grained control over routing:
- Route artifacts: Dev → Tester → QA (full cycle)
- Helper artifacts: Dev → Tester only (skip QA)
- Smart routing: If Tester/QA fails → immediately route back to Dev

Callbacks (uses ADK built-in before_agent_callback / after_agent_callback):
- before_agent_callback: Called at start, enables standalone testing (artifact injection)
- after_agent_callback: Called after completion, enables manifest persistence

Flow:
    Planner injects artifact → Loop(Dev ↔ Tester ↔ QA) → Result in state → Planner reads result
"""

import json
from pathlib import Path
from typing import AsyncGenerator, Optional, Any

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as gt
from pydantic import BaseModel, Field

from src.agents.backend_dev_team.tester.state import STATE_KEY_TESTER_RESULT
from src.core.logging import get_logger
from src.agents.backend_dev_team.loop.tools import (
    MAX_ITERATIONS,
    MAX_TOTAL_RETRIES,
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_LOOP_RESULT,
    STATE_KEY_LOOP_ITERATION,
    STATE_KEY_QA_RESULT,
    STATE_KEY_LOOP_ERROR,
    STATE_KEY_RETRY_COUNT,
    STATE_KEY_PREVIOUS_TEST_SUMMARY,
    STATE_KEY_ESCALATION_REASON,
    STATE_KEY_DEV_REPORT_PATH,
    STATE_KEY_TEST_REPORT_PATH,
    STATE_KEY_RUN_DIR,
)
from src.agents.backend_dev_team.loop.callbacks import (
    before_loop_callback,
    after_loop_callback,
    STATE_KEY_PREVIOUS_SUMMARIES,
)
from src.agents.backend_dev_team.dev import create_backend_dev_agent
from src.agents.backend_dev_team.dev.state import STATE_KEY_DEV_RESULT
from src.agents.backend_dev_team.tester import create_tester_agent
from src.models.backend_dev import BackendDevResult
from src.models.testing_agent import TestAgentResult

logger = get_logger(__name__)

# Model for QA sub-agent (Tester now has its own full implementation)
SUB_AGENT_MODEL = "openai/gpt-4.1-mini-2025-04-14"


# =============================================================================
# Report Persistence Helpers
# =============================================================================

def _persist_dev_report(
    state: dict,
    dev_result: dict | BackendDevResult | None,
    artifact_id: str,
) -> str | None:
    """
    Persist DevReport to disk after Dev Agent completes.
    
    Creates: {run_dir}/dev/{artifact_id}.dev_report.json
    
    Returns the file path if successful, None otherwise.
    """
    if dev_result is None:
        return None
    
    run_dir = state.get(STATE_KEY_RUN_DIR)
    if not run_dir:
        logger.warning("Cannot persist DevReport: run_dir not in state")
        return None
    
    # Extract report data
    if isinstance(dev_result, dict):
        report_data = dev_result.get("report", dev_result)
    elif hasattr(dev_result, "report") and dev_result.report:
        report_data = dev_result.report.model_dump(mode="json")
    elif hasattr(dev_result, "model_dump"):
        report_data = dev_result.model_dump(mode="json")
    else:
        report_data = {"raw": str(dev_result)}
    
    # Ensure dev reports directory exists
    dev_dir = Path(run_dir) / "dev"
    dev_dir.mkdir(parents=True, exist_ok=True)
    
    # Write report
    report_path = dev_dir / f"{artifact_id}.dev_report.json"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        logger.info(f"Persisted DevReport to {report_path}")
        return str(report_path)
    except Exception as e:
        logger.error(f"Failed to persist DevReport: {e}")
        return None


def _persist_test_report(
    state: dict,
    tester_result: dict | TestAgentResult | None,
    artifact_id: str,
) -> str | None:
    """
    Persist TestReport to disk after Tester Agent completes.
    
    Creates: {run_dir}/dev/{artifact_id}.test_report.json
    
    Returns the file path if successful, None otherwise.
    """
    if tester_result is None:
        return None
    
    run_dir = state.get(STATE_KEY_RUN_DIR)
    if not run_dir:
        logger.warning("Cannot persist TestReport: run_dir not in state")
        return None
    
    # Extract test_report data
    if isinstance(tester_result, dict):
        report_data = tester_result.get("test_report", tester_result)
    elif hasattr(tester_result, "test_report") and tester_result.test_report:
        report_data = tester_result.test_report.model_dump(mode="json")
    elif hasattr(tester_result, "model_dump"):
        report_data = tester_result.model_dump(mode="json")
    else:
        report_data = {"raw": str(tester_result)}
    
    # Ensure dev reports directory exists (test reports alongside dev reports)
    dev_dir = Path(run_dir) / "dev"
    dev_dir.mkdir(parents=True, exist_ok=True)
    
    # Write report
    report_path = dev_dir / f"{artifact_id}.test_report.json"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        logger.info(f"Persisted TestReport to {report_path}")
        return str(report_path)
    except Exception as e:
        logger.error(f"Failed to persist TestReport: {e}")
        return None


# =============================================================================
# Structured Output Schema for QA agent (Tester is now in tester/agent.py)
# =============================================================================

class QAResult(BaseModel):
    """Structured output from the QA Agent."""
    passed: bool = Field(description="Whether QA validation passed")
    issues: list[str] = Field(default_factory=list, description="List of issues found")
    recommendations: list[str] = Field(default_factory=list, description="Suggestions for improvement")
    error_message: str | None = Field(default=None, description="Error message if QA failed to run")


# =============================================================================
# Sub-agent instruction builder (QA only - Tester is in tester/agent.py)
# =============================================================================

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
    
    Uses ADK built-in callbacks (inherited from BaseAgent):
    - before_agent_callback: Called before agent runs, enables standalone testing
    - after_agent_callback: Called after agent runs, enables manifest persistence
    
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
    
    def __init__(
        self,
        dev_agent: LlmAgent,
        tester_agent: LlmAgent,
        qa_agent: LlmAgent,
        name: str = "backend_loop",
        max_iterations: int = MAX_ITERATIONS,
        before_agent_callback=None,
        after_agent_callback=None,
    ):
        """Initialize the Backend Dev Loop Agent."""
        dev_agent = dev_agent
        tester_agent = tester_agent
        qa_agent = qa_agent
        
        super().__init__(
            name=name,
            dev_agent=dev_agent,
            tester_agent=tester_agent,
            qa_agent=qa_agent,
            sub_agents=[dev_agent, tester_agent, qa_agent],
            before_agent_callback=before_agent_callback,
            after_agent_callback=after_agent_callback,
        )
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Execute the Dev → Tester → QA loop with smart routing.
        
        Routing Logic:
        - If Dev fails: Exit with failure (likely spec issue)
        - If Tester.needs_dev_fix: Skip QA, route back to Dev with test summary
        - If Tester.needs_spec_clarification: Exit and escalate
        - If QA fails: Route back to Dev
        - If retry_count >= MAX_TOTAL_RETRIES: Exit and escalate
        
        Note: before_agent_callback and after_agent_callback are handled
        automatically by the ADK framework (BaseAgent.run_async).
        
        The loop extracts TestReport and DevReport from results after completion
        for persistence by the orchestrator.
        """
        state = ctx.session.state
        
        # Note: before_agent_callback is called automatically by BaseAgent.run_async
        # before _run_async_impl is invoked
        
        # Get artifact from state (may have been injected by before_agent_callback)
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
        
        
        # Initialize counters
        state[STATE_KEY_LOOP_ITERATION] = 0
        state[STATE_KEY_RETRY_COUNT] = state.get(STATE_KEY_RETRY_COUNT, 0)
        
        for iteration in range(1, self.max_iterations + 1):
            state[STATE_KEY_LOOP_ITERATION] = iteration
            retry_count = state.get(STATE_KEY_RETRY_COUNT, 0)
            
            logger.info(
                f"Iteration {iteration}/{self.max_iterations} for {artifact_id} (retries={retry_count})",
                extra={"agent": self.name, "iteration": iteration, "retry_count": retry_count}
            )
            
            # --- CHECK RETRY LIMIT ---
            if retry_count >= MAX_TOTAL_RETRIES:
                logger.warning(f"[{artifact_id}] Max retries ({MAX_TOTAL_RETRIES}) reached - escalating")
                state[STATE_KEY_LOOP_RESULT] = "escalate"
                state[STATE_KEY_ESCALATION_REASON] = "max_retries"
                state[STATE_KEY_LOOP_ERROR] = f"Max retries ({MAX_TOTAL_RETRIES}) reached"
                yield self._create_status_event(f"ESCALATE: {artifact_id} - max retries reached")
                return
            
            # --- DEV PHASE ---
            logger.info(f"[{artifact_id}] Running Dev Agent...")
            async for event in self.dev_agent.run_async(ctx):
                yield event
            
            dev_result = state.get(STATE_KEY_DEV_RESULT)
            
            # Persist DevReport to disk
            dev_report_path = _persist_dev_report(state, dev_result, artifact_id)
            if dev_report_path:
                state[STATE_KEY_DEV_REPORT_PATH] = dev_report_path
            
            if not self._check_dev_success(dev_result):
                logger.warning(f"[{artifact_id}] Dev Agent failed - exiting loop")
                state[STATE_KEY_LOOP_RESULT] = "fail"
                state[STATE_KEY_LOOP_ERROR] = "Dev Agent failed to implement"
                yield self._create_status_event(f"Dev failed for {artifact_id}")
                return
            
            # --- TESTER PHASE ---
            # Pass previous test summary to Tester if this is a retry
            if iteration > 1:
                prev_tester = state.get(STATE_KEY_TESTER_RESULT)
                if prev_tester:
                    state[STATE_KEY_PREVIOUS_TEST_SUMMARY] = self._extract_test_summary(prev_tester)
            
            logger.info(f"[{artifact_id}] Running Tester Agent...")
            async for event in self.tester_agent.run_async(ctx):
                yield event
            
            tester_result = state.get(STATE_KEY_TESTER_RESULT)
            
            # Persist TestReport to disk
            test_report_path = _persist_test_report(state, tester_result, artifact_id)
            if test_report_path:
                state[STATE_KEY_TEST_REPORT_PATH] = test_report_path
            
            # Check for spec clarification escalation
            if self._needs_spec_clarification(tester_result):
                logger.warning(f"[{artifact_id}] Tester needs spec clarification - escalating")
                state[STATE_KEY_LOOP_RESULT] = "escalate"
                state[STATE_KEY_ESCALATION_REASON] = "spec_clarification"
                state[STATE_KEY_LOOP_ERROR] = "Tester flagged spec clarification needed"
                yield self._create_status_event(f"ESCALATE: {artifact_id} - spec clarification needed")
                return
            
            # Check for dev fix needed (skip QA, route back to Dev)
            if self._needs_dev_fix(tester_result):
                logger.info(f"[{artifact_id}] Tests failed, needs dev fix - routing back to Dev")
                state[STATE_KEY_RETRY_COUNT] = retry_count + 1
                # Store test summary for next Dev iteration
                state[STATE_KEY_PREVIOUS_TEST_SUMMARY] = self._extract_test_summary(tester_result)
                yield self._create_status_event(
                    f"Tests failed for {artifact_id}, routing back to Dev (retry {retry_count + 1})"
                )
                continue
            
            # Check for tester failure without needs_dev_fix
            if not self._check_tester_success(tester_result):
                logger.info(f"[{artifact_id}] Tester failed - routing back to Dev")
                state[STATE_KEY_RETRY_COUNT] = retry_count + 1
                state[STATE_KEY_PREVIOUS_TEST_SUMMARY] = self._extract_test_summary(tester_result)
                yield self._create_status_event(
                    f"Tests failed for {artifact_id}, routing back to Dev (retry {retry_count + 1})"
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
                    state[STATE_KEY_RETRY_COUNT] = retry_count + 1
                    yield self._create_status_event(
                        f"QA failed for {artifact_id}, routing back to Dev (retry {retry_count + 1})"
                    )
                    continue
            
            # --- SUCCESS ---
            logger.info(f"[{artifact_id}] Loop completed successfully!")
            state[STATE_KEY_LOOP_RESULT] = "pass"
            self._append_dev_summary_to_state(state, dev_result, artifact_id)
            
            # Note: after_agent_callback is called automatically by BaseAgent.run_async
            # after _run_async_impl completes
            
            yield self._create_status_event(
                f"SUCCESS: {artifact_id} completed in {iteration} iteration(s)"
            )
            return
        
        # --- MAX ITERATIONS REACHED ---
        logger.warning(f"[{artifact_id}] Max iterations ({self.max_iterations}) reached - escalating")
        state[STATE_KEY_LOOP_RESULT] = "escalate"
        state[STATE_KEY_ESCALATION_REASON] = "max_iterations"
        state[STATE_KEY_LOOP_ERROR] = f"Max iterations ({self.max_iterations}) reached"
        yield self._create_status_event(f"ESCALATE: {artifact_id} - max iterations reached")
    
    def _check_dev_success(self, dev_result: dict | BackendDevResult | None) -> bool:
        """Check if Dev Agent succeeded (status='success')."""
        if dev_result is None:
            return False
        if isinstance(dev_result, dict):
            return dev_result.get("status") == "success"
        return dev_result.status == "success"
    
    def _check_tester_success(self, tester_result: dict | TestAgentResult | None) -> bool:
        """
        Check if Tester Agent succeeded (status='success' and not needs_dev_fix).
        
        TestAgentResult has:
        - status: 'success' | 'failed' | 'partial'
        - needs_dev_fix: bool (if True, route back to Dev)
        - needs_spec_clarification: bool (if True, escalate)
        """
        if tester_result is None:
            return False
        if isinstance(tester_result, dict):
            status = tester_result.get("status")
            needs_dev_fix = tester_result.get("needs_dev_fix", False)
            return status == "success" and not needs_dev_fix
        return tester_result.status == "success" and not tester_result.needs_dev_fix
    
    def _needs_dev_fix(self, tester_result: dict | TestAgentResult | None) -> bool:
        """Check if Tester flagged that dev fix is needed."""
        if tester_result is None:
            return False
        if isinstance(tester_result, dict):
            return tester_result.get("needs_dev_fix", False)
        return tester_result.needs_dev_fix
    
    def _needs_spec_clarification(self, tester_result: dict | TestAgentResult | None) -> bool:
        """Check if Tester flagged that spec clarification is needed (escalate)."""
        if tester_result is None:
            return False
        if isinstance(tester_result, dict):
            return tester_result.get("needs_spec_clarification", False)
        return tester_result.needs_spec_clarification
    
    def _extract_test_summary(self, tester_result: dict | TestAgentResult | None) -> str:
        """Extract summary from tester result for passing to next Dev iteration."""
        if tester_result is None:
            return "(no previous test run)"
        
        if isinstance(tester_result, dict):
            summary = tester_result.get("summary", "")
            test_report = tester_result.get("test_report", {})
            if isinstance(test_report, dict):
                # Try new nested structure first (execution.tests_failed, etc.)
                execution = test_report.get("execution", {})
                if isinstance(execution, dict):
                    tests_failed = execution.get("tests_failed", 0)
                    failed_tests = execution.get("failed_test_names", [])
                    output_snippet = execution.get("output_snippet", "")
                else:
                    # Fallback to legacy flat structure
                    tests_failed = test_report.get("tests_failed", 0)
                    failed_tests = test_report.get("failed_test_names", [])
                    output_snippet = test_report.get("output_snippet", "")
                
                parts = [summary] if summary else []
                if tests_failed > 0:
                    parts.append(f"Failed tests ({tests_failed}): {', '.join(failed_tests[:5])}")
                if output_snippet:
                    parts.append(f"Output: {output_snippet[:300]}")
                return " | ".join(parts) if parts else "(test summary unavailable)"
            return summary or "(test summary unavailable)"
        
        # Pydantic model (TestAgentResult)
        parts = [tester_result.summary] if tester_result.summary else []
        if tester_result.test_report:
            tr = tester_result.test_report
            # Try new nested structure first
            if tr.execution:
                if tr.execution.tests_failed > 0:
                    parts.append(f"Failed tests ({tr.execution.tests_failed}): {', '.join(tr.execution.failed_test_names[:5])}")
                if tr.execution.output_snippet:
                    parts.append(f"Output: {tr.execution.output_snippet[:300]}")
            # Fallback to legacy fields
            elif tr.tests_failed > 0:
                parts.append(f"Failed tests ({tr.tests_failed}): {', '.join(tr.failed_test_names[:5])}")
                if tr.output_snippet:
                    parts.append(f"Output: {tr.output_snippet[:300]}")
        return " | ".join(parts) if parts else "(test summary unavailable)"
    
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
    max_iterations: int = MAX_ITERATIONS,
) -> BackendDevLoopAgent:
    """
    Create a Backend Dev Loop Agent.
    
    Args:
        dev_agent: Custom Dev Agent (uses default if None)
        tester_agent: Custom Tester Agent (uses default if None)
        qa_agent: Custom QA Agent (uses default if None)
        max_iterations: Max loop iterations before escalation
        use_default_callbacks: If True, use before_agent_callback and after_agent_callback
            for standalone testing and manifest persistence
            
    Returns:
        Configured BackendDevLoopAgent
    """
    
    return BackendDevLoopAgent(
        name="backend_loop",
        dev_agent=create_backend_dev_agent(),
        tester_agent=create_tester_agent(),
        qa_agent=create_qa_agent(),
        max_iterations=max_iterations,
        before_agent_callback=before_loop_callback,
        after_agent_callback=after_loop_callback,
    )


def get_loop_agent() -> BackendDevLoopAgent:
    """
    Get a configured Loop Agent instance with default sub-agents and callbacks.
    
    Uses ADK built-in before_agent_callback / after_agent_callback for:
    - Standalone testing (artifact injection from backend_todos.json)
    - Manifest persistence (write BackendManifestEntry on success)
    """
    return create_loop_agent()


__all__ = [
    "BackendDevLoopAgent",
    "create_loop_agent",
    "get_loop_agent",
    "create_qa_agent",
    "QAResult",
    "SUB_AGENT_MODEL",
    "MAX_ITERATIONS",
    "MAX_TOTAL_RETRIES",
    # Callbacks (exposed for custom usage)
    "before_loop_callback",
    "after_loop_callback",
]

