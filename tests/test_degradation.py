"""Ruling 1: a run whose LLM checks degraded must disclose it (spec §11).
Degradation = the completion CALL failing, not a parse-failure fallback."""

from mcpdoctor import llm
from mcpdoctor.doctor.runner import degraded_banners


def _llm_with_complete(fn) -> llm.OpenAILLM:
    obj = llm.OpenAILLM()
    obj._complete = fn  # bypass the network
    return obj


def test_completion_failure_records_degradation_and_defaults():
    llm.reset_degradation()

    def boom(_prompt):
        raise RuntimeError("network down")

    obj = _llm_with_complete(boom)
    result = obj.json_call("hi", default={"score": 1})
    assert result == {"score": 1}  # safe default
    assert llm.degradation_events()  # infra failure disclosed


def test_parse_failure_is_not_degradation():
    llm.reset_degradation()
    obj = _llm_with_complete(lambda _p: "not json at all")
    result = obj.json_call("hi", default={"score": 1})
    assert result == {"score": 1}  # fell back...
    assert llm.degradation_events() == []  # ...but that's ordinary hygiene


def test_success_records_nothing():
    llm.reset_degradation()
    obj = _llm_with_complete(lambda _p: '{"score": 2}')
    assert obj.json_call("hi", default={"score": 1}) == {"score": 2}
    assert llm.degradation_events() == []


def test_banner_when_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm.reset_degradation()
    banners = degraded_banners()
    assert len(banners) == 1
    assert "OPENAI_API_KEY not set" in banners[0]
    assert "floor, not a final" in banners[0]


def test_banner_when_api_failed_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-present")
    llm.reset_degradation()
    llm._record_degradation("LLM call failed (AuthenticationError)")
    banners = degraded_banners()
    assert len(banners) == 1
    assert "LLM call failed" in banners[0]


def test_no_banner_when_key_present_and_clean(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-present")
    llm.reset_degradation()
    assert degraded_banners() == []
