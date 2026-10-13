#!/usr/bin/env python3
"""Assemble the one-download release ZIP for the Blueprint Packager.

The ZIP unpacks to a single folder, ``brightspace-blueprint-packager-v<version>/``,
holding a clean ``git archive`` of one commit plus ``release_manifest.json``:
the version, the tag, the commit, the date, every file's SHA-256, and the
Workbench commit the vendored engine is pinned at. A ``.sha256`` sidecar is
written beside the ZIP.

Everything in the manifest comes from the archived commit, never from the
working tree: the version is read from ``blueprint_packager/__init__.py`` at
that commit and the vendor pin from ``vendor/coursecraft_workbench/MANIFEST.json``
at that commit, so a build cannot pair one commit's files with another's
metadata. ``--ref`` names the commit to archive (default HEAD). ``--tag``
names the release tag; the builder checks that the tag exists, that it points
at the archived commit, and that its name is ``v<version>`` for that commit's
tree, and it refuses a dirty worktree for a tagged build. Without ``--tag``
the builder records a ``v<version>`` tag found at the commit, and otherwise
writes ``"tag": null``: an unreleased build, which the output says.

Follows the Blueprint Wizard runner's scripts/make_release_bundle.py
(brightspace-blueprint-runner, commit 85cef27) in shape; this tool has one
repository, so there is no sibling bundle to pair.

    python3 scripts/make_release_bundle.py --ref v0.3.0 --tag v0.3.0   # a release
    python3 scripts/make_release_bundle.py                             # HEAD, unreleased
    python3 scripts/make_release_bundle.py --allow-dirty --out-dir /tmp/rel
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
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
VERSION_FILE = "blueprint_packager/__init__.py"
VENDOR_MANIFEST = "vendor/coursecraft_workbench/MANIFEST.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def resolve_commit(ref: str, root: Path = ROOT) -> str:
    """The full commit id a ref names, or a clear refusal."""
    try:
        return git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", root=root)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"{ref!r} is not a commit in {root}: {(exc.stderr or '').strip() or 'unknown ref'}") from exc


def show_file(commit: str, path: str, root: Path = ROOT) -> str | None:
    """A file's text at a commit, or None when the commit has no such file."""
    try:
        return git("show", f"{commit}:{path}", root=root)
    except subprocess.CalledProcessError:
        return None


def version_at(commit: str, root: Path = ROOT) -> str:
    text = show_file(commit, VERSION_FILE, root=root)
    match = re.search(r'^__version__ = "([^"]+)"', text or "", re.M)
    if not match:
        raise SystemExit(f"{VERSION_FILE} at {commit[:12]} has no __version__")
    return match.group(1)


def vendored_pin_at(commit: str, root: Path = ROOT) -> dict[str, Any]:
    text = show_file(commit, VENDOR_MANIFEST, root=root)
    try:
        data = json.loads(text or "")
    except ValueError:
        return {}
    return {"commit": data.get("commit"), "commit_short": data.get("commit_short"),
            "files": len(data.get("files") or []), "source": data.get("source") or data.get("source_repository")}


def tag_at(commit: str, version: str, root: Path = ROOT) -> str | None:
    """``v<version>`` when such a tag points at the commit, else None."""
    wanted = f"v{version}"
    tags = git("tag", "--points-at", commit, root=root).split()
    return wanted if wanted in tags else None


def verify_tag(tag: str, commit: str, version: str, root: Path = ROOT) -> None:
    """A release tag must exist, point at the archived commit, and be named for its version."""
    try:
        tagged = git("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}", root=root)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"tag {tag!r} does not exist in {root}; create it on the release commit first") from exc
    if tagged != commit:
        raise SystemExit(f"tag {tag} points at {tagged[:12]}, not at the archived commit {commit[:12]}")
    if tag != f"v{version}":
        raise SystemExit(f"tag {tag} does not match version {version} at {commit[:12]}; the tag must be v{version}")


def release_manifest(staged: Path, *, version: str, commit: str, tag: str | None, ref: str, dirty: bool,
                     now: dt.datetime, vendored: dict[str, Any]) -> dict[str, Any]:
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
        "tag": tag,
        "commit": commit,
        "built_at_utc": now.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "build": {"ref": ref, "tag_verified": tag is not None, "dirty_worktree": dirty},
        "vendored_workbench": vendored,
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


def build(out_dir: Path, *, ref: str = "HEAD", tag: str | None = None, allow_dirty: bool = False,
          root: Path = ROOT, now: dt.datetime | None = None) -> tuple[Path, Path]:
    """Archive `ref`, write the manifest from that commit, and return (zip, sidecar)."""
    dirty = bool(git("status", "--porcelain", root=root))
    if dirty and tag:
        raise SystemExit("a tagged release is built from a clean worktree; commit or stash the changes first")
    if dirty and not allow_dirty:
        raise SystemExit("the worktree has uncommitted changes; commit them, or pass --allow-dirty for an unreleased build of the committed tree")
    commit = resolve_commit(ref, root=root)
    version = version_at(commit, root=root)
    if tag:
        verify_tag(tag, commit, version, root=root)
    else:
        tag = tag_at(commit, version, root=root)
    top_level = f"{PRODUCT}-v{version}"
    with tempfile.TemporaryDirectory() as temp:
        staged = Path(temp) / top_level
        staged.mkdir()
        archive = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", commit], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(staged)], input=archive, check=True)
        manifest = release_manifest(staged, version=version, commit=commit, tag=tag, ref=ref, dirty=dirty,
                                    now=now or dt.datetime.now(dt.timezone.utc), vendored=vendored_pin_at(commit, root=root))
        (staged / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        verify_manifest(staged)
        out_zip = out_dir / f"{top_level}.zip"
        write_zip(staged, out_zip, top_level=top_level)
    sidecar = out_zip.with_suffix(".zip.sha256")
    sidecar.write_text(f"{sha256_file(out_zip)}  {out_zip.name}\n", encoding="utf-8")
    return out_zip, sidecar


def read_manifest(out_zip: Path) -> dict[str, Any]:
    with zipfile.ZipFile(out_zip) as archive:
        top = archive.namelist()[0].split("/", 1)[0]
        return json.loads(archive.read(f"{top}/{MANIFEST_NAME}"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--ref", default="HEAD", help="the commit to archive (a tag, branch or sha; default HEAD)")
    parser.add_argument("--tag", help="the release tag; must point at --ref and be named v<version> of that tree")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="build an unreleased ZIP of the committed tree although the worktree has changes (never with --tag)")
    args = parser.parse_args(argv)
    out_zip, sidecar = build(args.out_dir, ref=args.ref, tag=args.tag, allow_dirty=args.allow_dirty)
    manifest = read_manifest(out_zip)
    print(f"release: {out_zip}")
    print(f"sha256:  {sidecar.read_text(encoding='utf-8').split()[0]}  ({sidecar.name})")
    print(f"commit:  {manifest['commit']}  (ref {args.ref})")
    if manifest["tag"]:
        print(f"tag:     {manifest['tag']}  verified at that commit")
        print(f"next:    gh release create {manifest['tag']} {out_zip} {sidecar} --repo timebeing92/{PRODUCT} "
              f"--title {manifest['tag']} --notes-file RELEASE_NOTES.md")
    else:
        print(f"tag:     none; this is an unreleased build of {manifest['commit'][:12]} (tag v{manifest['version']} is not at that commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
