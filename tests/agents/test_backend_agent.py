"""
Unit tests for the Backend Agent.

Tests cover:
- Agent creation and configuration
- State initialization callback
- Cleaned data files collection
- Tool configuration
- Custom agent with continuation support
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Any

import pytest


class TestGetCleanedDataFiles:
    """Tests for get_cleaned_data_files helper function."""

    def test_returns_files_from_cleaned_dir(self, tmp_path: Path):
        """Returns files from run_dir/cleaned/ directory."""
        from src.agents.backend.utils import get_cleaned_data_files
        
        # Create cleaned directory with files
        cleaned_dir = tmp_path / "cleaned"
        cleaned_dir.mkdir()
        (cleaned_dir / "data.csv").write_text("a,b\n1,2")
        (cleaned_dir / "metrics.json").write_text("{}")
        
        result = get_cleaned_data_files(tmp_path)
        
        assert len(result) == 2
        assert "sample-dashboard/data/data.csv" in result
        assert "sample-dashboard/data/metrics.json" in result

    def test_returns_empty_list_when_no_cleaned_dir(self, tmp_path: Path):
        """Returns empty list when no cleaned directory exists."""
        from src.agents.backend.utils import get_cleaned_data_files
        
        result = get_cleaned_data_files(tmp_path)
        
        assert result == []

    def test_ignores_subdirectories(self, tmp_path: Path):
        """Only returns files, not subdirectories."""
        from src.agents.backend.utils import get_cleaned_data_files
        
        cleaned_dir = tmp_path / "cleaned"
        cleaned_dir.mkdir()
        (cleaned_dir / "data.csv").write_text("a,b\n1,2")
        (cleaned_dir / "subdir").mkdir()
        
        result = get_cleaned_data_files(tmp_path)
        
        assert len(result) == 1
        assert "sample-dashboard/data/data.csv" in result

    def test_returns_sorted_list(self, tmp_path: Path):
        """Returns files in sorted order."""
        from src.agents.backend.utils import get_cleaned_data_files
        
        cleaned_dir = tmp_path / "cleaned"
        cleaned_dir.mkdir()
        (cleaned_dir / "z_last.csv").write_text("")
        (cleaned_dir / "a_first.csv").write_text("")
        (cleaned_dir / "m_middle.csv").write_text("")
        
        result = get_cleaned_data_files(tmp_path)
        
        assert result == [
            "sample-dashboard/data/a_first.csv",
            "sample-dashboard/data/m_middle.csv",
            "sample-dashboard/data/z_last.csv",
        ]


class TestInitializeBackendState:
    """Tests for initialize_backend_state callback."""

    def _create_mock_callback_context(self, state: dict[str, Any]) -> MagicMock:
        """Create a mock CallbackContext with the given state."""
        ctx = MagicMock()
        ctx.state = state
        return ctx

    def test_sets_default_run_dir_when_not_present(self, tmp_path: Path):
        """Uses DEFAULT_TEST_RUN_DIR when run_dir not in state."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
            STATE_KEY_RUN_ID,
            DEFAULT_TEST_RUN_DIR,
        )
        
        state: dict[str, Any] = {}
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"total_files": 0, "copied_files": []}
            result = initialize_backend_state(ctx)
        
        assert result is None
        assert STATE_KEY_RUN_DIR in state
        assert STATE_KEY_RUN_ID in state
        assert state[STATE_KEY_RUN_ID] == DEFAULT_TEST_RUN_DIR.name

    def test_uses_existing_run_dir(self, tmp_path: Path):
        """Uses existing run_dir from state."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
        )
        
        # Create run directory with data profile
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        (run_dir / "data_profile.md").write_text("# Profile")
        (run_dir / "cleaned").mkdir()
        
        state: dict[str, Any] = {STATE_KEY_RUN_DIR: str(run_dir)}
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"total_files": 0, "copied_files": []}
            initialize_backend_state(ctx)
        
        assert state[STATE_KEY_RUN_DIR] == str(run_dir)

    def test_sets_data_profile_path(self, tmp_path: Path):
        """Sets data_profile_path from run_dir/data_profile.md."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
            STATE_KEY_DATA_PROFILE_PATH,
        )
        
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        profile_path = run_dir / "data_profile.md"
        profile_path.write_text("# Data Profile")
        (run_dir / "cleaned").mkdir()
        
        state: dict[str, Any] = {STATE_KEY_RUN_DIR: str(run_dir)}
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"total_files": 0, "copied_files": []}
            initialize_backend_state(ctx)
        
        assert state[STATE_KEY_DATA_PROFILE_PATH] == str(profile_path.resolve())

    def test_sets_dashboard_spec_path(self, tmp_path: Path):
        """Sets dashboard_spec_path from run_dir/planner/dashboard_concept.json."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
            STATE_KEY_DASHBOARD_SPEC_PATH,
        )
        
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        (run_dir / "planner").mkdir()
        concept_path = run_dir / "planner" / "dashboard_concept.json"
        concept_path.write_text('{"goal": "test"}')
        (run_dir / "cleaned").mkdir()
        
        state: dict[str, Any] = {STATE_KEY_RUN_DIR: str(run_dir)}
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"total_files": 0, "copied_files": []}
            initialize_backend_state(ctx)
        
        assert state[STATE_KEY_DASHBOARD_SPEC_PATH] == str(concept_path.resolve())

    def test_calls_copy_data_to_project(self, tmp_path: Path):
        """Calls copy_data_to_project with current state."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
        )
        
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        (run_dir / "cleaned").mkdir()
        
        state: dict[str, Any] = {STATE_KEY_RUN_DIR: str(run_dir)}
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"total_files": 2, "copied_files": []}
            initialize_backend_state(ctx)
            
            mock_copy.assert_called_once()

    def test_populates_cleaned_data_files(self, tmp_path: Path):
        """Populates cleaned_data_files list in state."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
            STATE_KEY_CLEANED_DATA_FILES,
        )
        
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        cleaned_dir = run_dir / "cleaned"
        cleaned_dir.mkdir()
        (cleaned_dir / "data.csv").write_text("a,b\n1,2")
        (cleaned_dir / "metrics.csv").write_text("x,y\n1,2")
        
        state: dict[str, Any] = {STATE_KEY_RUN_DIR: str(run_dir)}
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"total_files": 2, "copied_files": []}
            initialize_backend_state(ctx)
        
        assert STATE_KEY_CLEANED_DATA_FILES in state
        assert len(state[STATE_KEY_CLEANED_DATA_FILES]) == 2

    def test_handles_copy_error_gracefully(self, tmp_path: Path):
        """Continues initialization even if copy fails."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
            STATE_KEY_CLEANED_DATA_FILES,
        )
        
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        (run_dir / "cleaned").mkdir()
        
        state: dict[str, Any] = {STATE_KEY_RUN_DIR: str(run_dir)}
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"error": "Source not found"}
            result = initialize_backend_state(ctx)
        
        assert result is None
        assert STATE_KEY_CLEANED_DATA_FILES in state

    def test_preserves_existing_paths_in_state(self, tmp_path: Path):
        """Does not override existing path values in state."""
        from src.agents.backend.callbacks import (
            initialize_backend_state,
            STATE_KEY_RUN_DIR,
            STATE_KEY_DATA_PROFILE_PATH,
            STATE_KEY_DASHBOARD_SPEC_PATH,
        )
        
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        (run_dir / "cleaned").mkdir()
        
        state: dict[str, Any] = {
            STATE_KEY_RUN_DIR: str(run_dir),
            STATE_KEY_DATA_PROFILE_PATH: "/custom/path/profile.md",
            STATE_KEY_DASHBOARD_SPEC_PATH: "/custom/path/concept.json",
        }
        ctx = self._create_mock_callback_context(state)
        
        with patch("src.agents.backend.callbacks.copy_data_to_project") as mock_copy:
            mock_copy.return_value = {"total_files": 0, "copied_files": []}
            initialize_backend_state(ctx)
        
        assert state[STATE_KEY_DATA_PROFILE_PATH] == "/custom/path/profile.md"
        assert state[STATE_KEY_DASHBOARD_SPEC_PATH] == "/custom/path/concept.json"


class TestCreateBackendAgent:
    """Tests for create_backend_agent factory function."""

    def test_creates_custom_agent(self):
        """Creates a BackendAgentWithContinuation instance."""
        from src.agents.backend.agent import create_backend_agent
        from src.agents.backend.custom_agent import BackendAgentWithContinuation
        
        agent = create_backend_agent()
        
        assert isinstance(agent, BackendAgentWithContinuation)

    def test_agent_has_correct_name(self):
        """Agent has name 'backend'."""
        from src.agents.backend.agent import create_backend_agent
        
        agent = create_backend_agent()
        
        assert agent.name == "backend"

    def test_agent_wraps_llm_agent(self):
        """Agent contains a wrapped LlmAgent."""
        from src.agents.backend.agent import create_backend_agent
        from google.adk.agents import LlmAgent
        
        agent = create_backend_agent()
        
        assert agent.llm_agent is not None
        assert isinstance(agent.llm_agent, LlmAgent)

    def test_agent_has_max_continuations(self):
        """Agent has max_continuations configured."""
        from src.agents.backend.agent import create_backend_agent, MAX_CONTINUATION_ATTEMPTS
        
        agent = create_backend_agent()
        
        assert agent.max_continuations == MAX_CONTINUATION_ATTEMPTS

    def test_custom_max_continuations(self):
        """Agent accepts custom max_continuations."""
        from src.agents.backend.agent import create_backend_agent
        
        agent = create_backend_agent(max_continuations=5)
        
        assert agent.max_continuations == 5


class TestCreateBackendLlmAgent:
    """Tests for create_backend_llm_agent factory function."""

    def test_creates_llm_agent(self):
        """Creates a raw LlmAgent instance."""
        from src.agents.backend.agent import create_backend_llm_agent
        from google.adk.agents import LlmAgent
        
        agent = create_backend_llm_agent()
        
        assert isinstance(agent, LlmAgent)

    def test_agent_has_correct_name(self):
        """Agent has name 'backend_llm'."""
        from src.agents.backend.agent import create_backend_llm_agent
        
        agent = create_backend_llm_agent()
        
        assert agent.name == "backend_llm"

    def test_agent_has_instruction(self):
        """Agent has instruction provider function configured."""
        from src.agents.backend.agent import create_backend_llm_agent
        from src.agents.backend.callbacks import backend_instruction_provider
        
        agent = create_backend_llm_agent()
        
        assert agent.instruction is not None
        assert callable(agent.instruction)
        assert agent.instruction == backend_instruction_provider

    def test_agent_has_tools(self):
        """Agent has tools configured."""
        from src.agents.backend.agent import create_backend_llm_agent
        
        agent = create_backend_llm_agent()
        
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_has_before_callback(self):
        """Agent has before_agent_callback configured."""
        from src.agents.backend.agent import create_backend_llm_agent
        from src.agents.backend.callbacks import initialize_backend_state
        
        agent = create_backend_llm_agent()
        
        assert agent.before_agent_callback == initialize_backend_state


class TestGetBackendAgent:
    """Tests for get_backend_agent convenience function."""

    def test_returns_custom_agent(self):
        """Returns a BackendAgentWithContinuation instance."""
        from src.agents.backend.agent import get_backend_agent
        from src.agents.backend.custom_agent import BackendAgentWithContinuation
        
        agent = get_backend_agent()
        
        assert isinstance(agent, BackendAgentWithContinuation)

    def test_returns_new_instance_each_call(self):
        """Returns a new instance on each call."""
        from src.agents.backend.agent import get_backend_agent
        
        agent1 = get_backend_agent()
        agent2 = get_backend_agent()
        
        assert agent1 is not agent2


class TestGetBackendLlmAgent:
    """Tests for get_backend_llm_agent convenience function."""

    def test_returns_llm_agent(self):
        """Returns a raw LlmAgent instance."""
        from src.agents.backend.agent import get_backend_llm_agent
        from google.adk.agents import LlmAgent
        
        agent = get_backend_llm_agent()
        
        assert isinstance(agent, LlmAgent)

    def test_returns_new_instance_each_call(self):
        """Returns a new instance on each call."""
        from src.agents.backend.agent import get_backend_llm_agent
        
        agent1 = get_backend_llm_agent()
        agent2 = get_backend_llm_agent()
        
        assert agent1 is not agent2


class TestBackendAgentExports:
    """Tests for package exports."""

    def test_exports_create_backend_agent(self):
        """Package exports create_backend_agent."""
        from src.agents.backend import create_backend_agent
        
        assert callable(create_backend_agent)

    def test_exports_create_backend_llm_agent(self):
        """Package exports create_backend_llm_agent."""
        from src.agents.backend import create_backend_llm_agent
        
        assert callable(create_backend_llm_agent)

    def test_exports_get_backend_agent(self):
        """Package exports get_backend_agent."""
        from src.agents.backend import get_backend_agent
        
        assert callable(get_backend_agent)

    def test_exports_get_backend_llm_agent(self):
        """Package exports get_backend_llm_agent."""
        from src.agents.backend import get_backend_llm_agent
        
        assert callable(get_backend_llm_agent)

    def test_exports_custom_agent_class(self):
        """Package exports BackendAgentWithContinuation."""
        from src.agents.backend import BackendAgentWithContinuation
        
        assert BackendAgentWithContinuation is not None

    def test_exports_initialize_backend_state(self):
        """Package exports initialize_backend_state."""
        from src.agents.backend import initialize_backend_state
        
        assert callable(initialize_backend_state)

    def test_exports_state_keys(self):
        """Package exports state key constants."""
        from src.agents.backend import (
            STATE_KEY_RUN_ID,
            STATE_KEY_RUN_DIR,
            STATE_KEY_DATA_PROFILE_PATH,
            STATE_KEY_DASHBOARD_SPEC_PATH,
            STATE_KEY_CLEANED_DATA_FILES,
            STATE_KEY_CONTINUATION_COUNT,
            MAX_CONTINUATION_ATTEMPTS,
        )
        
        assert STATE_KEY_RUN_ID == "run_id"
        assert STATE_KEY_RUN_DIR == "run_dir"
        assert STATE_KEY_DATA_PROFILE_PATH == "data_profile_path"
        assert STATE_KEY_DASHBOARD_SPEC_PATH == "dashboard_spec_path"
        assert STATE_KEY_CLEANED_DATA_FILES == "cleaned_data_files"
        assert STATE_KEY_CONTINUATION_COUNT == "_backend_continuation_count"
        assert isinstance(MAX_CONTINUATION_ATTEMPTS, int)

    def test_exports_default_test_run_dir(self):
        """Package exports DEFAULT_TEST_RUN_DIR."""
        from src.agents.backend import DEFAULT_TEST_RUN_DIR
        
        assert DEFAULT_TEST_RUN_DIR.name == "run_20251204_142914"

    def test_exports_build_backend_agent_prompt(self):
        """Package exports build_backend_agent_prompt."""
        from src.agents.backend import build_backend_agent_prompt
        
        assert callable(build_backend_agent_prompt)

    def test_exports_utility_functions(self):
        """Package exports utility functions."""
        from src.agents.backend import (
            get_cleaned_data_files,
            format_cleaned_files_for_prompt,
        )
        
        assert callable(get_cleaned_data_files)
        assert callable(format_cleaned_files_for_prompt)

