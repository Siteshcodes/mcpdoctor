"""Executable proof of the destructive-skip rule (spec §5).

badserver's delete_everything writes a sentinel file if it is EVER invoked.
The doctor must never trip it without --unsafe - and a positive control
proves the sentinel would appear if the tool were called, so the negative
test actually means something.
"""

import asyncio
import sys
from pathlib import Path

from mcp.client.stdio import get_default_environment

from mcpdoctor.mcp_client import MCPClient

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_doctor_run_never_trips_the_tripwire(badserver_run):
    # badserver_run executed the FULL pipeline - manifest gathering plus the
    # probe sweep - WITHOUT --unsafe. If the skip rule failed, badserver
    # wrote fixtures/.tripwire and this fails loudly.
    assert not (FIXTURES / ".tripwire").exists()


def test_tripwire_mechanism_actually_fires(tmp_path):
    # Positive control: invoke delete_everything directly with VALID args
    # (bypassing the probe engine entirely) and watch the sentinel appear.
    # Without this, the test above would also pass if the tripwire were broken.
    sentinel = tmp_path / "tripwire"

    async def invoke():
        env = {**get_default_environment(), "MCPDOCTOR_TRIPWIRE": str(sentinel)}
        async with MCPClient(
            command=sys.executable, args=[str(FIXTURES / "badserver.py")], env=env
        ) as client:
            result = await client.call_tool("delete_everything", {"target": "x"})
            assert result.isError  # the tool still raises "400" after tripping

    asyncio.run(invoke())
    assert sentinel.exists()
    assert "invoked" in sentinel.read_text()
