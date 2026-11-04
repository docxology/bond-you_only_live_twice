"""Film discovery: find :class:`MissionProvider` implementations on ``sys.path``.

The discovery convention is deliberately simple — a film package is a
top-level importable module named by its slug (``<slug>/mission.py``) exposing
a ``MissionProvider`` class that satisfies the BOND-API protocol:

* :func:`load_provider` imports one slug strictly and returns its provider,
  bound to the slug (a provider that declares no ``film`` attribute is bound
  to the slug it was discovered under; a provider declaring a different film
  is rejected as an identity mismatch).
* :func:`discover` scans search paths for candidate slugs (directories
  containing ``mission.py``) and returns every provider it can load, skipping
  un-discoverable slugs — bulk discovery must never crash the suite.

Slug imports are cached in ``sys.modules`` like any Python import; callers
that host multiple packages under the same slug in different locations must
use distinct slugs per location.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from bond_api.protocol import MissionProvider

__all__ = ["DiscoveryError", "discover", "load_provider"]

#: A slug must be a valid top-level module name.
_SLUG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DiscoveryError(RuntimeError):
    """Raised when a film package cannot be discovered, loaded, or bound."""


def _resolve_search_paths(search_paths: Iterable[str | os.PathLike[str]] | None) -> list[str]:
    """Resolve explicit search paths, validating they exist; default to ``sys.path``.

    For the default (``sys.path``) case, non-directory entries — stale paths,
    zip imports, files — are skipped rather than fatal: the interpreter's own
    path list is not something a caller should have to curate.
    """
    if search_paths is None:
        return [entry for entry in sys.path if entry and Path(entry).is_dir()]
    resolved: list[str] = []
    for raw in search_paths:
        path = os.fspath(raw)
        if not Path(path).is_dir():
            raise DiscoveryError(f"search path is not an existing directory: {path!r}")
        resolved.append(path)
    return resolved


def _validate_slug(slug: str) -> None:
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise DiscoveryError(
            f"invalid film slug {slug!r}: slugs must be importable module names "
            "(letters, digits, underscore; not starting with a digit)"
        )


def _candidate_slugs(search_paths: list[str]) -> list[str]:
    """Autodetect candidate slugs: top-level dirs containing ``mission.py``."""
    candidates: set[str] = set()
    for entry in search_paths:
        try:
            children = os.listdir(entry)
        except OSError:
            continue  # unreadable path entries are skipped, never fatal
        for name in children:
            if _SLUG_RE.fullmatch(name) and Path(entry, name, "mission.py").is_file():
                candidates.add(name)
    return sorted(candidates)


def load_provider(
    slug: str,
    *,
    search_paths: Iterable[str | os.PathLike[str]] | None = None,
) -> MissionProvider:
    """Import a single film package by slug and return its bound provider.

    Args:
        slug: The film slug (importable module name).
        search_paths: Directories to search, in order; defaults to ``sys.path``.

    Raises:
        DiscoveryError: if the slug is invalid, the package is missing or
            malformed, its provider fails to instantiate or satisfy the
            protocol, or its declared film identity mismatches the slug.
    """
    _validate_slug(slug)
    paths = _resolve_search_paths(search_paths)
    inserted = [entry for entry in paths if entry not in sys.path]
    for entry in inserted:
        sys.path.insert(0, entry)
    try:
        try:
            mission_module = importlib.import_module(f"{slug}.mission")
        except ImportError as exc:
            raise DiscoveryError(f"film package {slug!r} is not discoverable: {exc}") from exc

        provider_cls: Any = getattr(mission_module, "MissionProvider", None)
        if not isinstance(provider_cls, type):
            raise DiscoveryError(f"{slug}.mission must expose a MissionProvider class")

        try:
            provider: Any = provider_cls()
        except Exception as exc:  # a broken film must never crash the suite
            raise DiscoveryError(f"MissionProvider for {slug!r} failed to instantiate: {exc}") from exc

        # Bind first: a provider that declares no film attribute answers to the
        # slug it was discovered under. Binding must precede the protocol check
        # because ``film`` is part of the runtime-checkable surface.
        declared = getattr(provider, "film", "")
        if not declared:
            try:
                setattr(provider, "film", slug)
            except AttributeError as exc:
                raise DiscoveryError(
                    f"MissionProvider for {slug!r} cannot be bound to its slug (frozen or slotted)"
                ) from exc

        if not isinstance(provider, MissionProvider):
            raise DiscoveryError(
                f"{slug}.mission.MissionProvider does not satisfy the MissionProvider protocol "
                "(missing brief/recon/plan/execute/debrief or film)"
            )
        if declared and declared != slug:
            raise DiscoveryError(f"provider discovered under {slug!r} declares film {declared!r}")
        return provider
    finally:
        # Restore ``sys.path`` exactly as we found it. A film module that
        # rewrites ``sys.path`` on import can remove our entry first; that is
        # the film's business, not a discovery failure, so the missing-entry
        # case is tolerated here and nowhere else.
        for entry in inserted:
            try:
                sys.path.remove(entry)
            except ValueError:
                continue


def discover(
    *,
    slugs: Iterable[str] | None = None,
    search_paths: Iterable[str | os.PathLike[str]] | None = None,
) -> dict[str, MissionProvider]:
    """Discover mission providers, returning a slug → provider mapping.

    When ``slugs`` is omitted, candidates are autodetected by scanning each
    search path for top-level directories containing ``mission.py``. Slugs
    that fail to load are skipped so one broken film never hides the rest;
    use :func:`load_provider` when a single film must load strictly.

    "Fail to load" includes an **invalid slug**: slug validation happens
    inside :func:`load_provider`, whose ``DiscoveryError`` this function
    catches, so ``discover(slugs=["9bad-slug"])`` returns ``{}`` rather than
    raising. Search-path validation is the one check that runs before any
    loading, so a non-existent search path *does* raise from here.
    """
    paths = _resolve_search_paths(search_paths)
    if slugs is None:
        slugs = _candidate_slugs(paths)
    providers: dict[str, MissionProvider] = {}
    for slug in slugs:
        try:
            providers[slug] = load_provider(slug, search_paths=paths)
        except DiscoveryError:
            continue
    return providers
