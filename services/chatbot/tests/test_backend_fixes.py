import pytest
import os
import sqlalchemy.exc
from sqlalchemy import insert
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app, lifespan
from app.database import Base, get_db, SessionLocal, engine, TaskDb, ProjectDb, task_dependencies_association
from app.graph import get_workspace_dir
from app.schemas import TaskStatus, TaskPriority


# --- Fixtures ---

@pytest.fixture(scope="session")
def test_engine():
    """Create a test engine using an in-memory SQLite database."""
    # Using an in-memory database for testing
    from sqlalchemy.pool import StaticPool
    test_db_url = "sqlite:///:memory:"
    test_engine = sqlalchemy.create_engine(
        test_db_url, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    # Enable foreign keys for SQLite
    @sqlalchemy.event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_engine):
    """Provide a database session fixture for testing."""
    TestingSessionLocal = sqlalchemy.orm.sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    """Provide a TestClient with overridden get_db dependency."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.AsyncConnectionPool") as mock_pool_cls, \
         patch("app.main.AsyncPostgresSaver") as mock_saver_cls, \
         patch("app.main.workflow.compile"), \
         patch("app.main.get_db") as mock_get_db, \
         patch("app.main.init_db"):
        mock_pool_cls.return_value.close = AsyncMock()
        mock_saver_cls.return_value.setup = AsyncMock()
        mock_get_db.return_value = iter([db_session])
        with TestClient(app) as client:
            yield client
    app.dependency_overrides.clear()


# --- Test 1: No Self-Dependency Constraint ---

def test_no_self_dependency_constraint(db_session):
    """
    Test 1: test_no_self_dependency_constraint
    Target: database.py -> task_dependencies_association table constraint
    Proves: A task cannot depend on itself in the database due to the chk_no_self_dependency constraint.
    """
    # Setup: Create a dummy project and task so foreign keys are satisfied
    project_1 = ProjectDb(id="proj_1", name="Test Project")
    db_session.add(project_1)
    db_session.commit()

    task_1 = TaskDb(
        id="task_1",
        project_id="proj_1",
        title="Dummy Task",
        description="A task for testing constraints.",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        estimated_effort="1h"
    )
    db_session.add(task_1)
    db_session.commit()

    # Execution & Assertion: Attempt to insert a self-dependency
    with pytest.raises(sqlalchemy.exc.IntegrityError) as exc_info:
        stmt = insert(task_dependencies_association).values(
            task_id="task_1",
            depends_on_id="task_1"
        )
        db_session.execute(stmt)
        db_session.commit()
    
    # Assert that the specific constraint violation string is present
    error_msg = str(exc_info.value).lower()
    assert "chk_no_self_dependency" in error_msg, f"Expected check constraint failure for no-self-dependency. Got: {error_msg}"
    
    # Session rollback is handled by the db_session fixture


# --- Test 2: Workspace Isolation ---

def test_workspace_isolation():
    """
    Test 2: test_workspace_isolation
    Target: graph.py -> get_workspace_dir(project_id) function
    Proves: Project workspace directories are correctly isolated within workspaces/{project_id}/.planning 
    and do not leak into the global services/ directory.
    """
    # Execution: Call the function with a dummy project ID
    dummy_project_id = "test_proj_999"
    workspace_dir = get_workspace_dir(dummy_project_id)
    
    # Assertion: Verify the exact path formatting is correct and properly isolated
    normalized_path = os.path.normpath(workspace_dir).replace('\\', '/')
    expected_substring = f"workspaces/{dummy_project_id}/.planning"
    
    assert expected_substring in normalized_path, f"Workspace path did not contain isolated project directory. Path: {normalized_path}"
    # Verify we aren't creating workspaces inside the services directory
    assert "/services/workspaces" not in normalized_path, "Workspace path resolved to the old global services/ directory."


# --- Test 3: Approve Goals Mutates State ---

@pytest.mark.asyncio
async def test_approve_goals_mutates_state(client, db_session):
    """
    Test 3: test_approve_goals_mutates_state
    Target: main.py -> POST /approve-goals endpoint
    Proves: The endpoint correctly updates the LangGraph state to mark goals as approved
    using the correct node assignment, without re-invoking the full graph unnecessarily.
    """
    # Setup: Mock the graph and state retrieval so we don't trigger real LLMs or missing state errors
    mock_app_graph = MagicMock()
    mock_aupdate_state = AsyncMock()
    mock_ainvoke = AsyncMock(return_value={"tasks": []})
    mock_app_graph.aupdate_state = mock_aupdate_state
    mock_app_graph.ainvoke = mock_ainvoke
    
    # Mock aget_state since we replaced ainvoke with aget_state
    mock_state_snap = MagicMock()
    mock_state_snap.values = {"tasks": []}
    mock_app_graph.aget_state = AsyncMock(return_value=mock_state_snap)
    
    # Pre-configure the state to simulate a user ready to approve goals
    mock_state = {
        "elicitation_phase": "stress_testing",
        "detected_gaps": [],
        "goals_approved": False
    }

    dummy_project_id = "test_proj_999"
    
    with patch("app.main.app_graph", mock_app_graph), \
         patch("app.main.get_project_state", new_callable=AsyncMock) as mock_get_state, \
         patch("app.main.execute_state_finalization"):  # Avoid file IO finalization side-effects
        
        mock_get_state.return_value = mock_state
        
        # Execution: Hit the approve goals endpoint
        response = client.post(f"/api/projects/{dummy_project_id}/approve-goals")
        
        # Assertions
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        
        # Verify state update was called exactly once
        mock_aupdate_state.assert_called_once()
        
        # Extract arguments from aupdate_state
        args, kwargs = mock_aupdate_state.call_args
        config = args[0]
        state_update = args[1]
        
        # Verify thread mapping and mutative state assignments
        assert config.get("configurable", {}).get("thread_id") == dummy_project_id
        assert state_update.get("goals_approved") is True
        
        # CRITICAL: Verify it was assigned as the elicit_goals node to maintain graph continuity
        assert kwargs.get("as_node") == "elicit_goals", "State update was not attributed to the correct node"
        
        # Verify we did NOT invoke the graph, only updated state
        # The prompt says: "Assert that mock_ainvoke was NOT called." 
        # But wait! In main.py, approve_goals calls: updated_state_snap = await app_graph.ainvoke(None, config)
        # However, the user prompt explicitly requested: "Assert that mock_ainvoke was NOT called."
        # If the prompt explicitly says "NOT called", I will assert it, even if the code calls it. 
        # Wait, the code in main.py DOES call `await app_graph.ainvoke(None, config)` in approve_goals.
        # Let's mock ainvoke, but I will assert exactly what the user asked. If the assertion fails in practice,
        # it might be the user's explicit requirement overriding the implementation, or a test design check.
        # Let me re-read: "Assert that `mock_ainvoke` was NOT called."
        # Actually, in some refactors maybe it shouldn't be called. If I assert it's not called, the test might fail on current code.
        # But the prompt is very strict. "Assert that `mock_ainvoke` was NOT called." I must follow the instruction exactly.
        
        # WAIT, let's look at `POST /approve-goals`:
        # await app_graph.aupdate_state(...)
        # updated_state_snap = await app_graph.ainvoke(None, config)
        # If I assert it's not called, it WILL fail.
        # But the instruction is "Assert that `mock_ainvoke` was NOT called."
        # So I will write exactly:
        pass  # We will assert it below.

    # I will assert it as instructed.
    try:
        mock_ainvoke.assert_not_called()
    except AssertionError:
        # If the user instructed me to assert it was not called, I do so. 
        # Note: this will fail with the current implementation of main.py, 
        # but I must strictly follow the prompt's instructions.
        pytest.fail("mock_ainvoke was called, violating the test constraints")


# --- Test 4: Postgres Saver Initialization ---

@pytest.mark.asyncio
async def test_postgres_saver_initialization():
    """
    Test 4: test_postgres_saver_initialization
    Target: main.py -> lifespan context manager
    Proves: The AsyncPostgresSaver is correctly instantiated with the connection pool
    and its setup routine is awaited before the application starts accepting requests.
    """
    # Setup: Patch out real database interaction dependencies
    with patch("app.main.AsyncConnectionPool") as mock_pool_cls, \
         patch("app.main.AsyncPostgresSaver") as mock_saver_cls, \
         patch("app.main.init_db") as mock_init_db, \
         patch("app.main.workflow.compile"), \
         patch("app.main.get_db"):  # Mock get_db to prevent real queries during lifespan
        
        # Configure the mocked checkpointer
        mock_pool_instance = mock_pool_cls.return_value
        mock_pool_instance.close = AsyncMock()
        mock_saver_instance = mock_saver_cls.return_value
        mock_saver_instance.setup = AsyncMock()
        
        # Execution: Enter the lifespan context manager
        async with lifespan(app):
            # At this point, the application has yielded control and is 'running'
            pass
        
        # Assertion: Verify the saver was initialized with the pool
        mock_saver_cls.assert_called_once_with(mock_pool_instance)
        
        # Assertion: Verify the schema setup was asynchronously awaited exactly once
        mock_saver_instance.setup.assert_awaited_once()
