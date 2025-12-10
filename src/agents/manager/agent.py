"""
Manager Agent - Custom BaseAgent for orchestrating dashboard building.

This agent implements the streaming sub-agent pattern where:
1. The orchestrator runs and can call delegation tools
2. Delegation tools are intercepted and routed to the appropriate sub-agent
3. Sub-agents run, stream events, and their final output is captured
4. A synthetic tool response is created with the sub-agent's result
5. Control returns to the orchestrator with the result
"""

import logging
from pathlib import Path
import shutil
from typing import AsyncGenerator, Optional, Any, List

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions
from google.genai import types as gt

from src.agents.data_analysis.agent import create_data_analysis_agent
from src.agents.manager.state import STATE_KEY_CLEANED_DATASET_PATH, STATE_KEY_DATASET_PATH, STATE_KEY_ORIGINAL_DATASET_PATH, STATE_KEY_RUN_DIR, STATE_KEY_RUN_ID, STATE_KEY_USER_GOALS
from src.agents.orchestrator.agent import create_orchestrator_agent
from src.agents.planner.agent import create_planner_agent
from src.core.config import SANDBOX_CLEANED_CSV_PATH, SANDBOX_CSV_PATH
from src.core.state import _bootstrap_run_directory
from src.core.logging import get_logger

logger = get_logger(__name__)




def initialize_state_callback(callback_context: CallbackContext) -> Optional[gt.Content]:
    """
    Initialize session state on first run.
    
    This is a before_agent_callback that uses CallbackContext.state for proper
    state management. Changes made to callback_context.state are automatically
    tracked and persisted via the ADK event system.
    
    Args:
        callback_context: The callback context with proper state access
        
    Returns:
        None to allow normal agent execution to proceed
    """
    try:
        state = callback_context.state
        
        # Initialize run_id and run_dir if not present
        if STATE_KEY_RUN_ID not in state or STATE_KEY_RUN_DIR not in state:
            run_id, run_dir = _bootstrap_run_directory()
            state[STATE_KEY_RUN_ID] = run_id
            state[STATE_KEY_RUN_DIR] = str(run_dir)
            logger.info(
                f"Created new run: {run_id} at {run_dir}",
                extra={"agent": "manager", "phase": "init", "run_id": run_id}
            )
        
        # Initialize user_goals if not present
        if STATE_KEY_USER_GOALS not in state:
            state[STATE_KEY_USER_GOALS] = {
                "goal": None,
                "audience": None,
                "use_case": None,
                "constraints": []
            }
        
        shutil.copytree("C:\\Users\\darks\\Documents\\agentic-dashboard\\agentic-dashboard\\data\\additional_info", state[STATE_KEY_RUN_DIR] + "\\additional_info", dirs_exist_ok=True) 
        logger.info(
            "Copied additional_info to run directory",
            extra={"agent": "manager", "phase": "init"}
        )
        # Initialize dataset paths
        if STATE_KEY_DATASET_PATH not in state:
            state[STATE_KEY_DATASET_PATH] = None
        if STATE_KEY_ORIGINAL_DATASET_PATH not in state:
            state[STATE_KEY_ORIGINAL_DATASET_PATH] = SANDBOX_CSV_PATH
        if STATE_KEY_CLEANED_DATASET_PATH not in state:
            state[STATE_KEY_CLEANED_DATASET_PATH] = SANDBOX_CLEANED_CSV_PATH
            
    except Exception as e:
        logger.exception(
            f"Failed to initialize state: {e}",
            extra={"agent": "manager", "phase": "init"}
        )
    
    # Return None to allow normal agent execution
    return None


class ManagerAgent(BaseAgent):
    """
    Custom Manager Agent that coordinates orchestrator and sub-agents.
    
    This is the root entry point for the dashboard building system.
    It intercepts delegation tool calls from the orchestrator and routes
    them to the appropriate sub-agents (data_analysis, planner).
    
    The pattern:
    1. Run orchestrator until it calls a delegation tool or gives final response
    2. If delegation tool called, extract task and route to sub-agent
    3. Run sub-agent, capture final output
    4. Create synthetic FunctionResponse with sub-agent result
    5. Append to session and continue orchestrator loop
    """
    
    orchestrator: LlmAgent
    data_analysis_agent: LlmAgent
    planner_agent: LlmAgent
    before_agent_callback: Optional[Any] = None
    
    def __init__(
        self,
        orchestrator: LlmAgent,
        data_analysis_agent: LlmAgent,
        planner_agent: LlmAgent,
        before_agent_callback: Optional[Any] = None,
    ):
        super().__init__(
            name="manager",
            orchestrator=orchestrator,
            data_analysis_agent=data_analysis_agent,
            planner_agent=planner_agent,
            sub_agents=[orchestrator, data_analysis_agent, planner_agent],
            before_agent_callback=before_agent_callback,
        )
    
    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        """
        Main execution loop implementing the streaming sub-agent pattern.
        
        State initialization is handled at the start via initialize_state_callback
        which uses CallbackContext.state for proper ADK state tracking.
        """
        
        # Tools we intercept and route to sub-agents
        managed_tools = {"delegate_data_analysis", "delegate_planner"}
        keep_looping = True
        
        while keep_looping and not ctx.end_invocation:
            tool_call = None
            
            # ---------- STEP 1: Run orchestrator (user-facing) ----------
            agen = self.orchestrator.run_async(ctx)
            try:
                async for event in agen:
                    yield event
                    function_calls = event.get_function_calls()
                    
                    if function_calls:
                        # Check if any function call is one we manage
                        chosen: Optional[Any] = None
                        for fc in function_calls:
                            if fc.name in managed_tools:
                                chosen = fc
                                break
                        
                        if chosen is not None:
                            # Intercept our delegation tools
                            tool_call = chosen
                            break
                        
                        # Other tools (read_state, validate_dataset, etc.) are handled by ADK
                        continue
                    
                    if event.is_final_response():
                        keep_looping = False
                        break
            finally:
                await agen.aclose()
            
            # If orchestrator didn't call a delegation tool, we're done
            if not tool_call:
                break
            
            # ---------- STEP 2: Dispatch to sub-agent ----------
            tool_name = tool_call.name
            args = tool_call.args or {}
            
            # Extract task description from tool arguments
            task_description = args.get("task_description", "")
            
            if tool_name == "delegate_data_analysis":
                task_state_key = "data_analysis_task"
                worker = self.data_analysis_agent
                logger.info(
                    "Delegating to Data Analysis Agent",
                    extra={"agent": "manager", "phase": "delegate", "task": task_description[:100]}
                )
            elif tool_name == "delegate_planner":
                task_state_key = "planner_task"
                worker = self.planner_agent
                logger.info(
                    "Delegating to Planner Agent",
                    extra={"agent": "manager", "phase": "delegate", "task": task_description[:100]}
                )
            else:
                # Shouldn't happen, but be defensive
                keep_looping = False
                break
            
            # Store task in state via EventActions (proper state management)
            state_update_event = Event(
                author=self.name,
                actions=EventActions(state_delta={task_state_key: task_description}),
            )
            await ctx.session_service.append_event(
                session=ctx.session,
                event=state_update_event,
            )
            
            # ---------- STEP 3: Run sub-agent and capture output ----------
            final_response_text = ""
            worker_gen = worker.run_async(ctx)
            
            async for w_event in worker_gen:
                # Stream worker output to UI
                yield w_event
                
                # Capture final response text
                if w_event.is_final_response() and w_event.content and w_event.content.parts:
                    text_parts = [
                        p.text for p in w_event.content.parts
                        if hasattr(p, 'text') and p.text is not None
                    ]
                    if text_parts:
                        final_response_text = "\n".join(text_parts)
            
            worker_output = final_response_text.strip() or "Sub-agent completed successfully."
            
            # ---------- STEP 4: Create synthetic FunctionResponse ----------
            function_response = gt.FunctionResponse(
                id=tool_call.id,
                name=tool_name,
                response={"result": worker_output},
            )
            
            tool_content = gt.Content(
                role="tool",
                parts=[gt.Part(function_response=function_response)],
            )
            
            synthetic_event = Event(
                author=self.orchestrator.name,
                content=tool_content,
            )
            
            await ctx.session_service.append_event(
                session=ctx.session,
                event=synthetic_event,
            )
            
            logger.info(
                "Sub-agent completed, returning to orchestrator",
                extra={"agent": "manager", "phase": "return", "sub_agent": worker.name}
            )


def create_manager_agent() -> ManagerAgent:
    """
    Create and return the ManagerAgent with all sub-agents configured.
    
    State initialization is handled directly in the ManagerAgent's _run_async_impl
    using CallbackContext for proper ADK state tracking.
    
    Returns:
        ManagerAgent: The root agent for the dashboard building system
    """
    orchestrator = create_orchestrator_agent()
    data_analysis_agent = create_data_analysis_agent()
    planner_agent = create_planner_agent()
    
    return ManagerAgent(
        orchestrator=orchestrator,
        data_analysis_agent=data_analysis_agent,
        planner_agent=planner_agent,
        before_agent_callback=initialize_state_callback,
    )


# Export as root_agent for ADK compatibility
root_agent = None  # Will be lazily created


def get_root_agent() -> ManagerAgent:
    """Get or create the root manager agent."""
    global root_agent
    if root_agent is None:
        root_agent = create_manager_agent()
    return root_agent
