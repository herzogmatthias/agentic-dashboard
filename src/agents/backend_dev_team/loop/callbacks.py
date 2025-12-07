"""
Loop Agent callbacks - State injection and initialization for testability.

These callbacks allow the Loop Agent (and its sub-agents) to:
1. Receive artifact context via state injection
2. Be tested independently with mocked state
"""

from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.genai import types as gt

from src.core.logging import get_logger
from src.agents.backend_dev_team.loop.tools import (
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_CURRENT_ARTIFACT_ID,
    STATE_KEY_LOOP_ITERATION,
    STATE_KEY_LOOP_RESULT,
    STATE_KEY_RUN_DIR,
    MAX_ITERATIONS,
)

logger = get_logger(__name__)


def initialize_loop_state(callback_context: CallbackContext) -> gt.Content | None:
    """
    Initialize/validate loop state before the LoopAgent runs.
    
    This callback:
    1. Validates that an artifact has been injected into state
    2. Initializes the iteration counter if not present
    
    For testing, inject state before running:
        state[STATE_KEY_CURRENT_ARTIFACT] = {"id": "test", ...}
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to allow normal execution, or Content to skip with error
    """
    try:
        state = callback_context.state
        
        # Check for current artifact
        artifact = state.get(STATE_KEY_CURRENT_ARTIFACT)
        if not artifact:
            logger.warning(
                "No artifact in state - loop cannot proceed",
                extra={"agent": "loop", "phase": "init"}
            )
            return gt.Content(
                role="model",
                parts=[gt.Part.from_text(
                    text="Error: No artifact provided. Inject artifact via state before running loop."
                )]
            )
        
        # Initialize iteration counter
        if STATE_KEY_LOOP_ITERATION not in state:
            state[STATE_KEY_LOOP_ITERATION] = 0
        
        artifact_id = artifact.get("id", "unknown")
        iteration = state[STATE_KEY_LOOP_ITERATION]
        
        logger.info(
            f"Loop initialized for artifact {artifact_id}, iteration {iteration}",
            extra={
                "agent": "loop",
                "phase": "init",
                "artifact_id": artifact_id,
                "iteration": iteration,
            }
        )
        
        return None
        
    except Exception as e:
        logger.exception(f"Failed to initialize loop state: {e}")
        return gt.Content(
            role="model",
            parts=[gt.Part.from_text(text=f"Error initializing loop: {e}")]
        )


def increment_loop_iteration(callback_context: CallbackContext) -> gt.Content | None:
    """
    Increment the loop iteration counter at the start of each cycle.
    
    This callback should be attached to the LoopAgent's before_agent_callback
    to track how many Dev→Tester→QA cycles have occurred.
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to continue, or Content to skip if max iterations reached
    """
    try:
        state = callback_context.state
        
        # Increment iteration
        iteration = state.get(STATE_KEY_LOOP_ITERATION, 0)
        iteration += 1
        state[STATE_KEY_LOOP_ITERATION] = iteration
        
        artifact = state.get(STATE_KEY_CURRENT_ARTIFACT, {})
        artifact_id = artifact.get("id", "unknown")
        
        logger.info(
            f"Loop iteration {iteration}/{MAX_ITERATIONS} for {artifact_id}",
            extra={
                "agent": "loop",
                "artifact_id": artifact_id,
                "iteration": iteration,
                "max_iterations": MAX_ITERATIONS,
            }
        )
        
        # Note: max_iterations is handled by LoopAgent itself, but we log it
        return None
        
    except Exception as e:
        logger.exception(f"Failed to increment loop iteration: {e}")
        return None


def after_loop_callback(callback_context: CallbackContext) -> gt.Content | None:
    """
    Callback that runs after the loop completes.
    
    This callback:
    1. Logs the final loop result
    2. Can modify the output if needed
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to use agent's output, or Content to replace it
    """
    try:
        state = callback_context.state
        
        artifact = state.get(STATE_KEY_CURRENT_ARTIFACT, {})
        artifact_id = artifact.get("id", "unknown")
        result = state.get(STATE_KEY_LOOP_RESULT, "unknown")
        iteration = state.get(STATE_KEY_LOOP_ITERATION, 0)
        
        logger.info(
            f"Loop completed for {artifact_id}: result={result}, iterations={iteration}",
            extra={
                "agent": "loop",
                "phase": "complete",
                "artifact_id": artifact_id,
                "result": result,
                "iterations": iteration,
            }
        )
        
        return None
        
    except Exception as e:
        logger.exception(f"Error in after_loop_callback: {e}")
        return None


# =============================================================================
# Sub-agent callbacks (for Dev, Tester, QA)
# =============================================================================

def inject_artifact_context_for_dev(callback_context: CallbackContext) -> gt.Content | None:
    """
    Inject artifact context for the Dev Agent.
    
    The Dev Agent needs the full artifact spec to implement it.
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to allow execution
    """
    state = callback_context.state
    artifact = state.get(STATE_KEY_CURRENT_ARTIFACT)
    
    if not artifact:
        logger.warning("Dev Agent: No artifact in state")
        return gt.Content(
            role="model",
            parts=[gt.Part.from_text(text="Error: No artifact to implement.")]
        )
    
    logger.debug(
        f"Dev Agent processing: {artifact.get('id')}",
        extra={"agent": "dev", "artifact_id": artifact.get("id")}
    )
    
    return None


def inject_artifact_context_for_tester(callback_context: CallbackContext) -> gt.Content | None:
    """
    Inject artifact context for the Tester Agent.
    
    The Tester Agent needs the artifact spec and Dev result to create tests.
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to allow execution
    """
    state = callback_context.state
    artifact = state.get(STATE_KEY_CURRENT_ARTIFACT)
    
    if not artifact:
        logger.warning("Tester Agent: No artifact in state")
        return gt.Content(
            role="model",
            parts=[gt.Part.from_text(text="Error: No artifact to test.")]
        )
    
    logger.debug(
        f"Tester Agent processing: {artifact.get('id')}",
        extra={"agent": "tester", "artifact_id": artifact.get("id")}
    )
    
    return None


def inject_artifact_context_for_qa(callback_context: CallbackContext) -> gt.Content | None:
    """
    Inject artifact context for the QA Agent.
    
    The QA Agent needs the artifact spec, Dev result, and Tester result to validate.
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to allow execution
    """
    state = callback_context.state
    artifact = state.get(STATE_KEY_CURRENT_ARTIFACT)
    
    if not artifact:
        logger.warning("QA Agent: No artifact in state")
        return gt.Content(
            role="model",
            parts=[gt.Part.from_text(text="Error: No artifact to validate.")]
        )
    
    logger.debug(
        f"QA Agent processing: {artifact.get('id')}",
        extra={"agent": "qa", "artifact_id": artifact.get("id")}
    )
    
    return None
