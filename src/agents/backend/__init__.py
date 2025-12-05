"""Backend Agent package for creating Next.js API routes."""

from src.agents.backend.agent import (
    create_backend_agent,
    create_backend_llm_agent,
    get_backend_agent,
    get_backend_llm_agent,
)
from src.agents.backend.callbacks import (
    inject_context_callback,
    initialize_backend_state,
    backend_instruction_provider,
    # State keys
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_DATA_PROFILE_PATH,
    STATE_KEY_DASHBOARD_SPEC_PATH,
    STATE_KEY_CLEANED_DATA_FILES,
    STATE_KEY_CLEANED_DATA_PATH,
    STATE_KEY_CONTINUATION_COUNT,
    DEFAULT_TEST_RUN_DIR,
    MAX_CONTINUATION_ATTEMPTS,
)
from src.agents.backend.custom_agent import BackendAgentWithContinuation
from src.agents.backend.utils import (
    get_cleaned_data_files,
    format_cleaned_files_for_prompt,
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
    "create_backend_llm_agent",
    "get_backend_agent",
    "get_backend_llm_agent",
    # Custom agent
    "BackendAgentWithContinuation",
    # Callbacks
    "inject_context_callback",
    "initialize_backend_state",
    "backend_instruction_provider",
    # Utilities
    "get_cleaned_data_files",
    "format_cleaned_files_for_prompt",
    # Prompt
    "build_backend_agent_prompt",
    # State keys
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_DATA_PROFILE_PATH",
    "STATE_KEY_DASHBOARD_SPEC_PATH",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_CLEANED_DATA_PATH",
    "STATE_KEY_CONTINUATION_COUNT",
    "DEFAULT_TEST_RUN_DIR",
    "MAX_CONTINUATION_ATTEMPTS",
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
