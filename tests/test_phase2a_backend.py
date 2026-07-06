"""
Phase 2A — Backend & Database Agent Test Suite
Tests: BE-001 through BE-010, DEV-001 through DEV-003, LG-001 through LG-007, DB-001 through DB-005
"""
import os
import sys
import json
import time
import pytest
import httpx

# ─── Configuration ──────────────────────────────────────────────────────────

CHATBOT_URL = "http://localhost:8001"
DEVELOPER_URL = "http://localhost:8002"
ORCHESTRATOR_URL = "http://localhost:8000"
TEST_PROJECT_ID = f"qa-test-{int(time.time())}"

# ─── Chatbot Endpoint Unit Tests ────────────────────────────────────────────

class TestChatbotEndpoints:
    """BE-001 through BE-010: Chatbot Node HTTP endpoint tests."""

    def test_BE001_list_projects(self):
        """BE-001: GET /api/projects returns 200 + JSON array."""
        r = httpx.get(f"{CHATBOT_URL}/api/projects", timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"  ✅ BE-001 PASS — {len(data)} projects returned")

    def test_BE002_create_project(self):
        """BE-002: POST /api/projects creates and returns project."""
        payload = {
            "id": TEST_PROJECT_ID,
            "name": "QA Test Project",
            "description": "Created by Phase 2A test suite"
        }
        r = httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["id"] == TEST_PROJECT_ID
        assert data["name"] == "QA Test Project"
        assert data["status"] == "listening"
        print(f"  ✅ BE-002 PASS — Project '{TEST_PROJECT_ID}' created")

    def test_BE003_get_project(self):
        """BE-003: GET /api/projects/{id} returns merged DB+Graph state."""
        payload = {
            "id": f"{TEST_PROJECT_ID}-get",
            "name": "GET Test",
            "description": "Test"
        }
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        r = httpx.get(f"{CHATBOT_URL}/api/projects/{TEST_PROJECT_ID}-get", timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "elicitation_phase" in data, "Missing graph state field"
        assert "name" in data, "Missing DB metadata field"
        assert data["elicitation_phase"] == "listening"
        print(f"  ✅ BE-003 PASS — Merged state returned with {len(data)} fields")

    def test_BE004_get_nonexistent_project(self):
        """BE-004: GET /api/projects/nonexistent returns 404."""
        r = httpx.get(f"{CHATBOT_URL}/api/projects/nonexistent-project-xyz", timeout=10)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        print(f"  ✅ BE-004 PASS — 404 returned for nonexistent project")

    def test_BE006_empty_message(self):
        """BE-006: POST /api/projects/{id}/messages with empty content returns 400."""
        payload = {
            "id": f"{TEST_PROJECT_ID}-msg",
            "name": "Msg Test",
            "description": "Test"
        }
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        r = httpx.post(
            f"{CHATBOT_URL}/api/projects/{TEST_PROJECT_ID}-msg/messages",
            json={"content": ""},
            timeout=10
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        print(f"  ✅ BE-006 PASS — 400 returned for empty message")

    def test_BE007_finish_sharing_valid(self):
        """BE-007: POST finish-sharing in listening phase transitions to stress_testing."""
        proj_id = f"finish-{int(time.time())}"
        payload = {"id": proj_id, "name": "Finish Test", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        r = httpx.post(f"{CHATBOT_URL}/api/projects/{proj_id}/finish-sharing", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["elicitation_phase"] == "stress_testing", f"Expected stress_testing, got {data['elicitation_phase']}"
        print(f"  ✅ BE-007 PASS — Phase transitioned to stress_testing")

    def test_BE008_finish_sharing_wrong_phase(self):
        """BE-008: POST finish-sharing when NOT in listening returns 400."""
        proj_id = f"phase-{int(time.time())}"
        payload = {"id": proj_id, "name": "Phase Test", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        r1 = httpx.post(f"{CHATBOT_URL}/api/projects/{proj_id}/finish-sharing", timeout=10)
        assert r1.status_code == 200, f"First finish-sharing failed: {r1.text}"
        
        r2 = httpx.post(f"{CHATBOT_URL}/api/projects/{proj_id}/finish-sharing", timeout=10)
        assert r2.status_code == 400, f"Expected 400 on double finish-sharing, got {r2.status_code}"
        print(f"  ✅ BE-008 PASS — 400 returned for non-listening phase")

    def test_BE009_get_project_tasks(self):
        """BE-009: GET /api/projects/{id}/tasks returns task array."""
        proj_id = f"tasks-{int(time.time())}"
        payload = {"id": proj_id, "name": "Task Test", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        r = httpx.get(f"{CHATBOT_URL}/api/projects/{proj_id}/tasks", timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"  ✅ BE-009 PASS — Tasks endpoint returned {len(data)} tasks")

    def test_BE010_get_users(self):
        """BE-010: GET /api/users returns user array with seeded user."""
        r = httpx.get(f"{CHATBOT_URL}/api/users", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "Expected at least 1 seeded user"
        assert any(u["id"] == "usr_default" for u in data), "Missing seeded usr_default"
        print(f"  ✅ BE-010 PASS — {len(data)} users returned, usr_default confirmed")


# ─── Developer Node Unit Tests ──────────────────────────────────────────────

class TestDeveloperEndpoints:
    """DEV-001 through DEV-003: Developer Node HTTP endpoint tests."""

    def test_DEV001_health_check(self):
        """DEV-001: GET / returns ok."""
        r = httpx.get(f"{DEVELOPER_URL}/", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        print(f"  ✅ DEV-001 PASS — Developer node healthy")

    def test_DEV003_missing_fields(self):
        """DEV-003: POST /api/qc/evaluate with missing fields returns 422."""
        r = httpx.post(
            f"{DEVELOPER_URL}/api/qc/evaluate",
            json={"task_id": "t1"},
            timeout=10
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
        print(f"  ✅ DEV-003 PASS — 422 returned for missing fields")


# ─── LangGraph State Machine Whitebox Tests ──────────────────────────────────

class TestLangGraphWhitebox:
    """LG-001 through LG-007: Pure function tests on graph logic."""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        chatbot_path = os.path.join(os.path.dirname(__file__), "..", "services", "chatbot")
        if chatbot_path not in sys.path:
            sys.path.insert(0, os.path.abspath(chatbot_path))

    def test_LG001_valid_dag(self):
        """LG-001: validate_no_cycles with valid DAG returns True."""
        from app.schemas import Task, TaskStatus, TaskPriority
        from app.graph import validate_no_cycles
        
        tasks = [
            Task(id="A", title="A", description="A", status=TaskStatus.TODO,
                 priority=TaskPriority.MEDIUM, estimated_effort="1h", dependencies=["B"]),
            Task(id="B", title="B", description="B", status=TaskStatus.TODO,
                 priority=TaskPriority.MEDIUM, estimated_effort="1h", dependencies=["C"]),
            Task(id="C", title="C", description="C", status=TaskStatus.TODO,
                 priority=TaskPriority.MEDIUM, estimated_effort="1h", dependencies=[]),
        ]
        assert validate_no_cycles(tasks) == True
        print(f"  ✅ LG-001 PASS — Valid DAG correctly validated")

    def test_LG002_cyclic_graph(self):
        """LG-002: validate_no_cycles with cycle returns False."""
        from app.schemas import Task, TaskStatus, TaskPriority
        from app.graph import validate_no_cycles
        
        tasks = [
            Task(id="A", title="A", description="A", status=TaskStatus.TODO,
                 priority=TaskPriority.MEDIUM, estimated_effort="1h", dependencies=["B"]),
            Task(id="B", title="B", description="B", status=TaskStatus.TODO,
                 priority=TaskPriority.MEDIUM, estimated_effort="1h", dependencies=["A"]),
        ]
        assert validate_no_cycles(tasks) == False
        print(f"  ✅ LG-002 PASS — Cycle correctly detected")

    def test_LG003_empty_graph(self):
        """LG-003: validate_no_cycles with empty list returns True."""
        from app.graph import validate_no_cycles
        assert validate_no_cycles([]) == True
        print(f"  ✅ LG-003 PASS — Empty graph validated")

    def test_LG004_route_approved(self):
        """LG-004: route_next_node with goals_approved=True returns plan_tasks."""
        from app.graph import route_next_node
        state = {"goals_approved": True}
        result = route_next_node(state)
        assert result == "plan_tasks", f"Expected 'plan_tasks', got '{result}'"
        print(f"  ✅ LG-004 PASS — Approved goals route to plan_tasks")

    def test_LG005_route_not_approved(self):
        """LG-005: route_next_node with goals_approved=False returns END."""
        from app.graph import route_next_node, END
        state = {"goals_approved": False}
        result = route_next_node(state)
        assert result == END, f"Expected END, got '{result}'"
        print(f"  ✅ LG-005 PASS — Unapproved goals route to END")

    def test_LG007_workspace_init(self):
        """LG-007: initialize_workspace creates .planning/ dir with layer files."""
        from app.graph import initialize_workspace, get_workspace_dir
        import shutil
        
        test_id = f"qa-workspace-{int(time.time())}"
        initialize_workspace(test_id)
        
        base_dir = get_workspace_dir(test_id)
        assert os.path.isdir(base_dir), f"Planning dir not created: {base_dir}"
        
        arch_dir = os.path.join(base_dir, "architecture")
        assert os.path.isdir(arch_dir), "architecture/ dir not created"
        
        expected_files = ["DB_LAYER.md", "API_LAYER.md", "SERVICES_LAYER.md", "FRONTEND_LAYER.md"]
        for f in expected_files:
            assert os.path.isfile(os.path.join(arch_dir, f)), f"Missing layer file: {f}"
        
        assert os.path.isfile(os.path.join(base_dir, "DRAFT_USER_STORIES.md"))
        assert os.path.isfile(os.path.join(base_dir, "TEMP_ARCHITECT.md"))
        
        print(f"  ✅ LG-007 PASS — Workspace initialized with all expected files")
        
        # Cleanup
        workspace_root = os.path.dirname(base_dir)
        if os.path.exists(workspace_root):
            shutil.rmtree(workspace_root)


# ─── Database CRUD Tests ────────────────────────────────────────────────────

class TestDatabaseCRUD:
    """DB-001 through DB-005: Database persistence tests."""

    def test_DB001_project_creation(self):
        """DB-001: ProjectDb creation persists row."""
        proj_id = f"db-test-{int(time.time())}"
        payload = {"id": proj_id, "name": "DB Test", "description": "CRUD test"}
        r = httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        assert r.status_code == 200
        
        r2 = httpx.get(f"{CHATBOT_URL}/api/projects", timeout=10)
        projects = r2.json()
        assert any(p["id"] == proj_id for p in projects), "Project not persisted"
        print(f"  ✅ DB-001 PASS — Project row persisted in DB")

    def test_DB002_task_query(self):
        """DB-002: Tasks can be queried for any project."""
        proj_id = f"db-task-{int(time.time())}"
        payload = {"id": proj_id, "name": "Task DB Test", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        r = httpx.get(f"{CHATBOT_URL}/api/projects/{proj_id}/tasks", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        print(f"  ✅ DB-002 PASS — Task query endpoint works for project")

    def test_DB005_user_seeding(self):
        """DB-005: usr_default exists after lifespan boot."""
        r = httpx.get(f"{CHATBOT_URL}/api/users", timeout=10)
        users = r.json()
        default_user = next((u for u in users if u["id"] == "usr_default"), None)
        assert default_user is not None, "usr_default not seeded"
        assert default_user["name"] == "Developer"
        assert default_user["email"] == "dev@localhost"
        print(f"  ✅ DB-005 PASS — usr_default seeded correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
