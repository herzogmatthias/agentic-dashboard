import asyncio
import inspect
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.agents.data_analysis.agent import create_data_analysis_agent
from src.agents.planner.agent import create_planner_agent
from src.prompts.user_prompts import build_planner_handoff_message

from ..core.config import APP_NAME, USER_ID
from ..core.daytona_client import DaytonaSandboxSingleton
from ..core.state import SharedSessionState, _bootstrap_run_directory



def _print_final_response(event) -> None:
    if not event.is_final_response() or not event.content:
        return
    text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
    if text_parts:
        print("Agent:", "\n".join(text_parts))
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
    run_id, run_dir = _bootstrap_run_directory()
    session_state = SharedSessionState.bootstrap(run_id=run_id, run_dir=run_dir)

    agent = create_data_analysis_agent()
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)

    create_session_kwargs = {"app_name": APP_NAME, "user_id": USER_ID}
    try:
        create_session_sig = inspect.signature(runner.session_service.create_session)
        params = create_session_sig.parameters
        if "session_state" in params:
            create_session_kwargs["session_state"] = session_state.model_dump()
        elif "state" in params:
            create_session_kwargs["state"] = session_state.model_dump()
    except Exception:
        create_session_kwargs["session_state"] = session_state.model_dump()

    session = await runner.session_service.create_session(**create_session_kwargs)
    if not getattr(session, "state", None):
        try:
            session.state = session_state.model_dump()
        except Exception:
            pass

    print(f"Data Analysis Agent ready. Run dir: {run_dir}  Type 'exit' to quit.\n")

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
