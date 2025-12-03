"""Backend Agent package for creating Next.js API routes."""

from src.agents.backend.agent import (
    create_backend_agent,
    get_backend_agent,
    initialize_backend_state,
    backend_instruction_provider,
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_DATA_PROFILE_PATH,
    STATE_KEY_DASHBOARD_SPEC_PATH,
    STATE_KEY_CLEANED_DATA_FILES,
    STATE_KEY_CLEANED_DATA_PATH,
    DEFAULT_TEST_RUN_DIR,
)
from src.agents.backend.prompts import build_backend_agent_prompt
from src.models.backend_manifest import (
    ApiError,
    BackendManifest,
    BackendStatus,
    DataSourceInfo,
    ModelInfo,
    QueryParam,
    RouteInfo,
    ValidationResult,
    API_ERROR_TYPESCRIPT,
)

__all__ = [
    # Agent creation
    "create_backend_agent",
    "get_backend_agent",
    "initialize_backend_state",
    "backend_instruction_provider",
    # Prompt
    "build_backend_agent_prompt",
    # State keys
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_DATA_PROFILE_PATH",
    "STATE_KEY_DASHBOARD_SPEC_PATH",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_CLEANED_DATA_PATH",
    "DEFAULT_TEST_RUN_DIR",
    # Schema models
    "ApiError",
    "BackendManifest",
    "BackendStatus",
    "DataSourceInfo",
    "ModelInfo",
    "QueryParam",
    "RouteInfo",
    "ValidationResult",
    "API_ERROR_TYPESCRIPT",
]
