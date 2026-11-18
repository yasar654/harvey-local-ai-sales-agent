"""Tests for the Ollama-only local inference path."""
import os

import pytest
import pytest_asyncio
from pydantic import ValidationError

from sellbird.brain import Brain
from sellbird.config import BrainConfig
from sellbird.ollama_runtime import OllamaClient, OllamaError, OllamaResult
from sellbird.state import StateManager


@pytest_asyncio.fixture
async def state(tmp_path):
    manager = StateManager(str(tmp_path / "test.db"))
    await manager.init_db()
    yield manager


def test_ollama_is_the_only_provider_and_default():
    config = BrainConfig()
    assert config.provider == "ollama"
    assert config.model == "qwen3:8b"
    for provider in ("claude", "codex", "openai", "anthropic", "gemini"):
        with pytest.raises(ValidationError):
            BrainConfig(provider=provider)


def test_ollama_endpoint_must_be_loopback():
    assert OllamaClient(model="qwen3:8b", base_url="http://127.0.0.1:11434").base_url == "http://127.0.0.1:11434"
    for url in (
        "https://127.0.0.1:11434",
        "http://ollama.example.com:11434",
        "http://192.168.1.20:11434",
        "http://user:pass@127.0.0.1:11434",
    ):
        with pytest.raises(ValueError):
            OllamaClient(model="qwen3:8b", base_url=url)


def test_cloud_model_tags_are_rejected():
    for model in ("qwen3:8b-cloud", "example:remote"):
        with pytest.raises(ValueError):
            OllamaClient(model=model, base_url="http://localhost:11434")


def test_custom_transports_are_rejected():
    async def fake_transport(*args, **kwargs):
        return "not local"
    with pytest.raises(ValueError, match="Custom transports are disabled"):
        Brain(state=None, brain_config=BrainConfig(), transport=fake_transport)


@pytest.mark.asyncio
async def test_brain_uses_local_ollama_and_records_usage(state, monkeypatch):
    brain = Brain(state)
    called = {}

    async def fake_generate(prompt, *, timeout=300, expect_json=False):
        called["prompt"] = prompt
        called["expect_json"] = expect_json
        return OllamaResult(
            text='{"ok": true}',
            model="qwen3:8b",
            duration_ms=42,
            input_tokens=12,
            output_tokens=8,
        )

    async def no_subprocess(*args, **kwargs):
        raise AssertionError("No Claude/Codex subprocess may start")

    monkeypatch.setattr(brain.ollama, "generate", fake_generate)
    monkeypatch.setattr("asyncio.create_subprocess_exec", no_subprocess)

    assert await brain.think("return JSON", expect_json=True, agent="writer", task="email") == '{"ok": true}'
    assert called == {"prompt": "return JSON", "expect_json": True}
    assert await state.get_usage_today("ollama") == 1
    usage = await state.usage_by_provider(days=1)
    assert len(usage) == 1
    assert usage[0]["provider"] == "ollama"
    assert usage[0]["output_tokens"] == 8
    assert usage[0]["cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_ollama_unavailable_pauses_without_fallback(state, monkeypatch):
    brain = Brain(state)

    async def offline(*args, **kwargs):
        raise OllamaError("Local Ollama is unavailable; no cloud fallback is permitted.")

    async def no_subprocess(*args, **kwargs):
        raise AssertionError("Cloud/CLI fallback is forbidden")

    monkeypatch.setattr(brain.ollama, "preflight", offline)
    monkeypatch.setattr(brain.ollama, "generate", offline)
    monkeypatch.setattr("asyncio.create_subprocess_exec", no_subprocess)

    reason = await brain.preflight()
    assert "no cloud fallback" in reason
    assert brain.paused_reason
    assert await brain.think("generate an email") == ""


@pytest.mark.asyncio
async def test_preflight_recovers_when_local_ollama_returns(state, monkeypatch):
    brain = Brain(state)
    calls = 0

    async def health():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OllamaError("daemon stopped")
        return {"provider": "ollama-local", "model": "qwen3:8b"}

    monkeypatch.setattr(brain.ollama, "preflight", health)
    assert await brain.preflight() == "daemon stopped"
    assert brain.paused_reason
    assert await brain.preflight() == ""
    assert not brain.paused_reason
