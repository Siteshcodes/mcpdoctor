"""json_call hygiene (CLAUDE.md hard rules): fence-strip, one parse retry,
safe default, never raises. Exercised through an injected completion fn so no
network is touched."""

from mcpdoctor.llm import OpenAILLM, strip_and_parse


def make_llm(*responses):
    """An OpenAILLM whose _complete yields the given raw strings in order (a
    trailing response repeats). Exceptions can be embedded as instances."""
    calls = {"i": 0}

    def _complete(prompt: str) -> str:
        i = min(calls["i"], len(responses) - 1)
        calls["i"] += 1
        value = responses[i]
        if isinstance(value, Exception):
            raise value
        return value

    llm = OpenAILLM.__new__(OpenAILLM)
    llm.model = "test"
    llm._client = None
    llm._complete = _complete  # type: ignore[method-assign]
    llm._calls = calls
    return llm


def test_strip_and_parse_removes_json_fences():
    assert strip_and_parse('```json\n{"a": 1}\n```') == {"a": 1}


def test_strip_and_parse_extracts_object_from_prose():
    assert strip_and_parse('here you go: {"score": 2} thanks') == {"score": 2}


def test_clean_json_parses_first_try():
    llm = make_llm('{"score": 2}')
    assert llm.json_call("p", default={"score": 1}) == {"score": 2}
    assert llm._calls["i"] == 1


def test_garbage_then_valid_retries_once():
    llm = make_llm("not json at all", '{"score": 0}')
    assert llm.json_call("p", default={"score": 1}) == {"score": 0}
    assert llm._calls["i"] == 2


def test_garbage_twice_returns_default():
    llm = make_llm("nope", "still nope")
    assert llm.json_call("p", default={"score": 1, "reason": "judge unparseable"}) == {
        "score": 1,
        "reason": "judge unparseable",
    }


def test_exception_never_raises_returns_default():
    llm = make_llm(RuntimeError("api down"), RuntimeError("still down"))
    assert llm.json_call("p", default={"ok": False}) == {"ok": False}


def test_default_is_copied_not_shared():
    default = {"score": 1}
    llm = make_llm("garbage", "garbage")
    out = llm.json_call("p", default=default)
    out["mutated"] = True
    assert "mutated" not in default
