"""Strictly local Ollama adapter for the Harvey/Sellbird Brain.

The adapter accepts loopback URLs only. It never retries against another
provider, endpoint, or cloud service. Install/pull the model before going
offline; all chat requests then go to the local Ollama daemon.
"""
from __future__ import annotations

import ipaddress
import os
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


class OllamaError(RuntimeError):
    """Ollama is unavailable, the model is missing, or local inference failed."""


@dataclass(frozen=True)
class OllamaResult:
    text: str
    model: str
    duration_ms: int
    input_tokens: int
    output_tokens: int


class OllamaClient:
    def __init__(self, model: str = "", base_url: str | None = None):
        self.model = (model or os.getenv("OLLAMA_MODEL", "qwen3:8b")).strip()
        raw_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).strip()
        self.base_url = self._validate_local_url(raw_url)
        if not self.model or any(ch.isspace() for ch in self.model):
            raise ValueError("OLLAMA_MODEL must be a non-empty Ollama model tag, e.g. qwen3:8b.")

    @staticmethod
    def _validate_local_url(value: str) -> str:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        loopback = host == "localhost"
        try:
            loopback = loopback or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if parsed.scheme != "http" or not loopback or parsed.username or parsed.password:
            raise ValueError(
                "OLLAMA_BASE_URL must be a loopback URL such as "
                "http://127.0.0.1:11434. Remote/cloud inference endpoints are disabled."
            )
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("OLLAMA_BASE_URL must contain only the local host and port.")
        return value.rstrip("/")

    def fingerprint(self) -> tuple[str, str]:
        return self.base_url, self.model

    async def preflight(self) -> dict:
        """Confirm the local daemon is reachable and the configured model exists."""
        try:
            async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaError(
                "Local Ollama is unavailable. Start Ollama and verify "
                f"{self.base_url}; no cloud fallback is permitted ({type(exc).__name__})."
            ) from exc
        names = {
            str(item.get("name") or item.get("model") or "")
            for item in payload.get("models", [])
            if isinstance(item, dict)
        }
        if self.model not in names:
            raise OllamaError(
                f"Model '{self.model}' is not installed locally. Run "
                f"'ollama pull {self.model}' while internet is available, then retry."
            )
        return {"provider": "ollama-local", "model": self.model, "base_url": self.base_url}

    async def generate(
        self, prompt: str, *, timeout: float = 300, expect_json: bool = False
    ) -> OllamaResult:
        started = time.monotonic()
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        if expect_json:
            body["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=body)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = str(exc.response.json().get("error", ""))
            except Exception:
                pass
            raise OllamaError(
                f"Local Ollama inference failed (HTTP {exc.response.status_code}). "
                f"{detail[:300]} No external provider was contacted."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaError(
                "Could not reach local Ollama for inference. Start the local daemon; "
                "the request was not sent to any cloud service."
            ) from exc

        text = str((payload.get("message") or {}).get("content") or "").strip()
        if not text:
            raise OllamaError("Ollama returned an empty local response.")
        duration_ms = int(payload.get("total_duration", 0) / 1_000_000) or int(
            (time.monotonic() - started) * 1000
        )
        return OllamaResult(
            text=text,
            model=str(payload.get("model") or self.model),
            duration_ms=duration_ms,
            input_tokens=int(payload.get("prompt_eval_count") or 0),
            output_tokens=int(payload.get("eval_count") or 0),
        )
