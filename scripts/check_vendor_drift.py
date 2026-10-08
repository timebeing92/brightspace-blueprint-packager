#!/usr/bin/env python3
"""Compare the vendored Workbench files with upstream.

Usage:
    python3 scripts/check_vendor_drift.py /path/to/coursecraft_workbench
    python3 scripts/check_vendor_drift.py /path/to/coursecraft_workbench --commit 9d3a620abc

Without --commit: every vendored file is compared with the same path at the
pinned commit (recorded in vendor/coursecraft_workbench/MANIFEST.json) and with
the checkout's current working file. Drift from the pinned commit means the
vendored copy was edited here, which must not happen; exit 1. Drift from the
checkout's current file is reported as information: upstream has moved, and a
re-pin may be due; exit 0.

With --commit: every vendored file is replaced by its content at that commit
and the manifest is rewritten. Review the diff before committing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "vendor" / "coursecraft_workbench"
MANIFEST = VENDOR / "MANIFEST.json"


def git_show(checkout: Path, commit: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "-C", str(checkout), "show", f"{commit}:{path}"], capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(checkout: Path) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    commit = manifest["commit"]
    edited_here: list[str] = []
    upstream_moved: list[str] = []
    missing: list[str] = []
    for entry in manifest["files"]:
        rel = entry["path"]
        local = VENDOR / rel
        if not local.is_file():
            missing.append(rel)
            continue
        local_hash = sha256(local.read_bytes())
        pinned = git_show(checkout, commit, rel)
        if pinned is None:
            missing.append(f"{rel} (not at {commit[:7]} in {checkout})")
            continue
        if sha256(pinned) != local_hash or entry["sha256"] != local_hash:
            edited_here.append(rel)
        current = checkout / rel
        if current.is_file() and sha256(current.read_bytes()) != local_hash:
            upstream_moved.append(rel)
    print(f"vendored commit: {commit[:7]}; files: {len(manifest['files'])}")
    if missing:
        print("missing:", *missing, sep="\n  ")
    if edited_here:
        print("DRIFT from the pinned commit (vendored copies were edited here, or the manifest is stale):", *edited_here, sep="\n  ")
    if upstream_moved:
        print("upstream has moved since the pin (information; consider --commit to re-pin):", *upstream_moved, sep="\n  ")
    if not (missing or edited_here or upstream_moved):
        print("no drift: vendored files equal the pinned commit and the checkout's current files")
    return 1 if (missing or edited_here) else 0


def repin(checkout: Path, commit: str) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    full = subprocess.run(["git", "-C", str(checkout), "rev-parse", commit], capture_output=True, text=True, check=True).stdout.strip()
    files = []
    for entry in manifest["files"]:
        rel = entry["path"]
        data = git_show(checkout, full, rel)
        if data is None:
            print(f"not at {commit}: {rel}; kept as is", file=sys.stderr)
            files.append(entry)
            continue
        (VENDOR / rel).parent.mkdir(parents=True, exist_ok=True)
        (VENDOR / rel).write_bytes(data)
        files.append({"path": rel, "sha256": sha256(data), "bytes": len(data)})
    manifest.update({"commit": full, "commit_short": full[:7], "files": files})
    from datetime import date

    manifest["pinned_on"] = date.today().isoformat()
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"re-pinned {len(files)} files at {full[:7]}; review `git diff vendor/` before committing")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkout", help="path to a coursecraft_workbench checkout")
    parser.add_argument("--commit", help="re-pin every vendored file at this commit")
    args = parser.parse_args()
    checkout = Path(args.checkout).expanduser().resolve()
    if not (checkout / ".git").exists():
        print(f"not a git checkout: {checkout}", file=sys.stderr)
        return 2
    return repin(checkout, args.commit) if args.commit else check(checkout)


if __name__ == "__main__":
    raise SystemExit(main())
