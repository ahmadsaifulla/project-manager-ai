"""
SQLAlchemy database models for the AI Project Manager.
Matches the PostgreSQL schema defined in ARCHITECTURE.md.
Uses SQLite by default for local development (swappable via DATABASE_URL env var).
"""
import os
from datetime import datetime, UTC
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum as SqlEnum,
    Table,
    JSON,
    Integer,
    CheckConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from .schemas import TaskStatus, TaskPriority


# ─── Database Connection ──────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/project_manager")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Association Table (Task Dependencies) ─────────────────────────────────

task_dependencies_association = Table(
    "task_dependencies",
    Base.metadata,
    Column(
        "task_id",
        String(50),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "depends_on_id",
        String(50),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    CheckConstraint('task_id <> depends_on_id', name='chk_no_self_dependency'),
)


# ─── User Model ───────────────────────────────────────────────────────────

class UserDb(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now(UTC))

    tasks = relationship("TaskDb", back_populates="assigned_user")


# ─── Project Model ────────────────────────────────────────────────────────

class ProjectDb(Base):
    __tablename__ = "projects"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="listening")  # listening, reviewing, approved, in-progress
    sprint = Column(String(100), nullable=True)
    progress = Column(Integer, default=0)
    due_date = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    accent_color = Column(String(20), default="#5B4EFF")
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    tasks = relationship("TaskDb", back_populates="project", cascade="all, delete-orphan")


# ─── Task Model ───────────────────────────────────────────────────────────

class TaskDb(Base):
    __tablename__ = "tasks"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SqlEnum(TaskStatus), default=TaskStatus.TODO)
    assignee = Column(
        String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    priority = Column(SqlEnum(TaskPriority), default=TaskPriority.MEDIUM)
    estimated_effort = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    assigned_user = relationship("UserDb", back_populates="tasks")
    project = relationship("ProjectDb", back_populates="tasks")

    # Self-referencing many-to-many relationship for task dependencies
    dependencies = relationship(
        "TaskDb",
        secondary=task_dependencies_association,
        primaryjoin="TaskDb.id==task_dependencies.c.task_id",
        secondaryjoin="TaskDb.id==task_dependencies.c.depends_on_id",
        backref="dependent_tasks",
    )


# ─── Database Helpers ──────────────────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a database session, ensuring cleanup on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
