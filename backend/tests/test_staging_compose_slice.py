"""Staging stack artifacts — file presence only."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_staging_compose_exists():
    compose = REPO_ROOT / "infra" / "staging" / "docker" / "docker-compose.yml"
    body = compose.read_text(encoding="utf-8")
    assert compose.is_file()
    assert "halfapp/api:staging" in body
    assert "osrm-routed" in body
    assert "/healthz" in body


def test_backend_dockerfile_exists():
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    text = dockerfile.read_text(encoding="utf-8")
    assert "uvicorn" in text
    assert "healthz" in text
