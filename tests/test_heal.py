"""The heal loop with a fake failing execute and a mocked LLM. No network."""

import pytest

from mcpdoctor import heal, llm


SCHEMA = {"type": "object", "properties": {"date": {"type": "string"}}, "required": ["date"]}


@pytest.fixture
def mock_repair(monkeypatch):
    """Patch the module-level json_call heal.py looks up late."""

    def install(*proposals):
        it = iter(proposals)

        def fake(prompt, *, default):
            try:
                nxt = next(it)
            except StopIteration:
                return dict(default)
            return {"args": nxt} if nxt is not None else dict(default)

        monkeypatch.setattr(llm, "json_call", fake)

    return install


def executor(succeed_on):
    """execute callback that returns ok when args match succeed_on."""
    seen = []

    async def execute(args):
        seen.append(args)
        if args == succeed_on:
            return True, ""
        return False, f"still bad: {args}"

    execute.seen = seen
    return execute


async def test_healed_on_first_attempt(mock_repair):
    mock_repair({"date": "2026-07-06"})
    execute = executor({"date": "2026-07-06"})
    result = await heal.heal(execute, "bad date", SCHEMA, {"date": "July 5th"})
    assert result.healed
    assert result.attempts == 1
    assert result.args == {"date": "2026-07-06"}
    assert len(execute.seen) == 1


async def test_healed_on_second_attempt(mock_repair):
    mock_repair({"date": "wrong"}, {"date": "2026-07-06"})
    execute = executor({"date": "2026-07-06"})
    result = await heal.heal(execute, "bad date", SCHEMA, {"date": "July 5th"})
    assert result.healed
    assert result.attempts == 2
    assert len(execute.seen) == 2


async def test_unrepaired_after_max_attempts(mock_repair):
    mock_repair({"date": "nope1"}, {"date": "nope2"}, {"date": "nope3"})
    execute = executor({"date": "unreachable"})
    result = await heal.heal(execute, "bad", SCHEMA, {"date": "x"})
    assert not result.healed
    assert result.attempts == heal.MAX_ATTEMPTS
    assert len(execute.seen) == heal.MAX_ATTEMPTS  # never exceeds the budget


async def test_no_proposal_stops_immediately(mock_repair):
    mock_repair(None)  # LLM declined / unparseable
    execute = executor({"date": "whatever"})
    result = await heal.heal(execute, "bad", SCHEMA, {"date": "x"})
    assert not result.healed
    assert result.attempts == 1
    assert execute.seen == []  # never executed a None proposal
