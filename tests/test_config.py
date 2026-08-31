"""Tests for environment-driven client configuration."""

from __future__ import annotations

import pytest

from querido_diario_mcp_server.config import DEFAULT_BASE_URL, load_config


def test_load_config_defaults_to_documented_production_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QD_API_BASE_URL", raising=False)

    config = load_config()

    assert config.base_url == DEFAULT_BASE_URL


def test_load_config_respects_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QD_API_BASE_URL", "http://localhost:8080/")

    config = load_config()

    assert config.base_url == "http://localhost:8080"
