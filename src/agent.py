from src.agents.manager.agent import create_manager_agent
from src.agents.orchestrator.agent import create_orchestrator_agent
from src.agents.data_analysis.agent import create_data_analysis_agent


# Root agent for Google ADK - the main entry point
root_agent = create_manager_agent()
