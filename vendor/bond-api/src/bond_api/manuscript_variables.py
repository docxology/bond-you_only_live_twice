"""Manuscript variable hydration for BOND-API.

Every ``{{TOKEN}}`` in ``manuscript/*.md`` resolves through
:func:`generate_variables`, which reads ``manuscript/config.yaml`` plus the
frozen protocol surface. Metrics are never hand-authored in prose: they flow
through this module so the manuscript cannot drift from the code.

The consuming orchestrator is ``scripts/z_generate_manuscript_variables.py``
(thin wrapper); the live cross-reference gate lives in
``tests/test_manuscript_variables.py``.

**No wall clock.** Every value here comes from a committed source — the live
package, ``manuscript/config.yaml``, ``pyproject.toml``, or the running
interpreter — so two runs of the generator write byte-identical artifacts.
The manuscript date is read from ``paper.date`` in the config (a committed
value that changes by edit, in a diff) rather than from ``datetime.now``:
a clock read here would make ``output/`` differ on every regeneration and
falsify the determinism claim in ``manuscript/06_reproducibility.md``.
``tests/test_regeneration_determinism.py`` binds that byte-identity by
running the generator twice across a whole-second boundary.
"""

from __future__ import annotations

import platform
import re
from pathlib import Path
from typing import Any

import yaml

from bond_api.capabilities import CAPABILITY_NAMES
from bond_api.protocol import CODENAME, IDENTITY, protocol_surface
from bond_api.serialization import SERIALIZATION_TAG

__all__ = [
    "generate_variables",
    "load_manuscript_config",
    "read_coverage_floor",
    "require_manuscript_date",
    "require_surface",
    "resolve_manuscript_tree",
]

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "manuscript" / "config.yaml"
DEFAULT_PYPROJECT_PATH = PACKAGE_ROOT / "pyproject.toml"

_TOKEN_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
#: Matches the enforced coverage floor declared in ``[tool.coverage.report]``.
_FAIL_UNDER_RE = re.compile(r"^\s*fail_under\s*=\s*(\d+)\s*$", re.MULTILINE)
#: ``paper.date`` must be a plain ISO calendar date — no time, no zone, no clock.
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_manuscript_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate ``manuscript/config.yaml`` (or an explicit path)."""
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"manuscript config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"manuscript config must be a top-level mapping, got {type(data).__name__}")
    return data


def read_coverage_floor(pyproject_path: str | Path | None = None) -> int:
    """Read the enforced coverage floor from ``pyproject.toml``.

    The floor is parsed from the gate declaration itself
    (``[tool.coverage.report] fail_under``) rather than restated in prose or
    config, so the manuscript can never quote a floor the suite does not
    enforce. A missing declaration is an error, not a default: silently
    substituting a number would be exactly the drift this token prevents.
    """
    path = Path(pyproject_path) if pyproject_path is not None else DEFAULT_PYPROJECT_PATH
    if not path.is_file():
        raise FileNotFoundError(f"pyproject.toml not found: {path}")
    match = _FAIL_UNDER_RE.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"no 'fail_under' coverage gate declared in {path}")
    return int(match.group(1))


def require_manuscript_date(paper: dict[str, Any]) -> str:
    """Return the committed manuscript date from a config ``paper`` section.

    This is the token that used to be a ``datetime.now`` read. A wall clock
    made every regeneration of ``output/`` differ, which silently falsified
    the determinism contract the reproducibility section states. The date now
    comes from ``paper.date`` — a committed value that changes only in a diff.

    A missing, blank, or non-calendar value is an error rather than a
    substituted default: falling back to *today* would reintroduce exactly the
    clock dependence this function exists to remove. Extracted as its own
    callable so the gate has a positive control — a test can hand it a bad
    ``paper`` section instead of the check being green purely because the real
    config always carries a good date.
    """
    raw = paper.get("date")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("manuscript config 'paper.date' must be a non-empty ISO date string (YYYY-MM-DD)")
    date = raw.strip()
    if not _ISO_DATE_RE.match(date):
        raise ValueError(f"manuscript config 'paper.date' must be a plain YYYY-MM-DD calendar date, got {date!r}")
    return date


def require_surface(surface: dict[str, Any]) -> None:
    """Fail when the frozen protocol surface exposes no dataclasses.

    Extracted from :func:`generate_variables` so the gate has a positive
    control: it can be called with a genuinely empty surface in a test rather
    than being green purely because the real package always populates one.
    """
    if not surface.get("dataclasses"):
        raise ValueError("protocol surface is empty — bond_api failed to expose its dataclasses")


def generate_variables(
    *,
    config_path: str | Path | None = None,
    pyproject_path: str | Path | None = None,
    require_outputs: bool = True,
) -> dict[str, str]:
    """Compute the ``{{TOKEN}}`` → value mapping for the manuscript.

    Args:
        config_path: Override for ``manuscript/config.yaml``.
        pyproject_path: Override for ``pyproject.toml`` (coverage-floor token).
        require_outputs: When True (default), verify the protocol surface is
            non-empty — the strict-mode gate that replaced the exemplar's
            analysis-CSV requirement.
    """
    config = load_manuscript_config(config_path)
    paper = config.get("paper", {})
    if not isinstance(paper, dict):
        raise ValueError("manuscript config 'paper' section must be a mapping")
    protocol_config = config.get("protocol", {})
    if not isinstance(protocol_config, dict):
        raise ValueError("manuscript config 'protocol' section must be a mapping")
    surface = protocol_surface()
    if require_outputs:
        require_surface(surface)
    return {
        "BOND_IDENTITY": IDENTITY,
        "BOND_CODENAME": CODENAME,
        "BOND_VERSION": str(paper.get("version", "")),
        "BOND_TITLE": str(paper.get("title", "")),
        "BOND_SUBTITLE": str(paper.get("subtitle", "")),
        "BOND_NUM_DATACLASSES": str(len(surface["dataclasses"])),
        "BOND_PROTOCOL_DATACLASSES": ", ".join(surface["dataclasses"]),
        "BOND_NUM_PROVIDER_METHODS": str(len(surface["provider_methods"])),
        "BOND_PROVIDER_METHODS": ", ".join(surface["provider_methods"]),
        "BOND_NUM_CAPABILITIES": str(len(CAPABILITY_NAMES)),
        "BOND_CAPABILITIES": ", ".join(CAPABILITY_NAMES),
        "BOND_SERIALIZATION_TAG": SERIALIZATION_TAG,
        "BOND_REFERENCE_FILM": str(protocol_config.get("reference_film", "")),
        "BOND_NUM_FILMS": str(protocol_config.get("film_count", "")),
        "BOND_COVERAGE_FLOOR": str(read_coverage_floor(pyproject_path)),
        "BOND_MANUSCRIPT_DATE": require_manuscript_date(paper),
        "PYTHON_VERSION": platform.python_version(),
    }


def resolve_manuscript_tree(
    variables: dict[str, str],
    *,
    manuscript_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    strict: bool = True,
) -> tuple[Path, list[str]]:
    """Copy each manuscript section to ``output/manuscript/``, substituting tokens.

    Only ``NN_*.md`` section files are copied (not sidecars such as
    ``SYNTAX.md``). In strict mode any leftover ``{{TOKEN}}`` fails the
    resolution so the manuscript can never render with raw braces, and a
    manuscript directory containing **no** sections is an error rather than a
    silent success: an empty scan set would make the unresolved-token gate
    vacuous (nothing scanned always passes).

    Returns the output directory and the sorted list of resolved file names.
    """
    manuscript_dir = Path(manuscript_dir) if manuscript_dir is not None else PACKAGE_ROOT / "manuscript"
    output_dir = Path(output_dir) if output_dir is not None else PACKAGE_ROOT / "output" / "manuscript"
    resolved: list[str] = []
    for source in sorted(manuscript_dir.glob("[0-9][0-9]_*.md")):
        text = source.read_text(encoding="utf-8")
        for token, value in variables.items():
            text = text.replace("{{" + token + "}}", value)
        unresolved = sorted(set(_TOKEN_RE.findall(text)))
        if unresolved and strict:
            raise ValueError(f"unresolved manuscript tokens in {source.name}: {unresolved}")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / source.name).write_text(text, encoding="utf-8")
        resolved.append(source.name)
    if not resolved and strict:
        raise ValueError(f"no manuscript sections (NN_*.md) found in {manuscript_dir} — nothing to resolve")
    return output_dir, resolved
