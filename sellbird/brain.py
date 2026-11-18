"""Local-only inference Brain for Sellbird.

All language-model requests are sent to a loopback Ollama daemon. There is no
Claude, Codex, OpenAI, Gemini, Anthropic, or remote inference fallback.
"""
import asyncio
import json
import logging
import re
import time

from sellbird.state import StateManager

logger = logging.getLogger("sellbird.brain")

from sellbird.paths import PROJECT_ROOT
from sellbird.textio import read_user_text
from sellbird.workspace_home import current_home

PROMPTS_DIR = PROJECT_ROOT / "prompts"
SKILLS_DIR = PROJECT_ROOT / "skills"
DEFAULT_TIMEOUT_SECONDS = 300
BRAIN_STATUS_KEY = "brain_status"
PROVIDER_LABELS = {"ollama": "Ollama (local)"}


def parse_brain_status(raw: str) -> dict:
    """Decode the stored Brain status, returning an empty object if invalid."""
    try:
        value = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def active_brain_status(raw: str, provider: str) -> dict:
    """Return the stored status only when it belongs to the selected provider."""
    status = parse_brain_status(raw)
    return status if status.get("provider") == provider else {}


class BrainUnavailable(Exception):
    """Local inference cannot run until Ollama or its model becomes available."""


def _read_knowledge(folder: str, name: str) -> str:
    """Read workspace knowledge, falling back to the bundled project copy."""
    own = getattr(current_home(), f"{folder}_dir") / f"{name}.md"
    try:
        return read_user_text(own)
    except FileNotFoundError:
        from sellbird.home import bundled_defaults
        shipped = bundled_defaults()
        if shipped is None or (shipped / folder / f"{name}.md") == own:
            raise
        return read_user_text(shipped / folder / f"{name}.md")


class Brain:
    """Orchestrates prompts and local Ollama inference for all sales agents."""

    def __init__(self, state: StateManager, brain_config=None, transport=None):
        from sellbird.config import BrainConfig
        from sellbird.ollama_runtime import OllamaClient

        self.state = state
        self.config = brain_config or BrainConfig()
        self.provider = self.config.provider
        self.model = self.config.model
        if self.provider != "ollama":
            raise ValueError("Only local Ollama inference is enabled.")
        if transport is not None:
            raise ValueError("Custom inference transports are disabled; use local Ollama only.")
        self.ollama = OllamaClient(
            model=self.model,
            base_url=self.config.base_url or None,
        )
        self.transport = None
        self.quota = None
        self.last_reply_empty = False
        self.unavailable = ""
        self._unavailable_fingerprint = None

    @property
    def provider_label(self) -> str:
        return PROVIDER_LABELS["ollama"]

    @property
    def paused_reason(self) -> str:
        return self.unavailable

    async def preflight(self) -> str:
        """Check local Ollama and the downloaded model without running inference."""
        try:
            details = await self.ollama.preflight()
        except Exception as exc:
            await self._mark_unavailable(exc)
            return str(exc)
        if self.unavailable:
            await self._mark_available()
        logger.info(
            "LOCAL_MODEL_READY provider=ollama model=%s endpoint=%s",
            details.get("model", self.model), details.get("base_url", self.ollama.base_url),
        )
        return ""

    def _fingerprint(self):
        return self.ollama.fingerprint()

    async def _mark_unavailable(self, error):
        reason = str(error)[:500]
        if self.unavailable != reason:
            logger.error("LOCAL_INFERENCE_UNAVAILABLE provider=ollama reason=%s", reason)
            self.unavailable = reason
            self._unavailable_fingerprint = self._fingerprint()
            await self._record_status("paused", reason)

    async def _mark_available(self):
        logger.info("Local Ollama inference is available again; resuming.")
        self.unavailable = ""
        self._unavailable_fingerprint = None
        await self._record_status("ok", "")

    async def _record_status(self, status: str, reason: str):
        try:
            await self.state.set_setting(BRAIN_STATUS_KEY, json.dumps({
                "provider": "ollama",
                "status": status,
                "reason": reason[:500],
                "since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }))
        except Exception as exc:
            logger.warning("Failed to record local Brain status: %s", type(exc).__name__)

    async def think(
        self,
        prompt: str,
        session_id: str | None = None,
        expect_json: bool = False,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = 0,
        agent: str = "",
        task: str = "",
    ) -> str:
        """Run one local generation and record model/latency/token evidence.

        max_retries is accepted for call compatibility but intentionally does
        not trigger a provider switch. On failure, the workflow remains
        retryable and the heartbeat will re-check Ollama next cycle.
        """
        from sellbird.ollama_runtime import OllamaError

        if self.paused_reason:
            logger.warning("Local inference skipped while paused: %s", self.paused_reason)
            return ""
        try:
            result = await self.ollama.generate(
                prompt, timeout=timeout, expect_json=expect_json
            )
            await self.state.increment_usage(provider="ollama")
            await self.state.record_usage_event(
                agent=agent,
                task=task or agent or "local_inference",
                session_id="",
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                duration_ms=result.duration_ms,
                num_turns=1,
                is_error=False,
                source="ollama_local",
                provider="ollama",
                cost_usd=0.0,
            )
            logger.info(
                "LOCAL_INFERENCE provider=ollama model=%s duration_ms=%s "
                "prompt_tokens=%s response_tokens=%s agent=%s task=%s",
                result.model, result.duration_ms, result.input_tokens,
                result.output_tokens, agent or "-", task or "-",
            )
            return result.text
        except Exception as exc:
            error = exc if isinstance(exc, OllamaError) else OllamaError(
                f"Local Ollama inference failed ({type(exc).__name__})."
            )
            await self._mark_unavailable(error)
            return ""

    async def think_json(
        self,
        prompt: str,
        session_id: str | None = None,
        agent: str = "",
        task: str = "",
    ) -> dict | list | None:
        """Run local inference and parse a JSON object or array."""
        full_prompt = prompt + "\n\nRespond ONLY with valid JSON. No markdown, no explanation."
        response = await self.think(
            full_prompt,
            session_id=session_id,
            expect_json=True,
            agent=agent,
            task=task,
        )
        self.last_reply_empty = not response
        if not response:
            return None
        parsed = self._extract_json(response)
        if parsed is None:
            logger.error("Failed to parse JSON from local model response.")
        return parsed

    @staticmethod
    def _extract_json(text: str) -> dict | list | None:
        """Strip optional code fences and extract a JSON object or array."""
        cleaned = text.strip()
        fence = chr(96) * 3
        if cleaned.startswith(fence):
            cleaned = re.sub(r"^.{3}(?:json)?\\s*", "", cleaned)
        if cleaned.endswith(fence):
            cleaned = cleaned[:-3].rstrip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        for open_ch, close_ch in (("{", "}"), ("[", "]")):
            start = cleaned.find(open_ch)
            end = cleaned.rfind(close_ch)
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    continue
        return None

    async def check_usage(self) -> float:
        """Return the number of local Ollama inference calls today."""
        try:
            return await self.state.get_usage_today(provider="ollama")
        except Exception as exc:
            logger.warning("Could not read local inference usage: %s", type(exc).__name__)
            return 0.0

    async def is_within_budget(
        self, max_daily_calls: int = 200, max_percent: float | None = None
    ) -> bool:
        """Apply a local daily-call guard; there is no subscription quota API."""
        calls = await self.check_usage()
        return calls < max_daily_calls

    def load_prompt(self, prompt_name: str, **kwargs) -> str:
        """Load a prompt template and replace its named placeholders."""
        try:
            template = _read_knowledge("prompts", prompt_name)
        except FileNotFoundError:
            logger.warning("Prompt file not found: %s.md", prompt_name)
            return ""
        except OSError as exc:
            logger.error("Could not read prompt file %s.md: %s", prompt_name, exc)
            return ""
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        leftovers = re.findall(r"\{\{(\w+)\}\}", template)
        if leftovers:
            logger.warning("Prompt '%s' has unfilled variables: %s",
                           prompt_name, sorted(set(leftovers)))
        return template

    def load_skill(self, skill_name: str) -> str:
        """Load a sales skill knowledge file."""
        try:
            return _read_knowledge("skills", skill_name)
        except FileNotFoundError:
            logger.warning("Skill file not found: %s.md", skill_name)
            return ""
        except OSError as exc:
            logger.error("Could not read skill file %s.md: %s", skill_name, exc)
            return ""

    def load_skills_for_agent(self, agent_name: str) -> str:
        """Concatenate the shipped sales playbooks relevant to an agent."""
        skill_map = {
            "scout": ["prospecting_tactics", "lead_qualification", "account_navigation",
                      "signal_playbook", "product_knowledge"],
            "writer": ["product_knowledge", "competitive_intel"],
            "handler": ["objection_handling", "sales_methodology", "offer_strategy",
                        "product_knowledge", "competitive_intel"],
            "sender": ["email_frameworks", "product_knowledge"],
            "linkedin": ["linkedin_outreach", "prospecting_tactics", "product_knowledge"],
        }
        names = skill_map.get(agent_name, [])
        sections = [self.load_skill(name) for name in names]
        sections = [section for section in sections if section]
        if not sections:
            return ""
        return (
            "\n\n---\n## FOUNDATIONAL KNOWLEDGE\n"
            "Use the following frameworks and best practices to guide your work:\n\n"
            + "\n\n---\n\n".join(sections)
        )
