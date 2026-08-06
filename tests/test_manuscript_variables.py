"""Tests for manuscript token hydration and the live cross-reference gate.

Verifies that ``generate_variables()`` produces every token used in the
numbered manuscript sections and that invalid configs fail loudly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from you_only_live_twice.manuscript_variables import (
    _fmt,
    generate_variables,
    load_mission_config,
)

#: manuscript/ directory (sibling of tests/).
_MANUSCRIPT = Path(__file__).resolve().parent.parent / "manuscript"


def test_generate_variables_returns_string_map() -> None:
    variables = generate_variables(now="2026-08-04")
    assert variables and all(isinstance(v, str) for v in variables.values())
    assert variables["BOND_CODENAME"] == "VOLCANO"
    assert variables["BOND_IDENTITY"] == "YOU ONLY LIVE TWICE"
    assert variables["BOND_FILM_YEAR"] == "1967"
    assert variables["SCENARIO_SEED"] == "1967"


def test_generate_variables_is_deterministic() -> None:
    a = generate_variables(now="2026-08-04")
    b = generate_variables(now="2026-08-04")
    assert a == b
    # A different 'now' only changes the timestamp token.
    c = generate_variables(now="2026-01-01")
    assert c["GENERATION_TIMESTAMP"] == "2026-01-01"
    assert a["GENERATION_TIMESTAMP"] == "2026-08-04"
    assert c["RENDEZVOUS_NUM_WINDOWS"] == a["RENDEZVOUS_NUM_WINDOWS"]


def test_load_mission_config() -> None:
    config = load_mission_config(_MANUSCRIPT / "config.yaml")
    assert config["paper"]["title"]
    with pytest.raises(FileNotFoundError):
        load_mission_config(_MANUSCRIPT / "does_not_exist.yaml")


def test_load_mission_config_rejects_non_mapping(tmp_path) -> None:
    bad = tmp_path / "config.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(TypeError):
        load_mission_config(bad)


def test_fmt() -> None:
    assert _fmt(None) == "N/A"
    assert _fmt(3.14) == "3.14"
    assert _fmt("x") == "x"


def test_all_manuscript_tokens_are_generated() -> None:
    """Live cross-reference gate: every token in prose exists in the map."""
    variables = generate_variables(now="2026-08-04")
    pattern = re.compile(r"{{\s*([A-Z0-9_]+)\s*}}")
    missing: set[str] = set()
    used = 0
    for path in sorted(_MANUSCRIPT.glob("[0-9]*.md")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            used += 1
            token = match.group(1)
            if token not in variables:
                missing.add(token)
    assert used > 0, "no tokens found in numbered manuscript sections"
    assert not missing, f"tokens used in prose but not generated: {sorted(missing)}"


def test_generate_variables_default_now_is_fixed() -> None:
    """With ``now=None`` the generation timestamp is the fixed local default."""
    variables = generate_variables()  # now not supplied
    assert variables["GENERATION_TIMESTAMP"] == "2026-08-04"
