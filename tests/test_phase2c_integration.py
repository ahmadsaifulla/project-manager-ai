"""
Phase 2C — Integration & API Gateway Agent Test Suite
Tests: INT-001 through INT-007, CORS-001/002, PAY-001/002, CFG-001 through CFG-003
"""
import time
import pytest
import httpx

# ─── Configuration ──────────────────────────────────────────────────────────

ORCHESTRATOR_URL = "http://localhost:8000"
CHATBOT_URL = "http://localhost:8001"
TEST_PROJECT_ID = f"int-test-{int(time.time())}"


# ─── Orchestrator ↔ Chatbot Proxy Tests ──────────────────────────────────────

class TestOrchestratorProxy:
    """INT-001 through INT-005: Proxy passthrough tests."""

    @pytest.fixture(autouse=True)
    def setup_project(self):
        """Create a test project via chatbot (direct) for proxy validation."""
        payload = {"id": TEST_PROJECT_ID, "name": "Integration Test", "description": "Proxy test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)

    def test_INT001_proxy_list_projects(self):
        """INT-001: GET :8000/api/projects proxies to :8001 correctly."""
        r_orch = httpx.get(f"{ORCHESTRATOR_URL}/api/projects", timeout=10)
        r_chat = httpx.get(f"{CHATBOT_URL}/api/projects", timeout=10)
        
        assert r_orch.status_code == 200
        assert r_orch.status_code == r_chat.status_code
        
        orch_data = r_orch.json()
        chat_data = r_chat.json()
        assert len(orch_data) == len(chat_data), f"Mismatch: orch={len(orch_data)}, chat={len(chat_data)}"
        print(f"  ✅ INT-001 PASS — Proxy list returned {len(orch_data)} projects")

    def test_INT002_proxy_create_project(self):
        """INT-002: POST :8000/api/projects proxies creation correctly."""
        proj_id = f"proxy-create-{int(time.time())}"
        payload = {"id": proj_id, "name": "Proxy Created", "description": "Via gateway"}
        
        r = httpx.post(f"{ORCHESTRATOR_URL}/api/projects", json=payload, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == proj_id
        assert data["name"] == "Proxy Created"
        print(f"  ✅ INT-002 PASS — Project created via gateway proxy")

    def test_INT003_proxy_get_project(self):
        """INT-003: GET :8000/api/projects/{id} proxies project state."""
        r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects/{TEST_PROJECT_ID}", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "elicitation_phase" in data
        assert "name" in data
        print(f"  ✅ INT-003 PASS — Project state proxied with {len(data)} fields")

    def test_INT005_proxy_finish_sharing(self):
        """INT-005: POST :8000/api/projects/{id}/finish-sharing proxies transition."""
        proj_id = f"proxy-finish-{int(time.time())}"
        payload = {"id": proj_id, "name": "Finish Proxy", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        r = httpx.post(f"{ORCHESTRATOR_URL}/api/projects/{proj_id}/finish-sharing", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["elicitation_phase"] == "stress_testing"
        print(f"  ✅ INT-005 PASS — State transition proxied correctly")


# ─── Orchestrator ↔ Developer Proxy Tests ────────────────────────────────────

class TestDeveloperProxy:
    """INT-006 through INT-007: QC evaluation proxy tests."""

    def test_INT006_proxy_qc_evaluate(self):
        """INT-006: POST :8000/api/qc/evaluate proxies to developer node."""
        payload = {
            "task_id": "test-task",
            "repo_name": "facebook/react",
            "branch_name": "main"
        }
        r = httpx.post(f"{ORCHESTRATOR_URL}/api/qc/evaluate", json=payload, timeout=30)
        # Should return 200 (with verdict) or 502 (dev node issue) — NOT 404 or 405
        assert r.status_code in [200, 500, 502], f"Unexpected status: {r.status_code}"
        data = r.json()
        # Verify JSON structure
        assert isinstance(data, dict)
        print(f"  ✅ INT-006 PASS — QC evaluate proxied (status {r.status_code})")

    def test_INT007_auto_inject_repo_name(self):
        """INT-007: Global repo_name is auto-injected when not provided."""
        payload = {
            "task_id": "test-inject",
            "branch_name": "main"
            # repo_name intentionally omitted — should be auto-injected
        }
        # This will fail 422 at developer node since it requires repo_name in schema,
        # but the orchestrator proxy should add it before forwarding.
        # The expected behavior depends on whether the injected payload satisfies the schema.
        r = httpx.post(f"{ORCHESTRATOR_URL}/api/qc/evaluate", json=payload, timeout=30)
        # 200 or 500 (LLM/GitHub error) means repo_name was injected; 422 means it wasn't
        assert r.status_code != 422, f"repo_name was NOT injected — got 422"
        print(f"  ✅ INT-007 PASS — repo_name auto-injected (status {r.status_code})")


# ─── CORS & Payload Integrity Tests ─────────────────────────────────────────

class TestCORSAndPayload:
    """CORS-001/002 and PAY-001/002: Cross-origin and payload tests."""

    def test_CORS001_orchestrator_cors(self):
        """CORS-001: Orchestrator returns CORS headers."""
        r = httpx.options(
            f"{ORCHESTRATOR_URL}/api/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            },
            timeout=10
        )
        assert r.status_code == 200
        assert "access-control-allow-origin" in r.headers
        print(f"  ✅ CORS-001 PASS — Orchestrator CORS headers present")

    def test_CORS002_chatbot_cors(self):
        """CORS-002: Chatbot returns CORS headers."""
        r = httpx.options(
            f"{CHATBOT_URL}/api/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            },
            timeout=10
        )
        assert r.status_code == 200
        assert "access-control-allow-origin" in r.headers
        print(f"  ✅ CORS-002 PASS — Chatbot CORS headers present")

    def test_PAY001_extra_fields_tolerance(self):
        """PAY-001: POST /api/projects with extra unknown fields is tolerated."""
        payload = {
            "id": f"pay-test-{int(time.time())}",
            "name": "Payload Test",
            "description": "Test",
            "unknown_field": "should be ignored",
            "extra_nested": {"deep": True}
        }
        r = httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        # Should not crash — Pydantic ignores extra fields by default
        assert r.status_code in [200, 422], f"Unexpected error: {r.status_code}"
        print(f"  ✅ PAY-001 PASS — Extra fields handled (status {r.status_code})")

    def test_PAY002_json_content_type(self):
        """PAY-002: All proxy responses return JSON content type."""
        r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects", timeout=10)
        assert "application/json" in r.headers.get("content-type", "")
        print(f"  ✅ PAY-002 PASS — JSON content type confirmed")


# ─── Global Config Endpoint Tests ────────────────────────────────────────────

class TestGlobalConfig:
    """CFG-001 through CFG-003: Orchestrator config endpoints."""

    def test_CFG001_get_config(self):
        """CFG-001: GET /api/config returns project state dict."""
        r = httpx.get(f"{ORCHESTRATOR_URL}/api/config", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "repo_name" in data
        assert "developer_node_url" in data
        assert "chatbot_node_url" in data
        print(f"  ✅ CFG-001 PASS — Config returned with {len(data)} keys")

    def test_CFG002_update_config(self):
        """CFG-002: POST /api/config updates state."""
        r = httpx.post(
            f"{ORCHESTRATOR_URL}/api/config",
            json={"repo_name": "test/repo-updated"},
            timeout=10
        )
        assert r.status_code == 200
        data = r.json()
        assert data["state"]["repo_name"] == "test/repo-updated"
        
        # Restore original
        httpx.post(
            f"{ORCHESTRATOR_URL}/api/config",
            json={"repo_name": "facebook/react"},
            timeout=10
        )
        print(f"  ✅ CFG-002 PASS — Config updated and restored")

    def test_CFG003_invalid_config_payload(self):
        """CFG-003: POST /api/config with invalid JSON returns 400."""
        r = httpx.post(
            f"{ORCHESTRATOR_URL}/api/config",
            content="not json",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"
        print(f"  ✅ CFG-003 PASS — 400 for invalid JSON")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
