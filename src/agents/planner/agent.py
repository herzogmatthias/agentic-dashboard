from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from phoenix.otel import register as register_phoenix

from src.prompts.system_prompts import build_planner_agent_prompt
from src.tools.planner import create_dashboard_tool


tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)


def create_planner_agent() -> LlmAgent:
    model = LiteLlm(model="gpt-5-mini")

    agent = LlmAgent(
        name="planner_agent",
        model=model,
        instruction=build_planner_agent_prompt(),
        tools=[
            create_dashboard_tool
        ],
        description="Profiles, cleans, and exports dataset artifacts using a Daytona sandbox.",
    )

    return agent
