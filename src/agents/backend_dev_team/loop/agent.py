"""
Backend Dev Loop Agent - Iterates through all backend todos and runs Dev Agent.

This loop processes all pending artifacts from the backend todo list:
1. Load backend_todo_list from state
2. For each pending artifact:
   - Run Dev Agent (including lint/type-check)
   - Update artifact status (success/failed) in todo list
   - Persist manifest entry from DevReport
3. On first failure: escalate with error message and break

Flow:
    Load todos → For each pending artifact: Dev Agent → Update status → Check result
    If failed: escalate and break. If success: continue to next.
    
Callbacks (uses ADK built-in before_agent_callback / after_agent_callback):
- before_agent_callback: Initialize run_dir and load todos if not present
- after_agent_callback: Persist manifest entry after each artifact completes
"""

import json
from pathlib import Path
from typing import AsyncGenerator, Optional, Any
from datetime import datetime

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types as gt

from src.core.logging import get_logger
from src.agents.backend_dev_team.loop.tools import (
    MAX_ITERATIONS,
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_CURRENT_GROUP,
    STATE_KEY_LOOP_RESULT,
    STATE_KEY_LOOP_ITERATION,
    STATE_KEY_LOOP_ERROR,
    STATE_KEY_DEV_REPORT_PATH,
    STATE_KEY_RUN_DIR,
    STATE_KEY_BACKEND_TODO_LIST,
    STATE_KEY_ACCESSIBLE_FILES,
    build_accessible_files_list,
)
from src.agents.backend_dev_team.loop.callbacks import (
    before_loop_callback,
    after_loop_callback,
    persist_artifact_manifest_entry,
    STATE_KEY_PREVIOUS_SUMMARIES,
    STATE_KEY_WORKSPACE_ROOT,
    STATE_KEY_METRICS_REF_CONTEXT,
    STATE_KEY_CLEANED_DATA_FILES,
    _load_dashboard_concept,
    _lookup_metrics_ref,
    _get_cleaned_data_files,
)
from src.agents.backend_dev_team.dev import create_backend_dev_agent
from src.agents.backend_dev_team.dev.state import STATE_KEY_DEV_RESULT
from src.models.backend_dev import BackendDevResult

logger = get_logger(__name__)

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


# =============================================================================
# Custom Loop Agent
# =============================================================================

class BackendDevLoopAgent(BaseAgent):
    """
    Custom agent that iterates through all backend todos.

    Routing Logic:
    - Load pending artifacts from backend_todo_list in state
    - For each pending artifact:
      - Run Dev Agent once per artifact
      - Dev performs implementation plus lint/type-check via its tools
      - Update artifact status in todo list (success or failed)
      - Persist DevReport and manifest entry
    - On first failure: escalate with error message and stop
    - On success: continue to next artifact

    State Requirements (input):
        - run_dir: Path to run directory
        - backend_todo_list: List of PlannerArtifactTodo dicts with status
    
    State Output:
        - loop_result: "pass" (all done) or "fail" (escalated due to error)
        - loop_iteration: Number of artifacts processed
        - dev_result: Last Dev Agent output
        - escalation_reason: If failed, why escalation occurred
        - backend_todo_list: Updated with status for each processed artifact
    """
    
    dev_agent: LlmAgent
    max_iterations: int = MAX_ITERATIONS
    
    def __init__(
        self,
        dev_agent: LlmAgent,
        name: str = "backend_loop",
        max_iterations: int = MAX_ITERATIONS,
        before_agent_callback=None,
        after_agent_callback=None,
    ):
        """Initialize the Backend Dev Loop Agent."""
        super().__init__(
            name=name,
            dev_agent=dev_agent, #ignore lint error
            sub_agents=[dev_agent],
            before_agent_callback=before_agent_callback,
            after_agent_callback=after_agent_callback,
        )
        self.dev_agent = dev_agent
        self.max_iterations = max_iterations
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Iterate through all groups and their pending artifacts, running Dev Agent on each.
        Break and escalate on first failure.
        """
        state = ctx.session.state
        
        # Get todo list from state
        todo_list = state.get(STATE_KEY_BACKEND_TODO_LIST)
        if not todo_list:
            logger.error("No backend_todo_list in state - cannot proceed")
            state[STATE_KEY_LOOP_RESULT] = "fail"
            state[STATE_KEY_LOOP_ERROR] = "No backend_todo_list provided in state"
            yield self._create_status_event("Error: No backend todo list to process")
            return
        
        # Extract groups array (new structure)
        groups = todo_list.get("groups", [])
        if not groups:
            logger.error("No groups in backend_todo_list")
            state[STATE_KEY_LOOP_RESULT] = "fail"
            state[STATE_KEY_LOOP_ERROR] = "No groups in backend_todo_list"
            yield self._create_status_event("Error: No groups in todo list")
            return
        
        logger.info(
            f"Starting loop with {len(groups)} groups",
            extra={"agent": self.name, "group_count": len(groups)},
        )
        
        groups_processed = 0
        artifacts_processed = 0
        
        # Iterate through groups - Dev Agent processes one group at a time
        for group_idx, group in enumerate(groups, 1):
            group_id = group.get("id", "unknown")
            group_label = group.get("label", group_id)
            artifacts = group.get("artifacts", [])
            
            # Filter to only pending artifacts in this group
            pending_artifacts = [a for a in artifacts if a.get("status", "pending") == "pending"]
            
            if not pending_artifacts:
                logger.info(
                    f"[Group {group_idx}/{len(groups)}] Skipping group {group_label} - no pending artifacts",
                    extra={"agent": self.name, "group_id": group_id},
                )
                continue
            
            logger.info(
                f"[Group {group_idx}/{len(groups)}] Processing group: {group_label} ({len(pending_artifacts)} pending artifacts)",
                extra={"agent": self.name, "group_id": group_id, "artifact_count": len(pending_artifacts)},
            )
            
            # Inject the entire group into state for Dev Agent
            state[STATE_KEY_CURRENT_GROUP] = group
            state[STATE_KEY_CURRENT_ARTIFACT] = group  # For backward compat
            state[STATE_KEY_LOOP_ITERATION] = groups_processed + 1
            
            # Inject accessible files list into state
            run_dir = state.get(STATE_KEY_RUN_DIR)
            # Pass first artifact for context (all in same group share context)
            accessible_files = build_accessible_files_list(pending_artifacts[0], run_dir)
            state[STATE_KEY_ACCESSIBLE_FILES] = accessible_files
            
            # Inject metrics_ref context for the group (combine all metrics_refs)
            if run_dir:
                dashboard_concept = _load_dashboard_concept(run_dir)
                # Collect all unique metrics_refs in the group
                metrics_refs = list(set(a.get("metrics_ref") for a in pending_artifacts if a.get("metrics_ref")))
                if metrics_refs:
                    metrics_context_parts = []
                    for ref in metrics_refs:
                        ref_context = _lookup_metrics_ref(dashboard_concept, ref)
                        if ref_context and not ref_context.startswith("("):
                            metrics_context_parts.append(f"{ref}: {ref_context}")
                    state[STATE_KEY_METRICS_REF_CONTEXT] = "\n".join(metrics_context_parts) if metrics_context_parts else "(no metrics_ref specified)"
                else:
                    state[STATE_KEY_METRICS_REF_CONTEXT] = "(no metrics_ref specified)"
                state[STATE_KEY_CLEANED_DATA_FILES] = _get_cleaned_data_files(run_dir)
            else:
                state[STATE_KEY_METRICS_REF_CONTEXT] = "(no run_dir in state)"
                state[STATE_KEY_CLEANED_DATA_FILES] = []
            
            logger.debug(
                f"[{group_label}] State initialized - accessible files: {len(accessible_files)}, pending artifacts: {len(pending_artifacts)}",
                extra={
                    "group_id": group_id,
                    "accessible_file_count": len(accessible_files),
                    "pending_artifact_count": len(pending_artifacts),
                    "cleaned_files_count": len(state.get(STATE_KEY_CLEANED_DATA_FILES, [])),
                }
            )
            
            # Run Dev Agent for the entire group
            logger.info(f"[{group_label}] Running Dev Agent for group...")
            try:
                async for event in self.dev_agent.run_async(ctx):
                    yield event
            except Exception as e:
                logger.exception(f"[{group_label}] Dev Agent raised exception: {e}")
                # Mark all pending artifacts as failed
                for artifact in pending_artifacts:
                    artifact["status"] = "failed"
                state[STATE_KEY_LOOP_RESULT] = "fail"
                state[STATE_KEY_LOOP_ERROR] = f"Dev Agent failed for group {group_label}: {e}"
                yield self._create_status_event(f"ERROR: Dev Agent exception for group {group_label}")
                return
            
            # Get Dev Result
            dev_result = state.get(STATE_KEY_DEV_RESULT)
            dev_report_path = _persist_dev_report(state, dev_result, group_id)
            if dev_report_path:
                state[STATE_KEY_DEV_REPORT_PATH] = dev_report_path
            
            # Check if Dev succeeded
            if not self._check_dev_success(dev_result):
                logger.warning(f"[{group_label}] Dev Agent failed - escalating")
                # Mark all pending artifacts as failed
                for artifact in pending_artifacts:
                    artifact["status"] = "failed"
                state[STATE_KEY_LOOP_RESULT] = "fail"
                
                # Extract error from dev_result
                error_msg = "Dev Agent failed to implement group"
                if dev_result:
                    if isinstance(dev_result, dict):
                        error_msg = dev_result.get("summary", error_msg)
                    elif hasattr(dev_result, "summary"):
                        error_msg = dev_result.summary
                
                state[STATE_KEY_LOOP_ERROR] = f"Group {group_label} failed: {error_msg}"
                yield self._create_status_event(f"ESCALATION: Group {group_label} failed - {error_msg}")
                return
            
            # Update all artifacts in group to success
            for artifact in pending_artifacts:
                artifact["status"] = "done"
                artifact["updated_at"] = datetime.utcnow().isoformat()
                
                # Persist manifest entry for each artifact
                if run_dir:
                    persist_artifact_manifest_entry(run_dir, artifact, dev_result)
            
            # Append group summary to previous_summaries
            self._append_group_summary_to_state(state, dev_result, group_id, group_label, len(pending_artifacts))
            
            groups_processed += 1
            artifacts_processed += len(pending_artifacts)
            yield self._create_status_event(f"✓ Group {group_label} completed ({len(pending_artifacts)} artifacts)")
        
        # All groups processed successfully
        state[STATE_KEY_LOOP_RESULT] = "pass"
        state[STATE_KEY_LOOP_ITERATION] = groups_processed
        yield self._create_status_event(f"SUCCESS: Completed {artifacts_processed} artifacts across {len(groups)} groups")
        return
    
    def _check_dev_success(self, dev_result: dict | BackendDevResult | None) -> bool:
        """Check if Dev Agent succeeded (status='success')."""
        if dev_result is None:
            return False
        if isinstance(dev_result, dict):
            return dev_result.get("status") == "success"
        return dev_result.status == "success"
    
    def _append_dev_summary_to_state(
        self,
        state: dict,
        dev_result: dict | BackendDevResult | None,
        artifact_id: str,
    ) -> None:
        """Extract summary, exports, and code_path from DevReport and append to previous_summaries."""
        if dev_result is None:
            return
        
        summary = None
        exports = []
        code_path = None
        
        if isinstance(dev_result, dict):
            report = dev_result.get("report", {})
            if isinstance(report, dict):
                summary = report.get("summary")
                # Extract exports and code_path from current_state
                current_state = report.get("current_state", {})
                if isinstance(current_state, dict):
                    exports = current_state.get("exports", [])
                    code_path = current_state.get("code_path")
            if not summary:
                summary = dev_result.get("summary")
        elif hasattr(dev_result, "report") and dev_result.report:
            summary = dev_result.report.summary
            if hasattr(dev_result.report, "current_state") and dev_result.report.current_state:
                exports = getattr(dev_result.report.current_state, "exports", [])
                code_path = getattr(dev_result.report.current_state, "code_path", None)
        
        if not summary:
            summary = f"Completed {artifact_id}"
        
        # Format summary with exports if available
        summary_line = f"[{artifact_id}] {summary}"
        if code_path:
            summary_line += f" (file: {code_path})"
        if exports:
            exports_str = ", ".join(exports) if isinstance(exports, list) else str(exports)
            summary_line += f" [exports: {exports_str}]"
        
        if STATE_KEY_PREVIOUS_SUMMARIES not in state:
            state[STATE_KEY_PREVIOUS_SUMMARIES] = []
        
        state[STATE_KEY_PREVIOUS_SUMMARIES].append(summary_line)
    
    def _append_group_summary_to_state(
        self,
        state: dict,
        dev_result: dict | BackendDevResult | None,
        group_id: str,
        group_label: str,
        artifact_count: int,
    ) -> None:
        """Extract summary from DevReport for a group and append to previous_summaries."""
        if dev_result is None:
            return
        
        summary = None
        exports = []
        
        if isinstance(dev_result, dict):
            report = dev_result.get("report", {})
            if isinstance(report, dict):
                summary = report.get("summary")
                current_state = report.get("current_state", {})
                if isinstance(current_state, dict):
                    exports = current_state.get("exports", [])
            if not summary:
                summary = dev_result.get("summary")
        elif hasattr(dev_result, "report") and dev_result.report:
            summary = dev_result.report.summary
            if hasattr(dev_result.report, "current_state") and dev_result.report.current_state:
                exports = getattr(dev_result.report.current_state, "exports", [])
        
        if not summary:
            summary = f"Completed group {group_label} ({artifact_count} artifacts)"
        
        # Format summary with group info
        summary_line = f"[Group: {group_label}] {summary}"
        if exports:
            exports_str = ", ".join(exports) if isinstance(exports, list) else str(exports)
            summary_line += f" [exports: {exports_str}]"
        
        if STATE_KEY_PREVIOUS_SUMMARIES not in state:
            state[STATE_KEY_PREVIOUS_SUMMARIES] = []
        
        state[STATE_KEY_PREVIOUS_SUMMARIES].append(summary_line)
    
    
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
    
    Iterates through all pending artifacts in backend_todo_list:
    - Processes each in sequence
    - Updates status after each artifact (success or failed)
    - Breaks and escalates on first failure
    - Builds manifest entries after each successful artifact
    
    Args:
        max_iterations: Max iterations (not actively used; limited by todo_list length)
            
    Returns:
        Configured BackendDevLoopAgent with dev agent and callbacks
    """
    
    return BackendDevLoopAgent(
        name="backend_loop",
        dev_agent=create_backend_dev_agent(),
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
    "MAX_ITERATIONS",
    # Callbacks (exposed for custom usage)
    "before_loop_callback",
    "after_loop_callback",
]

