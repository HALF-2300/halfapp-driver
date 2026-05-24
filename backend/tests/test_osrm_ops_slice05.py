"""Slice 05 ops artifacts — file presence only (no live OSRM required)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_slice05_healthcheck_scripts_exist():
    ps1 = REPO_ROOT / "scripts" / "osrm_healthcheck.ps1"
    sh = REPO_ROOT / "scripts" / "osrm_healthcheck.sh"
    assert ps1.is_file(), "missing scripts/osrm_healthcheck.ps1"
    assert sh.is_file(), "missing scripts/osrm_healthcheck.sh"
    assert "route/v1/driving" in ps1.read_text(encoding="utf-8")
    assert "route/v1/driving" in sh.read_text(encoding="utf-8")


def test_slice05_runbook_exists():
    doc = REPO_ROOT / "docs" / "HALFAPP_OSRM_OPS_ONLY_SLICE_05.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "OSRM_BASE_URL" in text
    assert "haversine_fallback" in text


def test_prepare_osrm_script_exists():
    script = REPO_ROOT / "infra" / "staging" / "osrm" / "prepare_osrm.sh"
    assert script.is_file()
    body = script.read_text(encoding="utf-8")
    assert "prepare-osrm-oregon.sh" in body


def test_self_hosted_routing_proof_v02_status_exists():
    doc = REPO_ROOT / "docs" / "SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md"
    assert doc.is_file()
    body = doc.read_text(encoding="utf-8")
    assert "OSRM runtime" in body
    assert "osrm_self_hosted" in body


def test_osrm_runtime_proof_v02_runbook_exists():
    doc = REPO_ROOT / "docs" / "OSRM_RUNTIME_PROOF_V0_2.md"
    assert doc.is_file()
    body = doc.read_text(encoding="utf-8")
    assert "osrm/osrm-backend" in body
    assert "overview=full" in body
    assert "routes[0].geometry" in body


def test_osrm_portland_compose_has_healthcheck():
    compose = REPO_ROOT / "docker" / "osrm-portland" / "docker-compose.yml"
    body = compose.read_text(encoding="utf-8")
    assert "healthcheck:" in body
    assert "route/v1/driving" in body
    assert "osrm/osrm-backend" in body
    assert "restart: always" in body
