"""
Unit tests for Testing Agent models.

Tests validation, serialization, and default values for:
- TestCurrentState, TestChanges, TestExecutionResult
- TestReport
- TestAgentInput
- TestAgentResult
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.testing_agent import (
    TestCurrentState,
    TestChanges,
    TestExecutionResult,
    TestReport,
    TestAgentInput,
    TestAgentResult,
)
from src.models.backend_planner_todos import (
    PlannerArtifactTodo,
    BackendArtifactKind,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_artifact() -> PlannerArtifactTodo:
    """Create a sample artifact for testing."""
    return PlannerArtifactTodo(
        id="route_sales_by_region",
        kind=BackendArtifactKind.route,
        title="Sales by Region",
        description="Returns sales data grouped by region",
        http_path="/api/sales/by-region",
        http_method="GET",
    )


@pytest.fixture
def sample_helper_artifact() -> PlannerArtifactTodo:
    """Create a sample helper artifact for testing."""
    return PlannerArtifactTodo(
        id="helper_aggregate_sales",
        kind=BackendArtifactKind.helper,
        title="Aggregate Sales Helper",
        description="Helper function for aggregating sales data",
    )


@pytest.fixture
def sample_test_report() -> TestReport:
    """Create a sample test report for testing with new structure."""
    return TestReport(
        artifact_id="route_sales_by_region",
        timestamp="2025-01-01T12:00:00Z",
        current_state=TestCurrentState(
            test_paths=["tests/api/route_sales_by_region.test.ts"]
        ),
        changes=TestChanges(
            files_created=["tests/api/route_sales_by_region.test.ts"],
            files_modified=[],
            files_deleted=[],
        ),
        execution=TestExecutionResult(
            tests_run=3,
            tests_passed=3,
            tests_failed=0,
            failed_test_names=[],
            command_used="npm test -- route_sales_by_region.test.ts",
            output_snippet="Test Suites: 1 passed, 1 total\nTests: 3 passed, 3 total",
        ),
        notes="Covers happy path and missing param validation",
    )


@pytest.fixture
def sample_test_report_legacy() -> TestReport:
    """Create a sample test report using legacy fields for backward compatibility."""
    return TestReport(
        artifact_id="route_sales_by_region",
        timestamp="2025-01-01T12:00:00Z",
        current_tests=["tests/api/route_sales_by_region.test.ts"],
        test_files_created=["tests/api/route_sales_by_region.test.ts"],
        test_files_modified=[],
        test_files_deleted=[],
        tests_run=3,
        tests_failed=0,
        failed_test_names=[],
        command_used="npm test -- route_sales_by_region.test.ts",
        output_snippet="Test Suites: 1 passed, 1 total\nTests: 3 passed, 3 total",
        notes="Covers happy path and missing param validation",
    )


# =============================================================================
# TestCurrentState Tests
# =============================================================================

class TestTestCurrentState:
    """Tests for TestCurrentState model."""

    def test_default_values(self):
        """Test default values for TestCurrentState."""
        state = TestCurrentState()
        assert state.test_paths == []

    def test_with_test_paths(self):
        """Test TestCurrentState with test paths."""
        state = TestCurrentState(
            test_paths=["tests/api/route.test.ts", "tests/lib/helper.test.ts"]
        )
        assert len(state.test_paths) == 2

    def test_serialization(self):
        """Test TestCurrentState serialization."""
        state = TestCurrentState(test_paths=["test.ts"])
        data = state.model_dump()
        assert data["test_paths"] == ["test.ts"]


# =============================================================================
# TestChanges Tests
# =============================================================================

class TestTestChanges:
    """Tests for TestChanges model."""

    def test_default_values(self):
        """Test default values for TestChanges."""
        changes = TestChanges()
        assert changes.files_created == []
        assert changes.files_modified == []
        assert changes.files_deleted == []

    def test_with_changes(self):
        """Test TestChanges with file changes."""
        changes = TestChanges(
            files_created=["new_test.ts"],
            files_modified=["existing_test.ts"],
            files_deleted=["old_test.ts"],
        )
        assert len(changes.files_created) == 1
        assert len(changes.files_modified) == 1
        assert len(changes.files_deleted) == 1


# =============================================================================
# TestExecutionResult Tests
# =============================================================================

class TestTestExecutionResult:
    """Tests for TestExecutionResult model."""

    def test_default_values(self):
        """Test default values for TestExecutionResult."""
        result = TestExecutionResult()
        assert result.tests_run == 0
        assert result.tests_passed == 0
        assert result.tests_failed == 0
        assert result.command_used == "npm test"

    def test_with_results(self):
        """Test TestExecutionResult with execution results."""
        result = TestExecutionResult(
            tests_run=10,
            tests_passed=8,
            tests_failed=2,
            failed_test_names=["test1", "test2"],
            command_used="npm test -- pattern.test.ts",
            output_snippet="2 failed, 8 passed",
        )
        assert result.tests_run == 10
        assert result.tests_failed == 2
        assert len(result.failed_test_names) == 2


# =============================================================================
# TestReport Tests
# =============================================================================

class TestTestReport:
    """Tests for TestReport model."""

    def test_minimal_valid_report(self):
        """Test creating a report with only required fields."""
        report = TestReport(
            artifact_id="test_artifact",
            timestamp="2025-01-01T12:00:00Z",
        )
        assert report.artifact_id == "test_artifact"
        assert report.timestamp == "2025-01-01T12:00:00Z"
        assert report.current_state.test_paths == []
        assert report.execution.tests_run == 0

    def test_full_report_new_structure(self, sample_test_report):
        """Test creating a report with new nested structure."""
        report = sample_test_report
        assert report.artifact_id == "route_sales_by_region"
        assert len(report.current_state.test_paths) == 1
        assert report.execution.tests_run == 3
        assert report.execution.tests_failed == 0
        assert "npm test" in report.execution.command_used

    def test_full_report_legacy_structure(self, sample_test_report_legacy):
        """Test backward compatibility with legacy flat structure."""
        report = sample_test_report_legacy
        assert report.artifact_id == "route_sales_by_region"
        assert len(report.current_tests) == 1  # legacy field
        assert report.tests_run == 3  # legacy field
        assert report.tests_failed == 0  # legacy field

    def test_report_with_failures(self):
        """Test report with failing tests using new structure."""
        report = TestReport(
            artifact_id="failing_artifact",
            timestamp="2025-01-01T12:00:00Z",
            current_state=TestCurrentState(
                test_paths=["tests/api/failing.test.ts"]
            ),
            changes=TestChanges(
                files_created=["tests/api/failing.test.ts"]
            ),
            execution=TestExecutionResult(
                tests_run=5,
                tests_passed=3,
                tests_failed=2,
                failed_test_names=[
                    "should return 400 for missing param",
                    "should validate enum values",
                ],
                command_used="npm test -- failing.test.ts",
                output_snippet="FAIL tests/api/failing.test.ts\n  ✕ should return 400...",
            ),
        )
        assert report.execution.tests_failed == 2
        assert len(report.execution.failed_test_names) == 2

    def test_report_with_deleted_files(self):
        """Test report that includes deleted test files."""
        report = TestReport(
            artifact_id="refactored_artifact",
            timestamp="2025-01-01T12:00:00Z",
            current_state=TestCurrentState(
                test_paths=["tests/api/new_test.test.ts"]
            ),
            changes=TestChanges(
                files_created=["tests/api/new_test.test.ts"],
                files_deleted=["tests/api/old_test.test.ts"],
            ),
            execution=TestExecutionResult(
                tests_run=2,
                tests_passed=2,
                tests_failed=0,
            ),
        )
        assert len(report.changes.files_deleted) == 1
        assert "old_test.test.ts" in report.changes.files_deleted[0]

    def test_report_serialization(self, sample_test_report):
        """Test that report serializes to dict correctly."""
        data = sample_test_report.model_dump()
        assert isinstance(data, dict)
        assert data["artifact_id"] == "route_sales_by_region"
        assert isinstance(data["current_state"]["test_paths"], list)
        assert isinstance(data["execution"]["tests_run"], int)

    def test_report_json_serialization(self, sample_test_report):
        """Test that report serializes to JSON correctly."""
        json_str = sample_test_report.model_dump_json()
        assert isinstance(json_str, str)
        assert "route_sales_by_region" in json_str

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TestReport(timestamp="2025-01-01T12:00:00Z")  # missing artifact_id
        assert "artifact_id" in str(exc_info.value)


# =============================================================================
# TestAgentInput Tests
# =============================================================================

class TestTestAgentInput:
    """Tests for TestAgentInput model."""

    def test_minimal_valid_input(self, sample_artifact):
        """Test creating input with only required fields."""
        input_data = TestAgentInput(
            run_id="run_123",
            artifact=sample_artifact,
            workspace_root="/workspace/backend",
            dev_report_path="artifacts/backend/dev/route_sales_by_region.dev_report.json",
        )
        assert input_data.run_id == "run_123"
        assert input_data.artifact.id == "route_sales_by_region"
        assert input_data.test_report_dir == "artifacts/qa/tests"  # default

    def test_full_input(self, sample_artifact):
        """Test creating input with all fields."""
        input_data = TestAgentInput(
            run_id="run_456",
            artifact=sample_artifact,
            workspace_root="/workspace/backend",
            dev_report_path="artifacts/backend/dev/route_sales_by_region.dev_report.json",
            backend_manifest_path="artifacts/backend/manifest.json",
            test_report_dir="custom/test/dir",
            previous_test_summary="Previous tests failed due to missing mock",
            previous_qa_summary="QA found data mismatch on region field",
        )
        assert input_data.backend_manifest_path == "artifacts/backend/manifest.json"
        assert input_data.test_report_dir == "custom/test/dir"
        assert "missing mock" in input_data.previous_test_summary

    def test_input_with_helper_artifact(self, sample_helper_artifact):
        """Test input with helper artifact type."""
        input_data = TestAgentInput(
            run_id="run_789",
            artifact=sample_helper_artifact,
            workspace_root="/workspace/backend",
            dev_report_path="artifacts/backend/dev/helper_aggregate_sales.dev_report.json",
        )
        assert input_data.artifact.kind == BackendArtifactKind.helper

    def test_missing_required_field(self, sample_artifact):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TestAgentInput(
                run_id="run_123",
                artifact=sample_artifact,
                # missing workspace_root and dev_report_path
            )
        assert "workspace_root" in str(exc_info.value) or "dev_report_path" in str(exc_info.value)

    def test_input_serialization(self, sample_artifact):
        """Test that input serializes correctly."""
        input_data = TestAgentInput(
            run_id="run_123",
            artifact=sample_artifact,
            workspace_root="/workspace/backend",
            dev_report_path="artifacts/backend/dev/test.json",
        )
        data = input_data.model_dump()
        assert data["run_id"] == "run_123"
        assert data["artifact"]["id"] == "route_sales_by_region"


# =============================================================================
# TestAgentResult Tests
# =============================================================================

class TestTestAgentResult:
    """Tests for TestAgentResult model."""

    def test_success_result(self, sample_test_report):
        """Test creating a successful result."""
        result = TestAgentResult(
            run_id="run_123",
            artifact_id="route_sales_by_region",
            status="success",
            summary="All 3 tests passed for route_sales_by_region",
            test_report=sample_test_report,
        )
        assert result.status == "success"
        assert result.needs_dev_fix is False
        assert result.needs_spec_clarification is False
        assert result.error_details is None

    def test_failed_result_needs_dev_fix(self):
        """Test creating a failed result that needs dev fix."""
        failing_report = TestReport(
            artifact_id="route_sales_by_region",
            timestamp="2025-01-01T12:00:00Z",
            execution=TestExecutionResult(
                tests_run=4,
                tests_passed=2,
                tests_failed=2,
                failed_test_names=["test1", "test2"],
            ),
        )
        
        result = TestAgentResult(
            run_id="run_123",
            artifact_id="route_sales_by_region",
            status="failed",
            summary="2 tests failed due to incorrect response shape",
            test_report=failing_report,
            needs_dev_fix=True,
        )
        assert result.status == "failed"
        assert result.needs_dev_fix is True
        assert result.needs_spec_clarification is False

    def test_failed_result_needs_spec_clarification(self, sample_test_report):
        """Test creating a failed result that needs spec clarification."""
        result = TestAgentResult(
            run_id="run_123",
            artifact_id="route_sales_by_region",
            status="failed",
            summary="Cannot determine expected behavior from spec",
            test_report=sample_test_report,
            needs_spec_clarification=True,
        )
        assert result.needs_spec_clarification is True
        assert result.needs_dev_fix is False

    def test_partial_result(self, sample_test_report):
        """Test creating a partial result."""
        result = TestAgentResult(
            run_id="run_123",
            artifact_id="route_sales_by_region",
            status="partial",
            summary="Basic tests pass, but edge cases not yet covered",
            test_report=sample_test_report,
        )
        assert result.status == "partial"

    def test_result_with_error_details(self, sample_test_report):
        """Test result with error details when tests couldn't run."""
        result = TestAgentResult(
            run_id="run_123",
            artifact_id="route_sales_by_region",
            status="failed",
            summary="Could not execute tests",
            test_report=sample_test_report,
            error_details="npm test failed with exit code 1: SyntaxError in test file",
        )
        assert result.error_details is not None
        assert "SyntaxError" in result.error_details

    def test_invalid_status(self, sample_test_report):
        """Test that invalid status raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TestAgentResult(
                run_id="run_123",
                artifact_id="route_sales_by_region",
                status="invalid_status",  # not in Literal
                summary="Test summary",
                test_report=sample_test_report,
            )
        assert "status" in str(exc_info.value)

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TestAgentResult(
                run_id="run_123",
                # missing artifact_id, status, summary, test_report
            )
        errors = str(exc_info.value)
        assert "artifact_id" in errors or "status" in errors

    def test_result_serialization(self, sample_test_report):
        """Test that result serializes correctly."""
        result = TestAgentResult(
            run_id="run_123",
            artifact_id="route_sales_by_region",
            status="success",
            summary="All tests passed",
            test_report=sample_test_report,
        )
        data = result.model_dump()
        assert data["status"] == "success"
        assert "test_report" in data
        assert data["test_report"]["artifact_id"] == "route_sales_by_region"

    def test_result_json_round_trip(self, sample_test_report):
        """Test JSON serialization and deserialization."""
        original = TestAgentResult(
            run_id="run_123",
            artifact_id="route_sales_by_region",
            status="success",
            summary="All tests passed",
            test_report=sample_test_report,
            needs_dev_fix=False,
            needs_spec_clarification=False,
        )
        json_str = original.model_dump_json()
        restored = TestAgentResult.model_validate_json(json_str)
        
        assert restored.run_id == original.run_id
        assert restored.status == original.status
        assert restored.test_report.artifact_id == original.test_report.artifact_id
