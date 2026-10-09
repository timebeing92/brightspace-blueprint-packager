#!/usr/bin/env python3
"""Assemble the one-download release ZIP for the Blueprint Packager.

The ZIP unpacks to a single folder, ``brightspace-blueprint-packager-v<version>/``,
holding a clean ``git archive`` of HEAD plus ``release_manifest.json``: the
version, the commit, the date, every file's SHA-256, and the Workbench commit
the vendored engine is pinned at. A ``.sha256`` sidecar is written beside the
ZIP. The builder refuses a dirty worktree unless told otherwise, so a release
is always one commit.

Follows the Blueprint Wizard runner's scripts/make_release_bundle.py
(brightspace-blueprint-runner, commit 85cef27) in shape; this tool has one
repository, so there is no sibling bundle to pair.

    python3 scripts/make_release_bundle.py            # dist/brightspace-blueprint-packager-v<version>.zip
    python3 scripts/make_release_bundle.py --allow-dirty --out-dir /tmp/rel
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = "coursecraft.packager_release/1"
MANIFEST_NAME = "release_manifest.json"
PRODUCT = "brightspace-blueprint-packager"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_version(root: Path = ROOT) -> str:
    text = (root / "blueprint_packager" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', text, re.M)
    if not match:
        raise SystemExit("blueprint_packager/__init__.py has no __version__")
    return match.group(1)


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def vendored_pin(root: Path = ROOT) -> dict[str, Any]:
    manifest = root / "vendor" / "coursecraft_workbench" / "MANIFEST.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {"commit": data.get("commit"), "commit_short": data.get("commit_short"),
            "files": len(data.get("files") or []), "source": data.get("source") or data.get("source_repository")}


def release_manifest(staged: Path, *, version: str, commit: str, now: dt.datetime, root: Path = ROOT) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in staged.rglob("*") if p.is_file()):
        rel = path.relative_to(staged).as_posix()
        if rel == MANIFEST_NAME:
            continue
        files.append({"path": rel, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return {
        "schema": MANIFEST_SCHEMA,
        "product": PRODUCT,
        "version": version,
        "tag": f"v{version}",
        "commit": commit,
        "built_at_utc": now.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "vendored_workbench": vendored_pin(root),
        "file_count": len(files),
        "files": files,
    }


def verify_manifest(folder: Path) -> dict[str, Any]:
    """Check an unpacked release folder against its manifest; raise ValueError on any difference."""
    manifest_path = folder / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"unexpected manifest schema {manifest.get('schema')!r}")
    listed = {entry["path"]: entry["sha256"] for entry in manifest.get("files", [])}
    present = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} - {MANIFEST_NAME}
    missing = sorted(set(listed) - present)
    extra = sorted(present - set(listed))
    if missing or extra:
        raise ValueError(f"manifest and folder differ: missing {missing[:5]}, extra {extra[:5]}")
    wrong = [rel for rel, digest in listed.items() if sha256_file(folder / rel) != digest]
    if wrong:
        raise ValueError(f"hash mismatch: {wrong[:5]}")
    return manifest


def write_zip(folder: Path, out_zip: Path, *, top_level: str) -> None:
    """A deterministic ZIP: sorted entries, fixed timestamps, one top-level folder."""
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            rel = path.relative_to(folder).as_posix()
            info = zipfile.ZipInfo(f"{top_level}/{rel}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix in {".sh", ".command"} or path.name == "bpk.py" else 0o644) << 16
            archive.writestr(info, path.read_bytes())


def build(out_dir: Path, *, allow_dirty: bool = False, root: Path = ROOT, now: dt.datetime | None = None) -> tuple[Path, Path]:
    dirty = git("status", "--porcelain", root=root)
    if dirty and not allow_dirty:
        raise SystemExit("the worktree has uncommitted changes; commit them or pass --allow-dirty")
    version = read_version(root)
    commit = git("rev-parse", "HEAD", root=root)
    top_level = f"{PRODUCT}-v{version}"
    with tempfile.TemporaryDirectory() as temp:
        staged = Path(temp) / top_level
        staged.mkdir()
        archive = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", "HEAD"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(staged)], input=archive, check=True)
        manifest = release_manifest(staged, version=version, commit=commit, now=now or dt.datetime.now(dt.timezone.utc), root=root)
        (staged / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        verify_manifest(staged)
        out_zip = out_dir / f"{top_level}.zip"
        write_zip(staged, out_zip, top_level=top_level)
    sidecar = out_zip.with_suffix(".zip.sha256")
    sidecar.write_text(f"{sha256_file(out_zip)}  {out_zip.name}\n", encoding="utf-8")
    return out_zip, sidecar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--allow-dirty", action="store_true", help="build from a worktree with uncommitted changes (not for a real release)")
    args = parser.parse_args(argv)
    out_zip, sidecar = build(args.out_dir, allow_dirty=args.allow_dirty)
    print(f"release: {out_zip}")
    print(f"sha256:  {sidecar.read_text(encoding='utf-8').split()[0]}  ({sidecar.name})")
    print(f"next:    gh release create v{read_version()} {out_zip} {sidecar} --repo timebeing92/{PRODUCT} --title v{read_version()} --notes-file RELEASE_NOTES.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
