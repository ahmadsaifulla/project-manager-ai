"""
Unit tests for graph.py — DAG validation, workspace initialization, and routing logic.
Tests that DO NOT require an LLM API key.
"""
import os
import shutil
import tempfile
import pytest
from app.schemas import Task, TaskStatus, TaskPriority, ProjectState
from app.graph import validate_no_cycles, initialize_workspace, route_next_node


class TestValidateNoCycles:
    """Tests for the DFS-based DAG cycle detection."""

    def test_empty_task_list(self):
        assert validate_no_cycles([]) is True

    def test_single_task_no_deps(self):
        tasks = [
            Task(id="TSK-001", title="A", description="D", estimated_effort="1h"),
        ]
        assert validate_no_cycles(tasks) is True

    def test_linear_chain(self):
        tasks = [
            Task(id="TSK-001", title="A", description="D", estimated_effort="1h", dependencies=[]),
            Task(id="TSK-002", title="B", description="D", estimated_effort="1h", dependencies=["TSK-001"]),
            Task(id="TSK-003", title="C", description="D", estimated_effort="1h", dependencies=["TSK-002"]),
        ]
        assert validate_no_cycles(tasks) is True

    def test_simple_cycle(self):
        tasks = [
            Task(id="TSK-001", title="A", description="D", estimated_effort="1h", dependencies=["TSK-002"]),
            Task(id="TSK-002", title="B", description="D", estimated_effort="1h", dependencies=["TSK-001"]),
        ]
        assert validate_no_cycles(tasks) is False

    def test_three_node_cycle(self):
        tasks = [
            Task(id="TSK-001", title="A", description="D", estimated_effort="1h", dependencies=["TSK-003"]),
            Task(id="TSK-002", title="B", description="D", estimated_effort="1h", dependencies=["TSK-001"]),
            Task(id="TSK-003", title="C", description="D", estimated_effort="1h", dependencies=["TSK-002"]),
        ]
        assert validate_no_cycles(tasks) is False

    def test_diamond_dag(self):
        """Diamond-shaped DAG (valid, not a cycle)."""
        tasks = [
            Task(id="TSK-001", title="A", description="D", estimated_effort="1h", dependencies=[]),
            Task(id="TSK-002", title="B", description="D", estimated_effort="1h", dependencies=["TSK-001"]),
            Task(id="TSK-003", title="C", description="D", estimated_effort="1h", dependencies=["TSK-001"]),
            Task(id="TSK-004", title="D", description="D", estimated_effort="1h", dependencies=["TSK-002", "TSK-003"]),
        ]
        assert validate_no_cycles(tasks) is True

    def test_invalid_dependency_reference(self):
        """Dependencies referencing non-existent tasks should be ignored, not crash."""
        tasks = [
            Task(id="TSK-001", title="A", description="D", estimated_effort="1h", dependencies=["TSK-MISSING"]),
        ]
        assert validate_no_cycles(tasks) is True


class TestInitializeWorkspace:
    """Tests for workspace directory/file creation."""

    def test_creates_all_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_workspace(tmpdir)

            # Check architecture directory
            arch_dir = os.path.join(tmpdir, "architecture")
            assert os.path.isdir(arch_dir)

            # Check all layer files
            for layer in ["DB_LAYER.md", "API_LAYER.md", "SERVICES_LAYER.md", "FRONTEND_LAYER.md"]:
                assert os.path.isfile(os.path.join(arch_dir, layer))

            # Check workspace files
            assert os.path.isfile(os.path.join(tmpdir, "DRAFT_USER_STORIES.md"))
            assert os.path.isfile(os.path.join(tmpdir, "TEMP_ARCHITECT.md"))

    def test_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pre-create a file with custom content
            draft_path = os.path.join(tmpdir, "DRAFT_USER_STORIES.md")
            with open(draft_path, "w") as f:
                f.write("CUSTOM CONTENT")

            initialize_workspace(tmpdir)

            # Verify it was NOT overwritten
            with open(draft_path, "r") as f:
                assert f.read() == "CUSTOM CONTENT"

    def test_idempotent(self):
        """Running initialize_workspace twice should not break anything."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_workspace(tmpdir)
            initialize_workspace(tmpdir)
            assert os.path.isfile(os.path.join(tmpdir, "DRAFT_USER_STORIES.md"))


class TestRouteNextNode:
    """Tests for the conditional router."""

    def test_routes_to_plan_tasks_when_approved(self):
        state = {"goals_approved": True}
        assert route_next_node(state) == "plan_tasks"

    def test_routes_to_end_when_not_approved(self):
        from langgraph.graph import END
        state = {"goals_approved": False}
        assert route_next_node(state) == END

    def test_routes_to_end_when_missing(self):
        from langgraph.graph import END
        state = {}
        assert route_next_node(state) == END
