"""Groq wrapper (ported from legacy/core/groq.py) plus judge/heal hygiene.

Two surfaces:
- GroqLLM.chat(...) — the conversational tool-calling loop for the chatbot.
- json_call(prompt, default=...) — a temperature=0, JSON-only single-shot
  used by heal.py and the LLM judges. Hygiene per CLAUDE.md hard rules:
  strip ```json fences, one parse retry, then the caller's safe default.
  It NEVER raises — a judge or heal failure must not crash a run.

Tests monkeypatch the module-level `json_call`; heal.py and checks_llm.py
look it up late (module attribute) so the patch always takes.
"""

import json
import os
import re

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


class GroqLLM:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("MODEL", "llama-3.3-70b-versatile")
        self._client = None

    @property
    def client(self):
        # Lazy: importing/constructing Groq needs no API key until first call,
        # and keyless test runs never touch this path. max_retries=0 so a
        # missing/invalid key degrades in seconds, not minutes of backoff
        # across every judge call (the keyless-run speed matters — spec §11).
        if self._client is None:
            from groq import Groq

            self._client = Groq(max_retries=0, timeout=20.0)
        return self._client

    def _complete(self, prompt: str) -> str:
        # Fail fast when there's no key at all: skip the network entirely so a
        # keyless lint returns safe defaults immediately instead of waiting on
        # doomed API calls for every tool.
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError("GROQ_API_KEY not set")
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
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
            "max_tokens": 8000,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            params["tools"] = tools
        completion = self.client.chat.completions.create(**params)
        return completion.choices[0].message


_default_llm: GroqLLM | None = None


def _get_llm() -> GroqLLM:
    global _default_llm
    if _default_llm is None:
        _default_llm = GroqLLM()
    return _default_llm


def json_call(prompt: str, *, default: dict) -> dict:
    """Module-level entry used by heal.py and the judges (patched in tests)."""
    return _get_llm().json_call(prompt, default=default)
