"""Engineering intelligence status endpoint (HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01)."""

from fastapi.testclient import TestClient

from main import app


def test_engineering_intelligence_status_is_local_context_only():
    with TestClient(app) as client:
        response = client.get("/internal/engineering-intelligence/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "LOCAL_CONTEXT_ONLY"
    assert body["external_ai_enabled"] is False
    assert body["provider_configured"] is False
    assert body["report_id"] == "HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03"
    assert body["truth"]["osrm_runtime"] == "NO_GO"
    assert body["truth"]["payments"] == "NO_GO"
    assert body["truth"]["dossier_spine"] == "PARALLEL_NOT_WIRED"
    assert body["truth"]["secret_key_guard"] in {"PENDING", "CONFIGURED"}
