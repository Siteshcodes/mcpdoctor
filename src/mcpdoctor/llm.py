"""OpenAI Chat Completions wrapper plus judge/heal hygiene.

Two surfaces:
- OpenAILLM.chat(...) — the conversational tool-calling loop for the chatbot.
- json_call(prompt, default=...) — a temperature=0, JSON-only single-shot
  used by heal.py and the LLM judges. Hygiene per the check specification:
  strip ```json fences, one parse retry, then the caller's safe default.
  It NEVER raises — a judge or heal failure must not crash a run.

Tests monkeypatch the module-level `json_call`; heal.py and checks_llm.py
look it up late (module attribute) so the patch always takes.
"""

import json
import os
import re

DEFAULT_MODEL = "gpt-5.4-mini"
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)

# Degradation = the completion CALL failing (auth/network/API) — distinct from
# a parse-failure fallback, which is normal judge hygiene. The doctor reads
# these to disclose a degraded grade (spec §11). Reset at the start of a run.
_degradation_events: list[str] = []


def reset_degradation() -> None:
    _degradation_events.clear()


def degradation_events() -> list[str]:
    return list(_degradation_events)


def _record_degradation(detail: str) -> None:
    _degradation_events.append(detail)


def strip_and_parse(raw: str) -> dict:
    """Strip optional ```json fences and parse. Raises on invalid JSON."""
    cleaned = _FENCE_RE.sub("", raw.strip())
    # A model sometimes wraps JSON in prose; grab the outermost object.
    if not cleaned.startswith("{"):
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("expected a JSON object")
    return parsed


def has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def api_error_hint(error: Exception) -> str:
    """Actionable provider errors without echoing keys or request contents."""
    from openai import (
        APIConnectionError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
    )

    if isinstance(error, AuthenticationError):
        return "OpenAI rejected the API key. Check OPENAI_API_KEY."
    if isinstance(error, RateLimitError):
        if error.code == "insufficient_quota":
            return "OpenAI API quota exhausted. Check your project's billing and usage limits."
        return "OpenAI rate limit reached. Wait before retrying."
    if isinstance(error, (NotFoundError, PermissionDeniedError)):
        return "Check OPENAI_MODEL and your OpenAI project's model access and key permissions."
    if isinstance(error, APITimeoutError):
        return "OpenAI timed out. Try again or choose a faster supported model."
    if isinstance(error, APIConnectionError):
        return "Could not reach OpenAI. Check your network connection."
    if isinstance(error, BadRequestError):
        return (
            "OpenAI rejected the request. Use an OPENAI_MODEL that supports Chat "
            "Completions, JSON mode, function calling, and temperature settings."
        )
    return "OpenAI request failed. Check the service status and your configuration."


class OpenAILLM:
    def __init__(self, model: str | None = None):
        self.model = (model or os.getenv("OPENAI_MODEL", "")).strip() or DEFAULT_MODEL
        self._client = None

    @property
    def client(self):
        # Lazy: constructing this wrapper needs no API key until first call,
        # and keyless test runs never touch this path. max_retries=0 so a
        # missing/invalid key degrades in seconds, not minutes of backoff
        # across every judge call (the keyless-run speed matters — spec §11).
        if not has_api_key():
            raise RuntimeError("OPENAI_API_KEY not set")
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=os.environ["OPENAI_API_KEY"].strip(),
                max_retries=0,
                timeout=20.0,
            )
        return self._client

    def _complete(self, prompt: str) -> str:
        # Fail fast when there's no key at all: skip the network entirely so a
        # keyless lint returns safe defaults immediately instead of waiting on
        # doomed API calls for every tool.
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_completion_tokens=1024,
            messages=[
                {"role": "system", "content": "Return only a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content or ""

    def json_call(self, prompt: str, *, default: dict) -> dict:
        """One JSON-only completion with fence-strip + one parse retry, then
        the safe default. Never raises. Records a degradation event only when
        the completion call itself failed and we fell back to the default —
        parse failures alone are ordinary hygiene, not degradation."""
        call_failed = ""
        for _ in range(2):
            try:
                raw = self._complete(prompt)
            except Exception as e:  # noqa: BLE001 - infra failure, degrade gracefully
                call_failed = type(e).__name__
                continue
            try:
                return strip_and_parse(raw)
            except Exception:
                continue
        if call_failed:
            _record_degradation(f"LLM call failed ({call_failed})")
        return dict(default)

    def chat(self, messages, tools=None, temperature=1.0):
        params = {
            "model": self.model,
            "max_completion_tokens": 8000,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            params["tools"] = tools
        completion = self.client.chat.completions.create(**params)
        return completion.choices[0].message


_default_llm: OpenAILLM | None = None


def _get_llm() -> OpenAILLM:
    global _default_llm
    if _default_llm is None:
        _default_llm = OpenAILLM()
    return _default_llm


def json_call(prompt: str, *, default: dict) -> dict:
    """Module-level entry used by heal.py and the judges (patched in tests)."""
    return _get_llm().json_call(prompt, default=default)
