"""Strict local-only Ollama inference. There is intentionally no cloud fallback."""
from __future__ import annotations
import os, time, json, ipaddress
from urllib.parse import urlparse
import httpx
from .db import connect

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

def _local_base_url() -> bool:
    """Reject remote endpoints: this app must never run inference in a cloud."""
    parsed = urlparse(OLLAMA_URL)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        return False
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        return False
    if "cloud" in DEFAULT_MODEL.lower() or "remote" in DEFAULT_MODEL.lower():
        return False
    if parsed.hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False

class LocalModelUnavailable(RuntimeError):
    pass

def log_event(event: str, status: str, duration_ms: int = 0, details: str = "", model: str = ""):
    with connect() as db:
        db.execute("INSERT INTO logs(event,model,status,duration_ms,details) VALUES(?,?,?,?,?)",
                   (event, model, status, duration_ms, details[:2000]))

async def ollama_status():
    if not _local_base_url() or DEFAULT_MODEL.endswith(":cloud"):
        return {"available": False, "url": OLLAMA_URL, "model": DEFAULT_MODEL,
                "model_installed": False, "ready": False, "models": [],
                "error": "Only a loopback Ollama endpoint and locally installed model are permitted."}
    try:
        async with httpx.AsyncClient(timeout=2.5, trust_env=False) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
            installed = any(x == DEFAULT_MODEL or x.startswith(DEFAULT_MODEL + "-") for x in models)
            return {"available": True, "url": OLLAMA_URL, "model": DEFAULT_MODEL,
                    "model_installed": installed, "ready": installed, "models": models}
    except (httpx.HTTPError, ValueError) as exc:
        return {"available": False, "url": OLLAMA_URL, "model": DEFAULT_MODEL,
                "model_installed": False, "ready": False, "models": [], "error": str(exc)}
async def generate(prompt: str, event: str, system: str = "You are a careful B2B sales research assistant. Do not invent facts. Distinguish evidence from inference.", temperature: float = 0.2) -> str:
    started = time.perf_counter()
    if not _local_base_url() or DEFAULT_MODEL.endswith(":cloud"):
        log_event(event, "blocked", 0, "Remote inference endpoint or cloud model tag is forbidden.", DEFAULT_MODEL)
        raise LocalModelUnavailable("Remote inference is disabled. Use a loopback Ollama endpoint and a locally installed model tag; no cloud fallback is permitted.")
    try:
        request_body = {
            "model": DEFAULT_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if event in {"buying_signal_classification", "prospect_scoring", "reply_classification"}:
            request_body["format"] = "json"
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=3.0), trust_env=False) as client:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=request_body)
            response.raise_for_status()
            payload = response.json()
            content = payload.get("message", {}).get("content", "").strip()
            if not content:
                raise LocalModelUnavailable("Ollama returned an empty response.")
        elapsed = int((time.perf_counter() - started) * 1000)
        log_event(event, "success", elapsed, f"local inference via {OLLAMA_URL}; no remote provider configured", DEFAULT_MODEL)
        return content
    except (httpx.HTTPError, ValueError, KeyError, LocalModelUnavailable) as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        log_event(event, "unavailable", elapsed, str(exc), DEFAULT_MODEL)
        raise LocalModelUnavailable(f"Local Ollama inference unavailable at {OLLAMA_URL}: {exc}. Start Ollama and ensure {DEFAULT_MODEL} is installed. No cloud fallback was attempted.") from exc
