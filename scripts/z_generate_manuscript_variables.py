"""Generate the manuscript ``{{TOKEN}}`` variable map.

Writes ``output/data/manuscript_variables.json`` (a deterministic ``{token:
value}`` mapping computed by :func:`you_only_live_twice.manuscript_variables.
generate_variables`). Unlike the exemplar this tree is local-only, so the
writer resolves every token from the deterministic scenario — there is no
``--allow-draft`` fallback because no token can be unresolved by construction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from you_only_live_twice.manuscript_variables import generate_variables


def main() -> int:
    variables = generate_variables()
    out_dir = _ROOT / "output" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "manuscript_variables.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(variables, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"[VOLCANO] wrote {out_path} ({len(variables)} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
