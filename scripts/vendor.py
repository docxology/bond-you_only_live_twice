#!/usr/bin/env python3
"""Check, and refresh, the vendored copies under ``vendor/``.

A vendored copy is a dependency, not a fork: every file under ``vendor/<name>/``
is a byte-for-byte copy of its upstream path at the commit recorded in
``vendor/<name>/PROVENANCE.json``. An edit made here splits the copy from
upstream, so the edit belongs upstream and is re-copied with ``--refresh``.
``--check`` is what enforces that, and it runs inside the package's own pytest gate
(``tests/test_vendor_provenance.py``), so a copy that drifts turns that repository red.

    scripts/vendor.py --check
    scripts/vendor.py --refresh --from <upstream checkout> [--sha <commit>]
    scripts/vendor.py --refresh            # re-seal the checker hash; refuses on drift

Only recorded paths are copied and checked. Artefacts the build writes into the
copy (``build/``, ``*.egg-info/``) are outside the recorded set and git-ignored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR_ROOT = ROOT / "vendor"
CHECKER = Path(__file__).resolve()
MANIFEST_NAME = "PROVENANCE.json"
VENDOR_NOTE = "VENDOR.md"
SHA_MARKER = "<!-- vendored-sha: {sha} -->"
REQUIRED = (
    "package",
    "module_path",
    "source_repository",
    "sha",
    "copied_paths",
    "sha256",
)
#: The project metadata a `directory` source is resolved from, at the copy's root.
METADATA_FILES = ("pyproject.toml", "LICENSE", "README.md")


def default_module_path(distribution: str) -> str:
    """The copied module tree for a distribution: ``bond-api`` -> ``src/bond_api``.

    The directory keeps the distribution name, because a vendored project may
    declare sibling sources of its own (``../bond-api``); inside ``vendor/``
    those resolve to the sibling copy exactly as they resolved in the suite.
    """
    return f"src/{distribution.replace('-', '_')}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate(hashes: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(hashes):
        digest.update(f"{name}\0{hashes[name]}\n".encode())
    return digest.hexdigest()


@dataclass
class Manifest:
    """The record of one vendored copy, as stored beside it."""

    path: Path
    package: str
    module_path: str
    source_repository: str
    sha: str
    copied_paths: list[str]
    sha256: dict[str, str]
    aggregate_sha256: str
    checker_sha256: str

    @property
    def directory(self) -> Path:
        return self.path.parent

    @classmethod
    def load(cls, path: Path) -> Manifest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SystemExit(f"{path}: not a JSON object")
        missing = [key for key in REQUIRED if key not in raw]
        if missing:
            raise SystemExit(f"{path}: missing key(s) {', '.join(missing)}")
        copied = raw["copied_paths"]
        hashes = raw["sha256"]
        if not isinstance(copied, list) or not all(
            isinstance(item, str) for item in copied
        ):
            raise SystemExit(f"{path}: copied_paths must be a list of strings")
        if not isinstance(hashes, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in hashes.items()
        ):
            raise SystemExit(f"{path}: sha256 must map paths to digests")
        return cls(
            path=path,
            package=str(raw["package"]),
            module_path=str(raw["module_path"]),
            source_repository=str(raw["source_repository"]),
            sha=str(raw["sha"]),
            copied_paths=[str(item) for item in copied],
            sha256={str(key): str(value) for key, value in hashes.items()},
            aggregate_sha256=str(raw.get("aggregate_sha256", "")),
            checker_sha256=str(raw.get("checker_sha256", "")),
        )

    def module_tree(self) -> list[str]:
        tree = self.directory / self.module_path
        if not tree.is_dir():
            raise SystemExit(f"{tree} does not exist; the copy is incomplete")
        found = [path for path in tree.rglob("*") if path.is_file()]
        return sorted(str(path.relative_to(self.directory)) for path in found)

    def note_text(self) -> str:
        metadata = [
            name
            for name in self.copied_paths
            if not name.startswith(f"{self.module_path}/")
        ]
        listed = ", ".join(f"`{name}`" for name in metadata)
        return f"""{SHA_MARKER.format(sha=self.sha)}
# Vendored `{self.package}`

This directory is a **copy, not a fork**: every file here is byte-identical to
its upstream path at the commit below, and `scripts/vendor.py --check` fails the
moment that stops being true.

| | |
| --- | --- |
| Upstream | `{self.source_repository}` |
| Commit | `{self.sha}` |
| Copied | {len(self.copied_paths)} files — `{self.module_path}/**` plus {listed} |
| Not copied | upstream `tests/`, `docs/`, `uv.lock`, and CI configuration |

**Why it is here.** The package is not installable from an index, and the
primary consumer of this repository clones it *alone* — Dependabot's update jobs
run in a single-repository checkout — so a suite-relative path cannot resolve
there.

**Refreshing.** Re-copy from a clean upstream checkout and re-record:

```bash
scripts/vendor.py --refresh --from <path to a {self.package} checkout> [--sha <commit>]
```

Edits belong upstream. A change made here is caught by
`scripts/vendor.py --check`, which `tests/test_vendor_provenance.py` runs inside
this package's own gate.
"""


def record(manifest: Manifest) -> None:
    """Write the manifest and its human note from the copy as it stands on disk."""
    names = sorted(
        [name for name in METADATA_FILES if (manifest.directory / name).is_file()]
        + manifest.module_tree()
    )
    hashes = {name: sha256(manifest.directory / name) for name in names}
    manifest.copied_paths = names
    manifest.sha256 = hashes
    manifest.aggregate_sha256 = aggregate(hashes)
    manifest.checker_sha256 = sha256(CHECKER)
    body = {
        "package": manifest.package,
        "module_path": manifest.module_path,
        "source_repository": manifest.source_repository,
        "sha": manifest.sha,
        "copied_paths": manifest.copied_paths,
        "sha256": manifest.sha256,
        "aggregate_sha256": manifest.aggregate_sha256,
        "checker_sha256": manifest.checker_sha256,
    }
    manifest.path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    (manifest.directory / VENDOR_NOTE).write_text(
        manifest.note_text(), encoding="utf-8"
    )


def manifests() -> list[Manifest]:
    if not VENDOR_ROOT.is_dir():
        raise SystemExit(f"{VENDOR_ROOT} does not exist; nothing is vendored")
    found = sorted(VENDOR_ROOT.glob(f"*/{MANIFEST_NAME}"))
    if not found:
        raise SystemExit(f"{VENDOR_ROOT} holds no {MANIFEST_NAME}; nothing is vendored")
    for directory in sorted(path for path in VENDOR_ROOT.iterdir() if path.is_dir()):
        if not (directory / MANIFEST_NAME).is_file():
            raise SystemExit(
                f"{directory}: a vendored directory with no {MANIFEST_NAME}"
            )
    return [Manifest.load(path) for path in found]


def check_one(manifest: Manifest) -> list[str]:
    """The findings for one vendored copy; an empty list means it matches its record."""
    findings: list[str] = []
    for name, digest in sorted(manifest.sha256.items()):
        path = manifest.directory / name
        if not path.is_file():
            findings.append(f"{name}: recorded, missing on disk")
        elif sha256(path) != digest:
            findings.append(f"{name}: differs from the recorded copy")
    findings.extend(
        f"{name}: not part of the recorded copy"
        for name in manifest.module_tree()
        if name not in manifest.sha256
    )
    if manifest.aggregate_sha256 != aggregate(manifest.sha256):
        findings.append(
            "PROVENANCE.json: the aggregate hash disagrees with the per-file hashes"
        )
    note = manifest.directory / VENDOR_NOTE
    marker = SHA_MARKER.format(sha=manifest.sha)
    if not note.is_file():
        findings.append(f"{VENDOR_NOTE}: missing")
    elif marker not in note.read_text(encoding="utf-8"):
        findings.append(f"{VENDOR_NOTE}: does not record {marker}")
    if manifest.checker_sha256 != sha256(CHECKER):
        findings.append(
            "scripts/vendor.py: changed since the record; re-seal with --refresh"
        )
    return findings


def check() -> int:
    total = 0
    for manifest in manifests():
        findings = check_one(manifest)
        total += len(findings)
        state = "ok" if not findings else f"{len(findings)} finding(s)"
        print(f"vendor/{manifest.package}: {state}")
        for finding in findings:
            print(f"  - {finding}")
    print(f"{total} finding(s)")
    return 1 if total else 0


def git(source: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise SystemExit(
            f"{source}: git {' '.join(arguments)}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def source_sha(source: Path, given: str | None) -> str:
    if not (source / ".git").exists():
        if not given:
            raise SystemExit(
                f"{source}: not a git checkout, so --sha <commit> is required"
            )
        if not re.fullmatch(r"[0-9a-f]{40}", given):
            raise SystemExit(
                f"--sha must be a full 40-character commit SHA, not {given!r}"
            )
        return given
    if git(source, "status", "--porcelain"):
        raise SystemExit(
            f"{source}: the checkout is not clean; refresh from a clean commit"
        )
    resolved = git(source, "rev-parse", "HEAD")
    if given and given != resolved:
        raise SystemExit(f"{source}: HEAD is {resolved}, not the requested {given}")
    return resolved


def refresh_from(
    package: str,
    source: Path,
    given: str | None,
    repository: str | None,
    module_path: str | None,
) -> int:
    manifest_path = VENDOR_ROOT / package / MANIFEST_NAME
    if manifest_path.is_file():
        manifest = Manifest.load(manifest_path)
        manifest.package = package
    else:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = Manifest(
            path=manifest_path,
            package=package,
            module_path=module_path or default_module_path(package),
            source_repository=repository or f"docxology/{package.replace('_', '-')}",
            sha="",
            copied_paths=[],
            sha256={},
            aggregate_sha256="",
            checker_sha256="",
        )
        print(f"vendor/{package}: no record yet; creating one")
    if not (source / manifest.module_path).is_dir():
        raise SystemExit(f"{source}: does not look like a {manifest.package} checkout")
    manifest.sha = source_sha(source, given)
    wanted = [name for name in METADATA_FILES if (source / name).is_file()]
    tree = source / manifest.module_path
    wanted += sorted(
        str(path.relative_to(source)) for path in tree.rglob("*") if path.is_file()
    )
    for name in wanted:
        destination = manifest.directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, destination)
    for name in manifest.module_tree():
        if name not in wanted:
            (manifest.directory / name).unlink()
    record(manifest)
    print(
        f"vendor/{package}: refreshed from {source} at {manifest.sha} "
        f"({len(wanted)} files)"
    )
    return 0


def reseal() -> int:
    """Re-record the checker hash after a deliberate change; refuse on drift."""
    found = manifests()
    for manifest in found:
        drifted = [
            name
            for name, digest in sorted(manifest.sha256.items())
            if not (manifest.directory / name).is_file()
            or sha256(manifest.directory / name) != digest
        ]
        if drifted:
            raise SystemExit(
                f"vendor/{manifest.package}: {len(drifted)} file(s) drifted; "
                f"refresh from upstream instead: {', '.join(drifted[:3])}"
            )
        record(manifest)
    print(f"{len(found)} copy/copies re-sealed against scripts/vendor.py")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="verify every copy against its record"
    )
    parser.add_argument(
        "--refresh", action="store_true", help="re-copy from a source checkout"
    )
    parser.add_argument(
        "--package", help="the vendored distribution, e.g. bond-api (its directory)"
    )
    parser.add_argument(
        "--from", dest="source", help="a checkout of the upstream package"
    )
    parser.add_argument("--sha", help="the upstream commit the copy comes from")
    parser.add_argument("--repository", help="the upstream repository, owner/name")
    parser.add_argument(
        "--module-path", help="the copied module tree, e.g. src/bond_api"
    )
    args = parser.parse_args(argv)
    if args.check == args.refresh:
        parser.error("choose exactly one of --check and --refresh")
    if args.check:
        return check()
    if args.source:
        if not args.package:
            parser.error("--from requires --package")
        return refresh_from(
            args.package,
            Path(args.source).resolve(),
            args.sha,
            args.repository,
            args.module_path,
        )
    if args.sha:
        parser.error("--sha is only meaningful with --from")
    return reseal()


if __name__ == "__main__":
    sys.exit(main())
