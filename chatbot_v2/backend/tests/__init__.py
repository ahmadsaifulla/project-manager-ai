"""
Unit tests for schemas.py — Pydantic models, enums, and state definition.
"""
import pytest
from app.schemas import (
    TaskStatus,
    TaskPriority,
    Task,
    BlastRadiusOutput,
    PMOutput,
    TaskModel,
    PlanTasksOutput,
    ProjectState,
)


class TestTaskStatus:
    def test_enum_values(self):
        assert TaskStatus.TODO == "todo"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.DONE == "done"

    def test_enum_from_string(self):
        assert TaskStatus("todo") == TaskStatus.TODO
        assert TaskStatus("in_progress") == TaskStatus.IN_PROGRESS


class TestTaskPriority:
    def test_enum_values(self):
        assert TaskPriority.LOW == "low"
        assert TaskPriority.MEDIUM == "medium"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.CRITICAL == "critical"


class TestTask:
    def test_task_creation_with_defaults(self):
        task = Task(
            id="TSK-001",
            title="Setup DB",
            description="Create tables",
            estimated_effort="4 hours",
        )
        assert task.id == "TSK-001"
        assert task.status == TaskStatus.TODO
        assert task.assignee is None
        assert task.priority == TaskPriority.MEDIUM
        assert task.dependencies == []

    def test_task_creation_with_all_fields(self):
        task = Task(
            id="TSK-002",
            title="Build API",
            description="REST endpoints",
            status=TaskStatus.IN_PROGRESS,
            assignee="usr_john",
            priority=TaskPriority.HIGH,
            estimated_effort="8 hours",
            dependencies=["TSK-001"],
        )
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assignee == "usr_john"
        assert task.priority == TaskPriority.HIGH
        assert task.dependencies == ["TSK-001"]

    def test_task_model_dump(self):
        task = Task(
            id="TSK-001",
            title="Test",
            description="Desc",
            estimated_effort="2h",
        )
        dumped = task.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["id"] == "TSK-001"
        assert dumped["status"] == "todo"


class TestBlastRadiusOutput:
    def test_empty_layers(self):
        result = BlastRadiusOutput(affected_layers=[])
        assert result.affected_layers == []

    def test_with_layers(self):
        result = BlastRadiusOutput(affected_layers=["DB_LAYER.md", "API_LAYER.md"])
        assert len(result.affected_layers) == 2


class TestPMOutput:
    def test_pm_output_creation(self):
        result = PMOutput(
            detected_gaps=["Gap 1"],
            next_question="What is the target audience?",
            project_goals="### What We Have Done / Finalized\nNone",
            updated_draft_user_stories="# Stories\n- Story 1",
        )
        assert len(result.detected_gaps) == 1
        assert "target audience" in result.next_question

    def test_pm_output_empty_gaps(self):
        result = PMOutput(
            detected_gaps=[],
            next_question="All resolved!",
            project_goals="Goals here",
            updated_draft_user_stories="Stories",
        )
        assert result.detected_gaps == []


class TestPlanTasksOutput:
    def test_plan_tasks_output(self):
        result = PlanTasksOutput(
            prd="# PRD",
            technical_spec="# Spec",
            tasks=[
                TaskModel(
                    id="TSK-001",
                    title="Task 1",
                    description="Desc",
                    priority="high",
                    estimated_effort="4h",
                    dependencies=[],
                )
            ],
        )
        assert len(result.tasks) == 1
        assert result.tasks[0].id == "TSK-001"
