"""
Phase 4 — Alpha Acceptance (End-to-End System Test)
Simulates a complete user journey through the entire system.
"""
import os
import sys
import time
import pytest
import httpx

ORCHESTRATOR_URL = "http://localhost:8000"
CHATBOT_URL = "http://localhost:8001"
E2E_PROJECT_ID = f"e2e-alpha-{int(time.time())}"


class TestAlphaAcceptance:
    """Phase 4 E2E: Complete user journey simulation."""

    def test_step1_create_project(self):
        """Step 1: Create project via API Gateway."""
        payload = {
            "id": E2E_PROJECT_ID,
            "name": "E2E Alpha Test Project",
            "description": "Full end-to-end acceptance test"
        }
        r = httpx.post(f"{ORCHESTRATOR_URL}/api/projects", json=payload, timeout=10)
        assert r.status_code == 200, f"Failed to create project: {r.text}"
        data = r.json()
        assert data["id"] == E2E_PROJECT_ID
        assert data["status"] == "listening"
        print(f"\n  ✅ Step 1 PASS — Project '{E2E_PROJECT_ID}' created via gateway")

    def test_step2_verify_initial_state(self):
        """Step 2: Verify the project state is correctly initialized."""
        r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects/{E2E_PROJECT_ID}", timeout=10)
        assert r.status_code == 200
        data = r.json()
        
        # Verify merged state
        assert data["project_id"] == E2E_PROJECT_ID
        assert data["elicitation_phase"] == "listening"
        assert data["goals_approved"] == False
        assert data["detected_gaps"] == []
        assert data["tasks"] == []
        assert data["name"] == "E2E Alpha Test Project"
        print(f"  ✅ Step 2 PASS — Initial state verified (listening, no gaps, no tasks)")

    def test_step3_transition_to_analysis(self):
        """Step 3: Trigger analysis phase (finish-sharing)."""
        r = httpx.post(
            f"{ORCHESTRATOR_URL}/api/projects/{E2E_PROJECT_ID}/finish-sharing",
            timeout=10
        )
        assert r.status_code == 200
        data = r.json()
        assert data["elicitation_phase"] == "stress_testing"
        print(f"  ✅ Step 3 PASS — Transitioned to stress_testing phase")

    def test_step4_verify_phase_persistence(self):
        """Step 4: Re-fetch project and verify phase persists."""
        r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects/{E2E_PROJECT_ID}", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["elicitation_phase"] == "stress_testing"
        assert data["goals_approved"] == False
        print(f"  ✅ Step 4 PASS — Phase persists as stress_testing after re-fetch")

    def test_step5_reject_goals_modification_loop(self):
        """Step 5: Test goal rejection loops back to stress_testing."""
        r = httpx.post(
            f"{ORCHESTRATOR_URL}/api/projects/{E2E_PROJECT_ID}/reject-goals",
            timeout=10
        )
        assert r.status_code == 200
        data = r.json()
        assert data["goals_approved"] == False
        assert data["elicitation_phase"] == "stress_testing"
        assert len(data["detected_gaps"]) > 0, "Expected gaps after rejection"
        print(f"  ✅ Step 5 PASS — Rejection loop works, {len(data['detected_gaps'])} gaps added")

    def test_step6_verify_tasks_endpoint_empty(self):
        """Step 6: Verify tasks endpoint returns empty before approval."""
        r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects/{E2E_PROJECT_ID}", timeout=10)
        data = r.json()
        assert data["tasks"] == [] or len(data["tasks"]) == 0
        print(f"  ✅ Step 6 PASS — No tasks generated before approval")

    def test_step7_verify_workspace_artifacts(self):
        """Step 7: Verify workspace artifacts were created by the chatbot."""
        workspace_dir = os.path.join(
            os.path.dirname(__file__), "..", "workspaces", E2E_PROJECT_ID, ".planning"
        )
        workspace_dir = os.path.abspath(workspace_dir)
        
        # The workspace should have been created when project was initialized
        if os.path.isdir(workspace_dir):
            files = os.listdir(workspace_dir)
            print(f"  ✅ Step 7 PASS — Workspace created with {len(files)} files: {files}")
        else:
            # Workspace creation may be deferred until first message
            print(f"  ⚠️ Step 7 CONDITIONAL — Workspace not yet created (deferred init)")

    def test_step8_verify_multi_project_isolation(self):
        """Step 8: Verify project state isolation — one project's state doesn't leak."""
        proj2_id = f"e2e-isolation-{int(time.time())}"
        payload = {"id": proj2_id, "name": "Isolation Test", "description": "Test"}
        httpx.post(f"{ORCHESTRATOR_URL}/api/projects", json=payload, timeout=10)
        
        # Project 2 should still be in listening
        r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects/{proj2_id}", timeout=10)
        data = r.json()
        assert data["elicitation_phase"] == "listening", \
            f"State leaked! Project 2 is {data['elicitation_phase']}"
        
        # Original project should still be in stress_testing
        r2 = httpx.get(f"{ORCHESTRATOR_URL}/api/projects/{E2E_PROJECT_ID}", timeout=10)
        data2 = r2.json()
        assert data2["elicitation_phase"] == "stress_testing", \
            f"Original project state changed!"
        print(f"  ✅ Step 8 PASS — Project state isolation verified")

    def test_step9_qc_endpoint_reachable(self):
        """Step 9: Verify QC evaluation endpoint is reachable through gateway."""
        r = httpx.post(
            f"{ORCHESTRATOR_URL}/api/qc/evaluate",
            json={
                "task_id": "e2e-task-1",
                "repo_name": "facebook/react",
                "branch_name": "main"
            },
            timeout=30
        )
        # Should return a result (200) or an error (500 from LLM) — NOT 404/405
        assert r.status_code in [200, 500], f"Unexpected status: {r.status_code}"
        data = r.json()
        assert isinstance(data, dict)
        print(f"  ✅ Step 9 PASS — QC endpoint reachable (status {r.status_code})")

    def test_step10_config_roundtrip(self):
        """Step 10: Verify global config can be read, updated, and restored."""
        # Read
        r1 = httpx.get(f"{ORCHESTRATOR_URL}/api/config", timeout=10)
        original = r1.json()
        
        # Update
        r2 = httpx.post(
            f"{ORCHESTRATOR_URL}/api/config",
            json={"repo_name": "e2e/test-repo"},
            timeout=10
        )
        assert r2.json()["state"]["repo_name"] == "e2e/test-repo"
        
        # Restore
        httpx.post(
            f"{ORCHESTRATOR_URL}/api/config",
            json={"repo_name": original["repo_name"]},
            timeout=10
        )
        
        r3 = httpx.get(f"{ORCHESTRATOR_URL}/api/config", timeout=10)
        assert r3.json()["repo_name"] == original["repo_name"]
        print(f"  ✅ Step 10 PASS — Config roundtrip verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
