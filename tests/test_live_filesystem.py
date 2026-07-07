"""DoD: the doctor completes against the official filesystem server with
zero crashes, zero destructive-call attempts, and zero mutations.

Marked `live` (excluded from default runs): the first invocation makes npx
download @modelcontextprotocol/server-filesystem from the network.
Run with: uv run pytest -m live
"""

import asyncio
import shutil

import pytest

from mcpdoctor.doctor.probes import ProbeConfig
from mcpdoctor.doctor.report import render_text
from mcpdoctor.doctor.runner import run_doctor_specs

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(shutil.which("npx") is None, reason="npx not installed"),
]


def test_filesystem_server_lints_safely(tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    spec = f'npx -y @modelcontextprotocol/server-filesystem "{sandbox.as_posix()}"'

    run = asyncio.run(run_doctor_specs([spec], ProbeConfig()))
    report = render_text(run.manifest, run.results, run.notes, run.degraded)

    assert "Overall:" in report  # completed end-to-end, no crash
    # The strongest safety assertion available: the probe sweep wrote,
    # moved, created and deleted NOTHING in the directory it was given.
    assert list(sandbox.iterdir()) == []
