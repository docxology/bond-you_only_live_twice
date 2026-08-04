"""Preflight: verify the VOLCANO provider satisfies the frozen BOND-API protocol.

Checks protocol-surface integrity, that the provider passes the runtime
protocol check, and that its gadgets register cleanly. Exits 0 only when every
check passes (argparse/SystemExit misuse is not used here; we return the code).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from bond_api.protocol import MissionProvider as ProtocolProvider
from bond_api.protocol import protocol_surface
from bond_api.registry import GadgetRegistry

from you_only_live_twice.mission import MissionProvider, register_gadgets


def main() -> int:
    surface = protocol_surface()
    print(f"[VOLCANO] protocol identity  {surface['identity']} ({surface['codename']})")
    print(f"[VOLCANO] protocol dataclasses {len(surface['dataclasses'])}")
    print(f"[VOLCANO] protocol provider methods {tuple(surface['provider_methods'])}")

    provider = MissionProvider()
    checks = [
        (
            "is instance of MissionProvider protocol",
            isinstance(provider, ProtocolProvider),
        ),
        ("film slug matches", provider.film == "you_only_live_twice"),
        ("brief resolves", len(provider.brief().objectives) == 3),
        ("gadgets register", _gadget_count() > 0),
    ]
    ok = True
    for label, passed in checks:
        print(f"[VOLCANO] check  {'PASS' if passed else 'FAIL'}  {label}")
        ok = ok and passed

    if not ok:
        print("[VOLCANO] preflight FAILED")
        return 1
    print("[VOLCANO] preflight OK")
    return 0


def _gadget_count() -> int:
    registry = GadgetRegistry()
    register_gadgets(registry)
    return len(registry.gadgets_for("you_only_live_twice"))


if __name__ == "__main__":
    raise SystemExit(main())
