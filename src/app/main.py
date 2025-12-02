import asyncio
import inspect
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.agents.manager.agent import create_manager_agent
from src.prompts.user_prompts import build_planner_handoff_message

from ..core.config import APP_NAME, USER_ID
from ..core.daytona_client import DaytonaSandboxSingleton
from ..core.state import SharedSessionState, _bootstrap_run_directory
from ..core.logging import get_logger

logger = get_logger(__name__)



def _print_final_response(event) -> None:
    if not event.is_final_response() or not event.content:
        return
    text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
    if text_parts:
        response_text = "\n".join(text_parts)
        logger.info("Agent response", extra={"response_length": len(response_text)})
        print("Agent:", response_text)
        print()



def _resolve_artifact_path(run_dir: Path, filename: str) -> Path:
    """
    Prefer the per-run directory for artifacts; fall back to legacy artifacts/.
    """
    candidate = run_dir / filename
    if candidate.exists():
        return candidate
    return Path("artifacts") / filename


async def console_chat() -> None:
    # Note: The ManagerAgent will initialize run_id and run_dir in session state
    # We don't need to bootstrap here - just create the agent and let it handle state
    
    agent = create_manager_agent()
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)

    # Create session without pre-populating state - Manager will initialize
    create_session_kwargs = {"app_name": APP_NAME, "user_id": USER_ID}
    session = await runner.session_service.create_session(**create_session_kwargs)

    logger.info("Console chat initialized with ManagerAgent")
    print(f"Dashboard Builder ready. Type 'exit' to quit.\n")

    #
    # -------------------------------------------------------------
    # 1) SEND INITIAL HANDOFF MESSAGE (as if from Orchestrator)
    # -------------------------------------------------------------
    #

    # Example: inject whatever dynamic artifacts you want here
    # data_profile_path = _resolve_artifact_path(run_dir, "data_profile.md")
    # cleaning_summary_path = _resolve_artifact_path(run_dir, "cleaning_summary.md")

    # if not data_profile_path.exists():
    #     raise FileNotFoundError(f"Missing: {data_profile_path}")

    # if not cleaning_summary_path.exists():
    #     raise FileNotFoundError(f"Missing: {cleaning_summary_path}")

    # data_profile_md = data_profile_path.read_text(encoding="utf-8")
    # cleaning_summary_md = cleaning_summary_path.read_text(encoding="utf-8")
    # initial_message = build_planner_handoff_message(
    #     goal_description="Monitor credit card customer attrition and understand key behavioral drivers.",
    #     audience="managers",
    #     use_case="monitoring",
    #     constraints=[
    #         "Single-page dashboard.",
    #         "Keep it manager-friendly and not too technical.",
    #         "No more than 5–6 main visuals plus a few KPIs.",
    #     ],
    #     data_profile_md=data_profile_md,          # your string variable
    #     cleaning_summary_md=cleaning_summary_md,  # your string variable
    #     summary_artifacts_json="{}",
    # )

    # initial_content = genai_types.Content(
    #     role="user",
    #     parts=[genai_types.Part(text=initial_message)]
    # )

    # print(">>> Sending initial Orchestrator handoff to Planner...\n")

    # async for event in runner.run_async(
    #     user_id=USER_ID,
    #     session_id=session.id,
    #     new_message=initial_content,
    # ):
    #     _print_final_response(event)

    # print("\n--- Initial handoff complete. You can now chat manually. ---\n")

    #
    # -------------------------------------------------------------
    # 2) CONTINUE WITH NORMAL INTERACTIVE CHAT
    # -------------------------------------------------------------
    #

    try:
        while True:
            user_text = input("You: ").strip()
            if not user_text:
                continue
            if user_text.lower() in {"exit", "quit"}:
                break

            user_content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_text)]
            )

            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=session.id,
                new_message=user_content,
            ):
                _print_final_response(event)

    finally:
        DaytonaSandboxSingleton().stop_and_archive()

def main() -> None:
    asyncio.run(console_chat())


if __name__ == "__main__":
    main()
