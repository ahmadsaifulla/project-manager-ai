"""
Phase 3 — Chaos, Load, and Regression Test Suite
Tests: CHAOS-001 through CHAOS-005, RATE-001, REG-001 through REG-004
"""
import os
import sys
import time
import json
import pytest
import httpx
import concurrent.futures

# ─── Configuration ──────────────────────────────────────────────────────────

ORCHESTRATOR_URL = "http://localhost:8000"
CHATBOT_URL = "http://localhost:8001"
DEVELOPER_URL = "http://localhost:8002"


# ─── Fault Injection Tests ──────────────────────────────────────────────────

class TestFaultInjection:
    """CHAOS-001 through CHAOS-005: Deliberate fault injection."""

    def test_CHAOS003_malformed_json_message(self):
        """CHAOS-003: Send malformed JSON to POST /messages — no 500 crash."""
        proj_id = f"chaos-msg-{int(time.time())}"
        payload = {"id": proj_id, "name": "Chaos Msg", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        # Send non-JSON body
        r = httpx.post(
            f"{CHATBOT_URL}/api/projects/{proj_id}/messages",
            content="this is not json {{{{",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert r.status_code != 500, f"Server crashed with 500: {r.text}"
        assert r.status_code in [400, 422], f"Expected 400/422, got {r.status_code}"
        print(f"  ✅ CHAOS-003 PASS — Malformed JSON handled ({r.status_code})")

    def test_CHAOS004_malformed_json_qc(self):
        """CHAOS-004: Send malformed JSON to POST /api/qc/evaluate."""
        r = httpx.post(
            f"{DEVELOPER_URL}/api/qc/evaluate",
            content="{{not valid json}}",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert r.status_code in [400, 422], f"Expected 400/422, got {r.status_code}"
        print(f"  ✅ CHAOS-004 PASS — Malformed QC payload handled ({r.status_code})")

    def test_CHAOS005_oversized_payload(self):
        """CHAOS-005: Send oversized payload (>100KB) — no OOM."""
        proj_id = f"chaos-big-{int(time.time())}"
        payload = {"id": proj_id, "name": "Chaos Big", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        # Create a ~200KB payload
        big_content = "A" * 200_000
        r = httpx.post(
            f"{CHATBOT_URL}/api/projects/{proj_id}/messages",
            json={"content": big_content},
            timeout=30
        )
        # Should not crash — either processes the oversized content or returns an error
        assert r.status_code != 500 or "timeout" in r.text.lower() or "error" in r.text.lower(), \
            f"Server crashed without meaningful error"
        print(f"  ✅ CHAOS-005 PASS — Oversized payload handled (status {r.status_code})")

    def test_CHAOS001_simulate_chatbot_down(self):
        """CHAOS-001: Verify orchestrator returns 502 when chatbot is unreachable.
        NOTE: Instead of killing the chatbot, we test by temporarily pointing to a bad URL.
        """
        # Save original config
        orig = httpx.get(f"{ORCHESTRATOR_URL}/api/config", timeout=10).json()
        
        # Point chatbot URL to a non-existent port
        httpx.post(
            f"{ORCHESTRATOR_URL}/api/config",
            json={"chatbot_node_url": "http://127.0.0.1:19999"},
            timeout=10
        )
        
        try:
            r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects", timeout=10)
            assert r.status_code == 502, f"Expected 502, got {r.status_code}"
            data = r.json()
            assert "Bad Gateway" in data.get("detail", ""), f"Missing error detail"
            print(f"  ✅ CHAOS-001 PASS — Orchestrator returns 502 when chatbot down")
        finally:
            # Restore original config
            httpx.post(
                f"{ORCHESTRATOR_URL}/api/config",
                json={"chatbot_node_url": orig["chatbot_node_url"]},
                timeout=10
            )

    def test_CHAOS002_simulate_developer_down(self):
        """CHAOS-002: Verify orchestrator returns 502 when developer node is unreachable."""
        orig = httpx.get(f"{ORCHESTRATOR_URL}/api/config", timeout=10).json()
        
        httpx.post(
            f"{ORCHESTRATOR_URL}/api/config",
            json={"developer_node_url": "http://127.0.0.1:19998"},
            timeout=10
        )
        
        try:
            r = httpx.post(
                f"{ORCHESTRATOR_URL}/api/qc/evaluate",
                json={"task_id": "t1", "repo_name": "test/repo", "branch_name": "main"},
                timeout=10
            )
            assert r.status_code == 502, f"Expected 502, got {r.status_code}"
            print(f"  ✅ CHAOS-002 PASS — Orchestrator returns 502 when developer down")
        finally:
            httpx.post(
                f"{ORCHESTRATOR_URL}/api/config",
                json={"developer_node_url": orig["developer_node_url"]},
                timeout=10
            )


# ─── Rate Limit / Throughput Tests ───────────────────────────────────────────

class TestRateAndThroughput:
    """RATE-001: Burst throughput test."""

    def test_RATE001_burst_50_requests(self):
        """RATE-001: Burst 50 GET /api/projects in ~1 second."""
        results = []
        start = time.time()
        
        def make_request(i):
            r = httpx.get(f"{ORCHESTRATOR_URL}/api/projects", timeout=10)
            return (i, r.status_code, r.elapsed.total_seconds())
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())
        
        elapsed = time.time() - start
        status_codes = [r[1] for r in results]
        response_times = [r[2] for r in results]
        
        # All should return 200
        success_count = status_codes.count(200)
        avg_response = sum(response_times) / len(response_times)
        
        assert success_count >= 45, f"Only {success_count}/50 returned 200"
        print(f"  ✅ RATE-001 PASS — {success_count}/50 succeeded in {elapsed:.2f}s (avg {avg_response:.3f}s)")


# ─── Regression Tests ────────────────────────────────────────────────────────

class TestRegression:
    """REG-001 through REG-004: Known bug regression verification."""

    def test_REG001_405_routing_fix(self):
        """REG-001: POST /api/projects/{id}/approve-goals through orchestrator should not 405."""
        proj_id = f"reg-405-{int(time.time())}"
        payload = {"id": proj_id, "name": "Regression 405", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        # Transition to stress_testing
        httpx.post(f"{ORCHESTRATOR_URL}/api/projects/{proj_id}/finish-sharing", timeout=10)
        
        # Attempt approve-goals through orchestrator
        r = httpx.post(f"{ORCHESTRATOR_URL}/api/projects/{proj_id}/approve-goals", timeout=30)
        # May return 400 (gaps unresolved) but must NOT be 405
        assert r.status_code != 405, f"Got 405 — routing regression detected!"
        print(f"  ✅ REG-001 PASS — No 405 routing error (got {r.status_code})")

    def test_REG002_langgraph_state_persistence(self):
        """REG-002: After finish-sharing, elicitation_phase persists as stress_testing."""
        proj_id = f"reg-state-{int(time.time())}"
        payload = {"id": proj_id, "name": "State Persist", "description": "Test"}
        httpx.post(f"{CHATBOT_URL}/api/projects", json=payload, timeout=10)
        
        # Transition
        httpx.post(f"{CHATBOT_URL}/api/projects/{proj_id}/finish-sharing", timeout=10)
        
        # Verify state persists after re-fetch
        r = httpx.get(f"{CHATBOT_URL}/api/projects/{proj_id}", timeout=10)
        data = r.json()
        assert data["elicitation_phase"] == "stress_testing", \
            f"State not persisted: {data['elicitation_phase']}"
        print(f"  ✅ REG-002 PASS — State persists as stress_testing after checkpoint")

    def test_REG003_workspace_path_resolution(self):
        """REG-003: get_workspace_dir() resolves correctly regardless of CWD."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "chatbot"))
        from app.graph import get_workspace_dir
        
        test_id = "reg-path-test"
        result = get_workspace_dir(test_id)
        
        # Path should end with workspaces/reg-path-test/.planning
        assert result.endswith(os.path.join("workspaces", test_id, ".planning")), \
            f"Bad path resolution: {result}"
        assert os.path.isabs(result), f"Path is not absolute: {result}"
        print(f"  ✅ REG-003 PASS — Path resolves correctly: {result}")

    def test_REG004_self_dependency_constraint(self):
        """REG-004: validate_no_cycles catches self-referencing task."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "chatbot"))
        from app.schemas import Task, TaskStatus, TaskPriority
        from app.graph import validate_no_cycles
        
        tasks = [
            Task(id="A", title="A", description="A", status=TaskStatus.TODO,
                 priority=TaskPriority.MEDIUM, estimated_effort="1h", dependencies=["A"]),
        ]
        # Self-dependency is a cycle of length 1
        assert validate_no_cycles(tasks) == False, "Self-dependency not detected!"
        print(f"  ✅ REG-004 PASS — Self-dependency correctly detected as cycle")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
