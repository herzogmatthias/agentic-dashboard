"""
Unit tests for Backend Dev Agent schemas and components.

Tests cover:
- I/O schema validation (FileChange, DevReport, BackendDevInput, BackendDevResult)
- DevCurrentState, DevChanges models
- create_helper_tool file creation
- create_backend_dev_agent factory function
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from src.models.backend_dev import (
    DevCurrentState,
    DevChanges,
    FileChange,
    DevReport,
    BackendDevInput,
    BackendDevResult,
    PlannerArtifactTodo,
    BackendArtifactKind,
)
from src.tools.backend_dev.creation import create_helper
from src.agents.backend_dev_team.dev.agent import (
    create_backend_dev_agent,
    BACKEND_DEV_MODEL,
)


# =============================================================================
# FileChange Schema Tests
# =============================================================================

class TestFileChange:
    """Tests for FileChange schema validation."""

    def test_file_change_valid_created(self):
        """Test valid FileChange with 'created' action."""
        fc = FileChange(
            path="src/app/api/sales/route.ts",
            action="created",
            description="Created sales API endpoint"
        )
        assert fc.path == "src/app/api/sales/route.ts"
        assert fc.action == "created"
        assert fc.description == "Created sales API endpoint"

    def test_file_change_valid_modified(self):
        """Test valid FileChange with 'modified' action."""
        fc = FileChange(
            path="src/lib/utils.ts",
            action="modified",
            description="Added helper function"
        )
        assert fc.action == "modified"

    def test_file_change_invalid_action(self):
        """Test FileChange rejects invalid action."""
        with pytest.raises(ValidationError) as exc_info:
            FileChange(
                path="src/file.ts",
                action="deleted",  # Invalid
                description="test"
            )
        assert "action" in str(exc_info.value).lower()

    def test_file_change_missing_required_fields(self):
        """Test FileChange requires all fields."""
        with pytest.raises(ValidationError):
            FileChange(path="src/file.ts")  # Missing action and description

    def test_file_change_empty_path(self):
        """Test FileChange accepts empty string path (schema doesn't enforce non-empty)."""
        fc = FileChange(path="", action="created", description="test")
        assert fc.path == ""


# =============================================================================
# DevCurrentState and DevChanges Tests
# =============================================================================

class TestDevCurrentState:
    """Tests for DevCurrentState model."""

    def test_minimal_state(self):
        """Test creating DevCurrentState with only required fields."""
        state = DevCurrentState(code_path="src/app/api/sales/route.ts")
        assert state.code_path == "src/app/api/sales/route.ts"
        assert state.dependent_code_paths == []
        assert state.exports is None

    def test_full_state(self):
        """Test creating DevCurrentState with all fields."""
        state = DevCurrentState(
            code_path="src/app/api/sales/route.ts",
            dependent_code_paths=["src/lib/db.ts", "src/models/sales.ts"],
            exports=["GET", "POST"],
        )
        assert len(state.dependent_code_paths) == 2
        assert len(state.exports) == 2


class TestDevChanges:
    """Tests for DevChanges model."""

    def test_default_values(self):
        """Test DevChanges default values."""
        changes = DevChanges()
        assert changes.files_created == []
        assert changes.files_modified == []
        assert changes.files_deleted == []

    def test_with_changes(self):
        """Test DevChanges with file changes."""
        changes = DevChanges(
            files_created=["new_file.ts"],
            files_modified=["existing.ts"],
            files_deleted=["old.ts"],
        )
        assert len(changes.files_created) == 1
        assert len(changes.files_modified) == 1
        assert len(changes.files_deleted) == 1


# =============================================================================
# DevReport Schema Tests
# =============================================================================

class TestDevReport:
    """Tests for DevReport schema validation."""

    def test_dev_report_minimal_success(self):
        """Test minimal valid DevReport with success status."""
        report = DevReport(
            artifact_id="route_sales",
            artifact_type="route",
            status="success",
            summary="Created sales endpoint",
            current_state=DevCurrentState(code_path="src/app/api/sales/route.ts"),
        )
        assert report.artifact_id == "route_sales"
        assert report.status == "success"
        assert report.current_state.code_path == "src/app/api/sales/route.ts"
        assert report.files_changed == []  # legacy field
        assert report.dependencies == []
        assert report.errors is None
        assert isinstance(report.timestamp, datetime)

    def test_dev_report_with_new_structure(self):
        """Test DevReport with new current_state and changes structure."""
        report = DevReport(
            artifact_id="route_kpis",
            artifact_type="route",
            status="success",
            summary="Created KPIs endpoint",
            current_state=DevCurrentState(
                code_path="src/app/api/kpis/route.ts",
                dependent_code_paths=["src/lib/db.ts"],
                exports=["GET"],
            ),
            changes=DevChanges(
                files_created=["src/app/api/kpis/route.ts"],
                files_modified=["src/lib/db.ts"],
            ),
            action_summary="Created route handler and updated db helper",
            implementation_notes="Used existing db connection pattern",
        )
        assert report.current_state.code_path == "src/app/api/kpis/route.ts"
        assert len(report.current_state.dependent_code_paths) == 1
        assert len(report.changes.files_created) == 1
        assert report.action_summary == "Created route handler and updated db helper"

    def test_dev_report_with_files_changed_legacy(self):
        """Test DevReport with legacy file changes."""
        report = DevReport(
            artifact_id="route_kpis",
            artifact_type="route",
            status="success",
            summary="Created KPIs endpoint",
            current_state=DevCurrentState(code_path="src/app/api/kpis/route.ts"),
            files_changed=[
                FileChange(path="src/app/api/kpis/route.ts", action="created", description="KPIs endpoint"),
                FileChange(path="src/models/KpiResponse.ts", action="created", description="Response type"),
            ]
        )
        assert len(report.files_changed) == 2
        assert report.files_changed[0].path == "src/app/api/kpis/route.ts"

    def test_dev_report_with_errors(self):
        """Test DevReport with failed status and errors."""
        report = DevReport(
            artifact_id="route_broken",
            artifact_type="route",
            status="failed",
            summary="Failed to create endpoint",
            current_state=DevCurrentState(code_path="src/app/api/broken/route.ts"),
            lint_passed=False,
            type_check_passed=False,
            errors=["TypeScript error: TS2304", "Missing import for Response"],
        )
        assert report.status == "failed"
        assert len(report.errors) == 2
        assert "TS2304" in report.errors[0]

    def test_dev_report_partial_status(self):
        """Test DevReport with partial status."""
        report = DevReport(
            artifact_id="helper_utils",
            artifact_type="helper",
            status="partial",
            summary="Created helper but lint failed",
            current_state=DevCurrentState(code_path="src/lib/utils.ts"),
            lint_passed=False,
            type_check_passed=True,
            errors=["Lint warning: unused variable"],
        )
        assert report.status == "partial"
        assert report.artifact_type == "helper"

    def test_dev_report_with_dependencies(self):
        """Test DevReport with discovered dependencies."""
        report = DevReport(
            artifact_id="route_details",
            artifact_type="route",
            status="success",
            summary="Created details endpoint",
            current_state=DevCurrentState(code_path="src/app/api/details/route.ts"),
            dependencies=["helper_data_loader", "route_base"],
        )
        assert len(report.dependencies) == 2

    def test_dev_report_with_next_steps(self):
        """Test DevReport with next_steps field."""
        report = DevReport(
            artifact_id="route_partial",
            artifact_type="route",
            status="partial",
            summary="Partially implemented",
            current_state=DevCurrentState(code_path="src/app/api/partial/route.ts"),
            next_steps=["Add error handling", "Implement caching"],
        )
        assert len(report.next_steps) == 2

    def test_dev_report_invalid_status(self):
        """Test DevReport rejects invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            DevReport(
                artifact_id="test",
                artifact_type="route",
                status="unknown",  # Invalid
                summary="test",
                current_state=DevCurrentState(code_path="test.ts"),
            )
        assert "status" in str(exc_info.value).lower()

    def test_dev_report_invalid_artifact_type(self):
        """Test DevReport rejects invalid artifact_type."""
        with pytest.raises(ValidationError) as exc_info:
            DevReport(
                artifact_id="test",
                artifact_type="model",  # Invalid - only route/helper allowed
                status="success",
                summary="test",
                current_state=DevCurrentState(code_path="test.ts"),
            )
        assert "artifact_type" in str(exc_info.value).lower()


# =============================================================================
# BackendDevInput Schema Tests
# =============================================================================

class TestBackendDevInput:
    """Tests for BackendDevInput schema validation."""

    @pytest.fixture
    def sample_artifact(self) -> PlannerArtifactTodo:
        """Create a sample PlannerArtifactTodo for testing."""
        return PlannerArtifactTodo(
            id="route_sales_by_region",
            kind=BackendArtifactKind.route,
            title="Sales by Region API",
            description="Returns sales data grouped by region",
            http_path="/api/sales/by-region",
            http_method="GET",
            priority=1,
        )

    def test_backend_dev_input_valid(self, sample_artifact):
        """Test valid BackendDevInput."""
        input_data = BackendDevInput(
            run_id="run_20251208_120000",
            artifact=sample_artifact,
            workspace_root="/path/to/sample-dashboard",
        )
        assert input_data.run_id == "run_20251208_120000"
        assert input_data.artifact.id == "route_sales_by_region"
        assert input_data.previous_summaries is None

    def test_backend_dev_input_with_previous_summaries(self, sample_artifact):
        """Test BackendDevInput with previous summaries."""
        input_data = BackendDevInput(
            run_id="run_20251208_120000",
            artifact=sample_artifact,
            workspace_root="/path/to/sample-dashboard",
            previous_summaries=[
                "[route_kpis] Created KPIs endpoint with attrition rate",
                "[helper_data_loader] Created CSV data loader utility",
            ],
        )
        assert len(input_data.previous_summaries) == 2
        assert "route_kpis" in input_data.previous_summaries[0]

    def test_backend_dev_input_missing_artifact(self):
        """Test BackendDevInput requires artifact."""
        with pytest.raises(ValidationError):
            BackendDevInput(
                run_id="test_run",
                workspace_root="/path/to/workspace",
            )

    def test_backend_dev_input_empty_previous_summaries(self, sample_artifact):
        """Test BackendDevInput with empty previous_summaries list."""
        input_data = BackendDevInput(
            run_id="test_run",
            artifact=sample_artifact,
            workspace_root="/path/to/workspace",
            previous_summaries=[],
        )
        assert input_data.previous_summaries == []


# =============================================================================
# BackendDevResult Schema Tests
# =============================================================================

class TestBackendDevResult:
    """Tests for BackendDevResult schema validation."""

    @pytest.fixture
    def sample_report(self) -> DevReport:
        """Create a sample DevReport for testing."""
        return DevReport(
            artifact_id="route_sales",
            artifact_type="route",
            status="success",
            summary="Created sales API endpoint with region filter",
            current_state=DevCurrentState(
                code_path="src/app/api/sales/route.ts",
                exports=["GET"],
            ),
            files_changed=[
                FileChange(
                    path="src/app/api/sales/route.ts",
                    action="created",
                    description="Sales endpoint"
                ),
            ],
        )

    def test_backend_dev_result_success(self, sample_report):
        """Test valid BackendDevResult with success status."""
        result = BackendDevResult(
            status="success",
            summary="Implemented sales endpoint successfully",
            report=sample_report,
        )
        assert result.status == "success"
        assert result.escalate is False  # Default
        assert result.report.artifact_id == "route_sales"

    def test_backend_dev_result_with_escalate(self, sample_report):
        """Test BackendDevResult with escalate flag."""
        result = BackendDevResult(
            status="failed",
            summary="Requirements unclear - need user input",
            escalate=True,
            report=DevReport(
                artifact_id="route_complex",
                artifact_type="route",
                status="failed",
                summary="Could not determine endpoint shape",
                current_state=DevCurrentState(code_path="src/app/api/complex/route.ts"),
                lint_passed=False,
                type_check_passed=False,
                errors=["Unclear requirements: multiple possible interpretations"],
            ),
        )
        assert result.escalate is True
        assert result.status == "failed"

    def test_backend_dev_result_partial(self, sample_report):
        """Test BackendDevResult with partial status."""
        partial_report = DevReport(
            artifact_id="route_partial",
            artifact_type="route",
            status="partial",
            summary="Created endpoint but lint warnings present",
            current_state=DevCurrentState(code_path="src/app/api/partial/route.ts"),
            lint_passed=False,
            type_check_passed=True,
        )
        result = BackendDevResult(
            status="partial",
            summary="Implemented but has warnings",
            report=partial_report,
        )
        assert result.status == "partial"

    def test_backend_dev_result_status_mismatch_allowed(self, sample_report):
        """Test that status can differ from report.status (schema allows it)."""
        # This tests current behavior - status fields are independent
        result = BackendDevResult(
            status="success",  # Result says success
            summary="Overall success",
            report=DevReport(
                artifact_id="test",
                artifact_type="route",
                status="partial",  # But report says partial
                summary="Some issues",
                current_state=DevCurrentState(code_path="src/app/api/test/route.ts"),
            ),
        )
        assert result.status == "success"
        assert result.report.status == "partial"

    def test_backend_dev_result_missing_report(self):
        """Test BackendDevResult requires report."""
        with pytest.raises(ValidationError):
            BackendDevResult(
                status="success",
                summary="Missing report",
            )


# =============================================================================
# create_helper_tool Tests
# =============================================================================

class TestCreateHelperTool:
    """Tests for create_helper tool."""

    @pytest.fixture
    def mock_tool_context(self, tmp_path):
        """Create a mock ToolContext with state."""
        context = MagicMock()
        context.state = {"run_dir": str(tmp_path)}
        return context

    @pytest.fixture
    def sample_dashboard_root(self, tmp_path):
        """Create a temporary sample-dashboard structure."""
        dashboard = tmp_path / "sample-dashboard"
        (dashboard / "src" / "lib").mkdir(parents=True)
        return dashboard

    @pytest.fixture
    def mock_validate_path(self, sample_dashboard_root):
        """Mock _validate_path to allow temp directory paths."""
        def _mock_validate(requested_path, run_dir=None, allow_new=False):
            path = Path(requested_path)
            # For tests, just resolve and allow if under the temp dashboard
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path
            
            # Check if path is under sample_dashboard_root
            try:
                resolved.relative_to(sample_dashboard_root)
                return True, resolved, ""
            except ValueError:
                return False, resolved, f"Path not within allowed directories: {resolved}"
        
        return _mock_validate

    def test_create_helper_valid_content(self, mock_tool_context, sample_dashboard_root, mock_validate_path):
        """Test create_helper with valid TypeScript content."""
        valid_content = '''
export function formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

export const DEFAULT_LOCALE = 'en-US';
'''
        with patch(
            "src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT",
            sample_dashboard_root
        ), patch(
            "src.tools.backend_dev.creation._validate_path",
            mock_validate_path
        ):
            result = create_helper(
                name="formatters",
                content=valid_content,
                tool_context=mock_tool_context,
            )
        
        assert result["success"] is True
        assert "formatters.ts" in result["relative_path"]
        assert (sample_dashboard_root / "src" / "lib" / "formatters.ts").exists()

    def test_create_helper_strips_ts_extension(self, mock_tool_context, sample_dashboard_root, mock_validate_path):
        """Test create_helper removes .ts extension from name if provided."""
        valid_content = "export const TEST = 1;"
        
        with patch(
            "src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT",
            sample_dashboard_root
        ), patch(
            "src.tools.backend_dev.creation._validate_path",
            mock_validate_path
        ):
            result = create_helper(
                name="utils.ts",  # With .ts
                content=valid_content,
                tool_context=mock_tool_context,
            )
        
        assert result["success"] is True
        assert "utils.ts" in result["relative_path"]
        # Should not create utils.ts.ts
        assert not (sample_dashboard_root / "src" / "lib" / "utils.ts.ts").exists()

    def test_create_helper_no_export_fails(self, mock_tool_context, sample_dashboard_root, mock_validate_path):
        """Test create_helper rejects content without exports."""
        no_export_content = '''
function internalHelper(): void {
    console.log("internal");
}
'''
        with patch(
            "src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT",
            sample_dashboard_root
        ), patch(
            "src.tools.backend_dev.creation._validate_path",
            mock_validate_path
        ):
            result = create_helper(
                name="internal",
                content=no_export_content,
                tool_context=mock_tool_context,
            )
        
        assert result["success"] is False
        assert "export" in result["error"].lower()

    def test_create_helper_syntax_error_is_not_validated(self, mock_tool_context, sample_dashboard_root, mock_validate_path):
        """Test that create_helper does NOT reject syntax errors.
        
        Note: TypeScript syntax validation via tsc is DISABLED because standalone
        file checking cannot resolve imports (e.g., from '@/lib/...' or 'next/server').
        The file will be created and validation happens later via run_lint/run_build.
        """
        invalid_syntax = '''
export function broken( {
    return "missing closing paren";
}
'''
        with patch(
            "src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT",
            sample_dashboard_root
        ), patch(
            "src.tools.backend_dev.creation._validate_path",
            mock_validate_path
        ):
            result = create_helper(
                name="broken",
                content=invalid_syntax,
                tool_context=mock_tool_context,
            )
        
        # File creation succeeds - syntax validation is disabled
        # Real validation happens via run_lint() / run_build()
        assert result["success"] is True
        assert (sample_dashboard_root / "src" / "lib" / "broken.ts").exists()

    def test_create_helper_file_exists_fails(self, mock_tool_context, sample_dashboard_root, mock_validate_path):
        """Test create_helper rejects if file already exists."""
        # Create existing file
        lib_dir = sample_dashboard_root / "src" / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        (lib_dir / "existing.ts").write_text("export const X = 1;")
        
        with patch(
            "src.tools.backend_dev.creation.SAMPLE_DASHBOARD_ROOT",
            sample_dashboard_root
        ), patch(
            "src.tools.backend_dev.creation._validate_path",
            mock_validate_path
        ):
            result = create_helper(
                name="existing",
                content="export const Y = 2;",
                tool_context=mock_tool_context,
            )
        
        assert result["success"] is False
        assert "exists" in result["error"].lower()


# =============================================================================
# create_backend_dev_agent Factory Tests
# =============================================================================

class TestCreateBackendDevAgent:
    """Tests for create_backend_dev_agent factory function."""

    def test_create_agent_returns_llm_agent(self):
        """Test factory returns an LlmAgent instance."""
        from google.adk.agents import LlmAgent
        
        agent = create_backend_dev_agent()
        assert isinstance(agent, LlmAgent)

    def test_create_agent_has_correct_name(self):
        """Test agent has correct name."""
        agent = create_backend_dev_agent()
        assert agent.name == "backend_dev"

    def test_create_agent_has_output_schema(self):
        """Test agent has BackendDevResult as output_schema."""
        agent = create_backend_dev_agent()
        assert agent.output_schema == BackendDevResult

    def test_create_agent_has_planner(self):
        """Test agent has PlanReActPlanner configured."""
        from google.adk.planners import PlanReActPlanner
        
        agent = create_backend_dev_agent()
        assert isinstance(agent.planner, PlanReActPlanner)

    def test_create_agent_has_tools(self):
        """Test agent has tools configured."""
        agent = create_backend_dev_agent()
        # Agent should have tools (list or tuple)
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_create_agent_has_dynamic_instruction(self):
        """Test agent has a callable instruction provider."""
        agent = create_backend_dev_agent()
        # instruction should be the function backend_dev_instruction_provider
        assert callable(agent.instruction)


# =============================================================================
# Run with pytest
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
