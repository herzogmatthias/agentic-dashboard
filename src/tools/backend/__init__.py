"""Backend Agent tools for file system operations, creation, validation, and manifest generation."""

from src.tools.backend.filesystem import (
    read_file,
    read_file_tool,
    inspect_dir,
    inspect_dir_tool,
    search_content,
    search_content_tool,
    ALLOWED_PATHS,
)

from src.tools.backend.data_access import (
    MAX_SAMPLE_ROWS,
    get_sample_rows,
    get_sample_rows_tool,
    read_data_profile,
    read_data_profile_tool,
    read_dashboard_concept,
    read_dashboard_concept_tool,
    copy_data_to_project,  # Callback helper, not a tool
)

from src.tools.backend.creation import (
    create_api,
    create_api_tool,
    create_model,
    create_model_tool,
    add_utility,
    add_utility_tool,
)

__all__ = [
    # Filesystem functions
    "read_file",
    "inspect_dir",
    "search_content",
    # Filesystem tools
    "read_file_tool",
    "inspect_dir_tool",
    "search_content_tool",
    # Data access functions
    "get_sample_rows",
    "read_data_profile",
    "read_dashboard_concept",
    # Data access tools
    "get_sample_rows_tool",
    "read_data_profile_tool",
    "read_dashboard_concept_tool",
    # Creation functions
    "create_api",
    "create_model",
    "add_utility",
    # Creation tools
    "create_api_tool",
    "create_model_tool",
    "add_utility_tool",
    # Callback helpers (not tools)
    "copy_data_to_project",
    # Constants
    "ALLOWED_PATHS",
    "MAX_SAMPLE_ROWS",
]
