"""
Backend Custom Agent with continuation capabilities.

This module provides a custom agent wrapper that can automatically retry
when the underlying LLM agent returns an empty or faulty response.

Faulty responses include:
- Empty responses (no content)
- Responses with /*ACTION*/ marker but no actual function_calls
"""

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types as gt
from pydantic import Field
from typing_extensions import override

from src.core.logging import get_logger
from src.agents.backend.callbacks import (
    STATE_KEY_CONTINUATION_COUNT,
    MAX_CONTINUATION_ATTEMPTS,
)

logger = get_logger(__name__)

# PlanReAct tags for detection
ACTION_TAG = "/*ACTION*/"


def has_action_marker(content: gt.Content) -> bool:
    """
    Check if content contains the /*ACTION*/ marker in text parts.
    
    Args:
        content: The content to check
        
    Returns:
        True if any text part contains /*ACTION*/
    """
    if not content or not content.parts:
        return False
    
    for part in content.parts:
        if hasattr(part, 'text') and part.text and ACTION_TAG in part.text:
            return True
    return False


def has_function_calls(content: gt.Content) -> bool:
    """
    Check if content contains any function_call parts.
    
    Args:
        content: The content to check
        
    Returns:
        True if any part has a function_call
    """
    if not content or not content.parts:
        return False
    
    for part in content.parts:
        if hasattr(part, 'function_call') and part.function_call:
            return True
    return False


def is_response_faulty(content: gt.Content) -> tuple[bool, str]:
    """
    Check if a response is faulty and needs continuation.
    
    A response is faulty if:
    1. It's empty (no content or empty parts)
    2. It has /*ACTION*/ marker but no function_calls
    
    Args:
        content: The content to check
        
    Returns:
        Tuple of (is_faulty, reason)
    """
    # Check for empty response
    if not content or not content.parts:
        return True, "empty_response"
    
    # Check all parts are empty
    all_empty = True
    for part in content.parts:
        has_text = hasattr(part, 'text') and part.text and part.text.strip()
        has_fc = hasattr(part, 'function_call') and part.function_call
        has_fr = hasattr(part, 'function_response') and part.function_response
        if has_text or has_fc or has_fr:
            all_empty = False
            break
    
    if all_empty:
        return True, "empty_parts"
    
    # Check for ACTION marker without function calls
    if has_action_marker(content) and not has_function_calls(content):
        return True, "action_without_function_call"
    
    return False, ""


class BackendAgentWithContinuation(BaseAgent):
    """
    Custom agent that wraps the Backend LlmAgent with automatic continuation.
    
    When the underlying LLM returns an empty response, this agent will:
    1. Detect the empty response
    2. Inject a continuation prompt as a user message
    3. Re-run the LLM agent
    4. Repeat until a valid response is received or max attempts reached
    
    This uses ADK's custom agent pattern to implement retry logic that
    isn't possible with callbacks alone.
    """
    
    # Pydantic field declarations
    llm_agent: LlmAgent = Field(description="The underlying LLM agent")
    max_continuations: int = Field(
        default=MAX_CONTINUATION_ATTEMPTS,
        description="Maximum number of continuation attempts"
    )
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(
        self,
        name: str,
        llm_agent: LlmAgent,
        max_continuations: int = MAX_CONTINUATION_ATTEMPTS,
        **kwargs,
    ):
        """
        Initialize the custom agent.
        
        Args:
            name: Name of this agent
            llm_agent: The underlying Backend LlmAgent to wrap
            max_continuations: Maximum continuation attempts on empty responses
        """
        # Pydantic BaseModel needs all fields passed through super().__init__()
        super().__init__(
            name=name,
            llm_agent=llm_agent,
            max_continuations=max_continuations,
            sub_agents=[llm_agent],
            **kwargs,
        )
    
    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Execute the agent with automatic continuation on faulty responses.
        
        This method:
        1. Runs the underlying LLM agent
        2. Checks if the response is faulty (empty or ACTION without function_call)
        3. If faulty and under max attempts, injects continuation and retries
        4. Yields all events from the underlying agent
        
        Args:
            ctx: The invocation context
            
        Yields:
            Events from the underlying agent execution
        """
        continuation_count = ctx.session.state.get(STATE_KEY_CONTINUATION_COUNT, 0)
        
        logger.info(
            f"[{self.name}] Starting backend agent execution",
            extra={"continuation_count": continuation_count}
        )
        
        # Track the last response to check for faulty
        last_event: Event | None = None
        response_is_faulty = False
        fault_reason = ""
        
        # Run the underlying LLM agent
        async for event in self.llm_agent.run_async(ctx):
            last_event = event
            yield event
            
            # Check if this is a model response event
            if event.content and event.author == self.llm_agent.name:
                response_is_faulty, fault_reason = is_response_faulty(event.content)
        
        # If response was faulty and we have attempts left, try continuation
        if response_is_faulty and continuation_count < self.max_continuations:
            continuation_count += 1
            ctx.session.state[STATE_KEY_CONTINUATION_COUNT] = continuation_count
            
            # Build continuation message based on fault reason
            if fault_reason == "action_without_function_call":
                continuation_msg = (
                    "Your previous response indicated an action (/*ACTION*/) but did not include "
                    "any function calls. Please execute the action by calling the appropriate tool. "
                    f"(Continuation attempt {continuation_count}/{self.max_continuations})"
                )
            else:
                continuation_msg = (
                    "Your previous response was empty. Please continue with the backend implementation. "
                    f"(Continuation attempt {continuation_count}/{self.max_continuations})"
                )
            
            logger.warning(
                f"[{self.name}] Faulty response detected ({fault_reason}), attempting continuation "
                f"({continuation_count}/{self.max_continuations})",
                extra={"attempt": continuation_count, "fault_reason": fault_reason}
            )
            
            # Add continuation message to session history (not yielded - internal only)
            # This makes the LLM see the prompt but doesn't display it as a chat bubble
            continuation_content = gt.Content(
                role="user",
                parts=[gt.Part.from_text(text=continuation_msg)],
            )
            ctx.session.events.append(Event(
                invocation_id=ctx.invocation_id,
                author="user",
                branch=ctx.branch,
                content=continuation_content,
            ))
            
            # Re-run LLM agent - it will see the continuation message in history
            logger.info(
                f"[{self.name}] Re-running LLM agent after continuation prompt",
                extra={"attempt": continuation_count}
            )
            
            async for event in self.llm_agent.run_async(ctx):
                yield event
        
        elif response_is_faulty:
            logger.error(
                f"[{self.name}] Max continuation attempts ({self.max_continuations}) reached, giving up",
                extra={"attempts": continuation_count, "fault_reason": fault_reason}
            )
            
            # Yield an error message event
            error_content = gt.Content(
                role="model",
                parts=[gt.Part.from_text(
                    text="I apologize, but I'm having trouble generating a valid response after multiple attempts. "
                         f"The issue was: {fault_reason}. "
                         "Please try again or contact support if this persists."
                )],
            )
            
            error_event = Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=error_content,
            )
            yield error_event
        else:
            # Reset continuation count on successful response
            ctx.session.state[STATE_KEY_CONTINUATION_COUNT] = 0
            logger.info(
                f"[{self.name}] Backend agent completed successfully",
                extra={"had_continuations": continuation_count > 0}
            )
