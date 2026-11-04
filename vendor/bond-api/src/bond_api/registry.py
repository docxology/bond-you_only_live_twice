"""Registries for the BOND suite: gadgets and discovered mission providers.

Two complementary registries live here:

* :class:`GadgetRegistry` — a film → gadget-name → payload map. Gadgets are
  opaque (callables, data, handlers); the registry stores and returns whatever
  a film registered and never interprets it.
* :class:`MissionRegistry` — the mission/package registry of discovered
  :class:`~bond_api.protocol.MissionProvider` instances, keyed by film slug.
  Coordinators fill it from :func:`bond_api.discovery.discover` and then drive
  providers without touching import machinery again.

Both are deterministic: iteration and listing follow insertion order.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from bond_api.protocol import MissionProvider, _require, _require_non_empty

__all__ = ["GadgetRegistry", "MissionRegistry"]


class GadgetRegistry:
    """Map film slugs to named gadgets (opaque payloads)."""

    def __init__(self) -> None:
        self._gadgets: dict[str, dict[str, Any]] = {}

    def register(self, film: str, gadgets: Mapping[str, Any]) -> None:
        """Register (or merge) gadgets for a film.

        Re-registering an existing gadget name replaces its payload; other
        gadgets for the same film are preserved.
        """
        _require_non_empty(film, "film")
        _require(isinstance(gadgets, Mapping), "gadgets must be a mapping of name to payload")
        self._gadgets.setdefault(film, {}).update(gadgets)

    def lookup(self, film: str, gadget: str) -> Any:
        """Return the registered gadget for ``film``/``gadget``.

        Raises ``KeyError`` with an actionable message when either is missing.
        """
        film_gadgets = self._gadgets.get(film)
        if film_gadgets is None:
            raise KeyError(f"no gadgets registered for film {film!r}")
        try:
            return film_gadgets[gadget]
        except KeyError:
            raise KeyError(f"no gadget {gadget!r} registered for film {film!r}") from None

    def drop(self, film: str, gadget: str) -> None:
        """Remove a single gadget; the film entry disappears with its last gadget."""
        film_gadgets = self._gadgets.get(film)
        if film_gadgets is None:
            raise KeyError(f"no gadgets registered for film {film!r}")
        if gadget not in film_gadgets:
            raise KeyError(f"no gadget {gadget!r} registered for film {film!r}")
        del film_gadgets[gadget]
        if not film_gadgets:
            del self._gadgets[film]

    def drop_film(self, film: str) -> None:
        """Remove every gadget registered for a film."""
        if film not in self._gadgets:
            raise KeyError(f"no gadgets registered for film {film!r}")
        del self._gadgets[film]

    def films(self) -> tuple[str, ...]:
        """All film slugs with registered gadgets, in insertion order."""
        return tuple(self._gadgets)

    def gadgets_for(self, film: str) -> tuple[str, ...]:
        """Gadget names for a film, in insertion order (empty if unknown)."""
        return tuple(self._gadgets.get(film, {}))

    def contains(self, film: str, gadget: str) -> bool:
        """True when ``gadget`` is registered for ``film``."""
        return film in self._gadgets and gadget in self._gadgets[film]

    def __contains__(self, film: object) -> bool:
        return film in self._gadgets

    def __len__(self) -> int:
        return len(self._gadgets)


class MissionRegistry:
    """Registry of discovered mission providers, keyed by film slug."""

    def __init__(self) -> None:
        self._providers: dict[str, MissionProvider] = {}

    def register(self, provider: MissionProvider) -> None:
        """Register a provider under its ``film`` slug (replacing any prior)."""
        slug = getattr(provider, "film", None)
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError("provider.film must be a non-empty string")
        self._providers[slug] = provider

    def register_all(self, providers: Mapping[str, MissionProvider]) -> None:
        """Register a mapping of slug → provider (e.g. the result of ``discover``)."""
        for provider in providers.values():
            self.register(provider)

    def lookup(self, slug: str) -> MissionProvider:
        """Return the provider registered for ``slug`` or raise ``KeyError``."""
        try:
            return self._providers[slug]
        except KeyError:
            raise KeyError(f"no mission provider registered for slug {slug!r}") from None

    def drop(self, slug: str) -> None:
        """Remove the provider registered for ``slug`` or raise ``KeyError``."""
        if slug not in self._providers:
            raise KeyError(f"no mission provider registered for slug {slug!r}")
        del self._providers[slug]

    def slugs(self) -> tuple[str, ...]:
        """All registered film slugs, in insertion order."""
        return tuple(self._providers)

    def providers(self) -> tuple[MissionProvider, ...]:
        """All registered providers, in insertion order."""
        return tuple(self._providers.values())

    def __len__(self) -> int:
        return len(self._providers)

    def __iter__(self) -> Iterator[MissionProvider]:
        return iter(self._providers.values())

    def __contains__(self, slug: object) -> bool:
        return slug in self._providers
