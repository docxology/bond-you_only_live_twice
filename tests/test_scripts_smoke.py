"""Subprocess smoke tests for the thin mission CLIs.

Runs each script with the venv python (``sys.executable``) from the package
root and asserts exit code 0 plus expected output / artifacts. No mocks.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = _ROOT / "scripts"


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def test_run_mission_full_flow() -> None:
    proc = _run("run_mission.py")
    assert proc.returncode == 0, proc.stderr
    assert "windows=" in proc.stdout
    assert "lessons=" in proc.stdout


def test_run_mission_each_phase() -> None:
    for phase in ("brief", "recon", "plan", "execute", "debrief"):
        proc = _run("run_mission.py", phase)
        assert proc.returncode == 0, (phase, proc.stderr)
        assert f"[VOLCANO] {phase}" in proc.stdout
    # Unknown phase -> defaults to full flow.
    proc = _run("run_mission.py", "not-a-phase")
    assert proc.returncode == 0
    assert "run" in proc.stdout


def test_preflight_passes() -> None:
    proc = _run("00_preflight.py")
    assert proc.returncode == 0, proc.stderr
    assert "preflight OK" in proc.stdout
    assert "PASS" in proc.stdout


def test_generate_manuscript_variables_writes_json() -> None:
    proc = _run("z_generate_manuscript_variables.py")
    assert proc.returncode == 0, proc.stderr
    assert (_ROOT / "output" / "data" / "manuscript_variables.json").is_file()


def test_render_figures_writes_pngs() -> None:
    proc = _run("render_figures.py")
    assert proc.returncode == 0, proc.stderr
    for name in (
        "rendezvous_windows.png",
        "concealed_lair_detection.png",
        "pattern_of_life.png",
    ):
        assert (_ROOT / "output" / "figures" / name).is_file()
