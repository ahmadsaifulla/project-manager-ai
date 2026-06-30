"""
Unit tests for database.py — SQLAlchemy models and DB operations.
"""
import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, UserDb, TaskDb, task_dependencies_association
from app.schemas import TaskStatus, TaskPriority


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestUserDb:
    def test_create_user(self, db_session):
        user = UserDb(id="usr_1", name="Test User", email="test@test.com")
        db_session.add(user)
        db_session.commit()

        fetched = db_session.query(UserDb).filter_by(id="usr_1").first()
        assert fetched is not None
        assert fetched.name == "Test User"
        assert fetched.email == "test@test.com"
        assert fetched.avatar_url is None

    def test_unique_email_constraint(self, db_session):
        user1 = UserDb(id="usr_1", name="User 1", email="same@test.com")
        user2 = UserDb(id="usr_2", name="User 2", email="same@test.com")
        db_session.add(user1)
        db_session.commit()
        db_session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestTaskDb:
    def test_create_task(self, db_session):
        task = TaskDb(
            id="TSK-001",
            project_id="proj-1",
            title="Setup DB",
            description="Create tables",
            estimated_effort="4 hours",
        )
        db_session.add(task)
        db_session.commit()

        fetched = db_session.query(TaskDb).filter_by(id="TSK-001").first()
        assert fetched is not None
        assert fetched.title == "Setup DB"
        assert fetched.status == TaskStatus.TODO
        assert fetched.priority == TaskPriority.MEDIUM

    def test_task_dependencies(self, db_session):
        task1 = TaskDb(
            id="TSK-001", project_id="proj-1", title="T1",
            description="D1", estimated_effort="2h",
        )
        task2 = TaskDb(
            id="TSK-002", project_id="proj-1", title="T2",
            description="D2", estimated_effort="3h",
        )
        db_session.add_all([task1, task2])
        db_session.commit()

        # Add dependency: task2 depends on task1
        task2.dependencies.append(task1)
        db_session.commit()

        fetched = db_session.query(TaskDb).filter_by(id="TSK-002").first()
        assert len(fetched.dependencies) == 1
        assert fetched.dependencies[0].id == "TSK-001"

    def test_task_with_assignee(self, db_session):
        user = UserDb(id="usr_1", name="Dev", email="dev@test.com")
        db_session.add(user)
        db_session.commit()

        task = TaskDb(
            id="TSK-001", project_id="proj-1", title="T1",
            description="D1", estimated_effort="4h", assignee="usr_1",
        )
        db_session.add(task)
        db_session.commit()

        fetched = db_session.query(TaskDb).filter_by(id="TSK-001").first()
        assert fetched.assignee == "usr_1"
        assert fetched.assigned_user.name == "Dev"

    def test_cascade_delete_dependencies(self, db_session):
        task1 = TaskDb(
            id="TSK-001", project_id="proj-1", title="T1",
            description="D1", estimated_effort="2h",
        )
        task2 = TaskDb(
            id="TSK-002", project_id="proj-1", title="T2",
            description="D2", estimated_effort="3h",
        )
        db_session.add_all([task1, task2])
        db_session.commit()
        task2.dependencies.append(task1)
        db_session.commit()

        # Delete task1 — should cascade to dependency junction
        db_session.delete(task1)
        db_session.commit()

        fetched = db_session.query(TaskDb).filter_by(id="TSK-002").first()
        assert fetched is not None
        assert len(fetched.dependencies) == 0
