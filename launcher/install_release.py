#!/usr/bin/env python3
"""Install a verified Blueprint Packager release beside the current one.

A release is one ZIP with one top-level folder and a ``release_manifest.json``
naming every file and its SHA-256. Installing means: fetch the ZIP (from
GitHub Releases through ``gh`` or a token, or from a local file), check every
member name is safe, unpack into a staging folder, verify every hash against
the manifest, move the folder into place next to the current install, and
point ``.blueprint-packager-current`` at it. The pointer is written atomically,
so the launchers never see a half-installed version; the previous version is
left where it was. Remembered answers (``.last_run.json``) are carried over.

Installing a release that is already in place does not trust the old receipt
alone: every file the manifest lists is checked against the installed folder
(runtime state such as ``.venv``, remembered answers, the update-check cache
and logs is left alone). A difference is refused, naming the files, unless
``--repair`` asks for them to be restored from the verified archive.

Adapted in approach from the Blueprint Wizard runner's launcher/install_release.py
(brightspace-blueprint-runner, commit 85cef27), without its managed-root
machinery: this tool has one folder per version and one pointer file.

    python3 launcher/install_release.py --latest                  # from GitHub Releases
    python3 launcher/install_release.py --archive path/to/release.zip
    python3 launcher/install_release.py --latest --restart        # then start the new version
    python3 launcher/install_release.py --archive release.zip --repair   # restore changed release files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_DIR = HERE.parent
sys.path.insert(0, str(REPO_DIR / "scripts"))

import update_check  # noqa: E402

MANIFEST_NAME = "release_manifest.json"
MANIFEST_SCHEMA = "coursecraft.packager_release/1"
POINTER_NAME = ".blueprint-packager-current"
RECEIPT_NAME = "INSTALL_RECEIPT.json"
MAX_ARCHIVE_FILES = 20_000
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}
CARRIED_FILES = (".last_run.json",)


class ReleaseInstallError(RuntimeError):
    """A release archive failed verification or safe installation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- fetching
def download_latest(destination: Path, *, status: update_check.UpdateStatus | None = None) -> tuple[Path, str]:
    """Download the latest release's ZIP asset into `destination`; return (path, tag)."""
    if status is None:
        status = update_check.check_latest_release(current_version="0.0.0", cache_path=destination / ".check.json", force=True)
    if status.state == "no_access":
        raise ReleaseInstallError(status.error)
    if status.state == "unavailable" or not status.latest_tag:
        raise ReleaseInstallError(f"the latest release could not be read: {status.error or 'no release found'}")
    if not status.asset_name:
        raise ReleaseInstallError(f"release {status.latest_tag} has no ZIP asset; build one with scripts/make_release_bundle.py")
    destination.mkdir(parents=True, exist_ok=True)
    mode = update_check.access_mode()
    target = destination / status.asset_name
    if mode == "gh":
        gh = shutil.which("gh") or "gh"
        result = subprocess.run([gh, "release", "download", status.latest_tag, "--repo", update_check.REPO,
                                 "--pattern", status.asset_name, "--dir", str(destination), "--clobber"],
                                capture_output=True, text=True, check=False)
        if result.returncode != 0 or not target.is_file():
            raise ReleaseInstallError((result.stderr or result.stdout).strip() or "gh release download failed")
        return target, status.latest_tag
    # a token or nothing: the repository is public, so the asset URL answers without credentials
    headers = {"Accept": "application/octet-stream", "User-Agent": "Blueprint-Packager-Installer"}
    if mode == "token":
        headers["Authorization"] = f"Bearer {update_check.github_token()}"
    request = urllib.request.Request(status.asset_url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as out:
            shutil.copyfileobj(response, out)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise ReleaseInstallError("GitHub is rate-limiting anonymous downloads from this address; try later, "
                                      "or sign in with `gh auth login` or set GITHUB_TOKEN") from exc
        raise ReleaseInstallError(f"the release asset could not be downloaded: HTTP {exc.code}") from exc
    return target, status.latest_tag


# --------------------------------------------------------------------------- verification
def validate_member_name(name: str) -> PurePosixPath:
    if not name or "\\" in name or "\x00" in name:
        raise ReleaseInstallError(f"unsafe ZIP member name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReleaseInstallError(f"unsafe ZIP member path: {name!r}")
    for part in path.parts:
        if part.endswith((" ", ".")) or ":" in part or part.split(".", 1)[0].upper() in WINDOWS_RESERVED:
            raise ReleaseInstallError(f"non-portable ZIP member path: {name!r}")
    return path


def validated_members(archive: zipfile.ZipFile) -> tuple[str, list[zipfile.ZipInfo]]:
    members = archive.infolist()
    if not members or len(members) > MAX_ARCHIVE_FILES:
        raise ReleaseInstallError("release ZIP has an invalid number of entries")
    total, tops, seen = 0, set(), set()
    for info in members:
        path = validate_member_name(info.filename.rstrip("/"))
        tops.add(path.parts[0])
        key = "/".join(path.parts).casefold()
        if key in seen:
            raise ReleaseInstallError(f"duplicate or case-colliding path: {info.filename}")
        seen.add(key)
        if info.flag_bits & 0x1:
            raise ReleaseInstallError("encrypted ZIP members are not supported")
        if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF):
            raise ReleaseInstallError(f"release ZIP contains a symbolic link: {info.filename}")
        total += info.file_size
        if total > MAX_ARCHIVE_BYTES:
            raise ReleaseInstallError("release ZIP expands beyond the safety limit")
    if len(tops) != 1:
        raise ReleaseInstallError("release ZIP must contain exactly one top-level folder")
    return next(iter(tops)), members


def extract_members(archive: zipfile.ZipFile, members: list[zipfile.ZipInfo], destination: Path) -> None:
    for info in members:
        relative = validate_member_name(info.filename.rstrip("/"))
        target = destination.joinpath(*relative.parts)
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
        mode = (info.external_attr >> 16) & 0o777
        if mode:
            target.chmod(mode)


def verify_folder(folder: Path, *, expected_version: str | None = None) -> dict[str, Any]:
    manifest_path = folder / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ReleaseInstallError(f"release is missing {MANIFEST_NAME}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ReleaseInstallError(f"unexpected manifest schema {manifest.get('schema')!r}")
    version = str(manifest.get("version") or "")
    if expected_version and version != expected_version.lstrip("v"):
        raise ReleaseInstallError(f"release is version {version}, expected {expected_version}")
    listed = {entry["path"]: entry["sha256"] for entry in manifest.get("files", [])}
    present = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} - {MANIFEST_NAME}
    missing, extra = sorted(set(listed) - present), sorted(present - set(listed))
    if missing or extra:
        raise ReleaseInstallError(f"manifest and archive differ: missing {missing[:5]}, extra {extra[:5]}")
    wrong = [rel for rel, digest in listed.items() if sha256_file(folder / rel) != digest]
    if wrong:
        raise ReleaseInstallError(f"hash mismatch in {wrong[:5]}")
    return manifest


# --------------------------------------------------------------------------- installing
def pointer_path(install_root: Path) -> Path:
    return install_root / POINTER_NAME


def current_folder(install_root: Path) -> Path | None:
    try:
        name = pointer_path(install_root).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    candidate = install_root / name
    return candidate if name and candidate.is_dir() else None


def write_pointer(install_root: Path, folder_name: str) -> None:
    temporary = pointer_path(install_root).with_name(POINTER_NAME + ".tmp")
    temporary.write_text(folder_name + "\n", encoding="utf-8")
    os.replace(temporary, pointer_path(install_root))


def check_installed(folder: Path, manifest: dict[str, Any], *, verified: Path | None = None) -> dict[str, Any]:
    """Compare the release-owned files of an installed folder with the manifest.

    Only the files the manifest lists (and the manifest itself, when `verified`
    gives the archive's copy) are checked, so the runtime state an install
    accumulates (.venv, .last_run.json, the update-check cache, logs, the
    receipt) is neither checked nor touched."""
    missing, changed = [], []
    for entry in manifest.get("files", []):
        target = folder / entry["path"]
        if not target.is_file():
            missing.append(entry["path"])
        elif sha256_file(target) != entry["sha256"]:
            changed.append(entry["path"])
    if verified is not None:
        installed_manifest = folder / MANIFEST_NAME
        if not installed_manifest.is_file():
            missing.append(MANIFEST_NAME)
        elif installed_manifest.read_bytes() != (verified / MANIFEST_NAME).read_bytes():
            changed.append(MANIFEST_NAME)
    return {"ok": not missing and not changed, "checked": len(manifest.get("files", [])) + (verified is not None),
            "missing": missing, "changed": changed}


def repair_installed(folder: Path, verified: Path, report: dict[str, Any]) -> list[str]:
    """Restore the missing or changed release files in `folder` from the verified copy; return their paths."""
    restored = []
    for rel in [*report["missing"], *report["changed"]]:
        target = folder / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(verified / rel, target)
        restored.append(rel)
    return restored


def install_archive(archive_path: Path, install_root: Path, *, expected_version: str | None = None,
                    carry_from: Path | None = None, repair: bool = False) -> dict[str, Any]:
    archive_path = archive_path.expanduser().resolve()
    install_root = install_root.expanduser().resolve()
    if not archive_path.is_file():
        raise ReleaseInstallError(f"release ZIP not found: {archive_path}")
    install_root.mkdir(parents=True, exist_ok=True)
    staging = install_root / f".staging-{uuid.uuid4().hex}"
    try:
        with zipfile.ZipFile(archive_path) as archive:
            top_level, members = validated_members(archive)
            staging.mkdir()
            extract_members(archive, members, staging)
        extracted = staging / top_level
        manifest = verify_folder(extracted, expected_version=expected_version)
        destination = install_root / top_level
        archive_digest = sha256_file(archive_path)
        if destination.exists():
            try:
                receipt = json.loads((destination / RECEIPT_NAME).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                receipt = {}
            if receipt.get("archive_sha256") != archive_digest:
                raise ReleaseInstallError(f"{destination.name} already exists with a different or missing receipt; move it aside first")
            report = check_installed(destination, manifest, verified=extracted)
            if report["ok"]:
                write_pointer(install_root, top_level)
                return {"status": "already_installed", "version": manifest["version"], "folder": str(destination),
                        "archive_sha256": archive_digest, "checked_files": report["checked"]}
            differing = report["missing"] + report["changed"]
            if not repair:
                raise ReleaseInstallError(
                    f"{destination.name} is installed, but {len(report['missing'])} release file(s) are missing and "
                    f"{len(report['changed'])} changed (for example {', '.join(differing[:3])}); rerun with --repair to "
                    "restore them from the verified archive (.venv, remembered answers and logs are kept)")
            restored = repair_installed(destination, extracted, report)
            after = check_installed(destination, manifest, verified=extracted)
            if not after["ok"]:
                raise ReleaseInstallError(f"repair of {destination.name} left differences: {after['missing'] + after['changed']}")
            receipt["repaired_at_utc"] = update_check.utc_text(update_check.utc_now())
            receipt["repaired_files"] = restored
            (destination / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            write_pointer(install_root, top_level)
            return {"status": "repaired", "version": manifest["version"], "folder": str(destination),
                    "archive_sha256": archive_digest, "repaired": restored}
        receipt = {"schema": "coursecraft.packager_install/1", "version": manifest["version"], "commit": manifest.get("commit"),
                   "archive_name": archive_path.name, "archive_sha256": archive_digest,
                   "installed_at_utc": update_check.utc_text(update_check.utc_now()), "vendored_workbench": manifest.get("vendored_workbench")}
        (extracted / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        source = carry_from or current_folder(install_root)
        if source and source.is_dir() and source != extracted:
            for name in CARRIED_FILES:
                if (source / name).is_file():
                    shutil.copy2(source / name, extracted / name)
        os.replace(extracted, destination)
        write_pointer(install_root, top_level)
        return {"status": "installed", "version": manifest["version"], "folder": str(destination), "archive_sha256": archive_digest}
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def launcher_for(folder: Path) -> list[str]:
    if os.name == "nt":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(folder / "blueprint_packager.ps1")]
    return ["bash", str(folder / "blueprint_packager.sh")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--latest", action="store_true", help="download the latest release from GitHub Releases")
    source.add_argument("--archive", type=Path, help="a release ZIP already on disk")
    parser.add_argument("--install-root", type=Path, default=REPO_DIR.parent, help="where version folders live (default: beside this install)")
    parser.add_argument("--expected-version", help="refuse a release that is not this version")
    parser.add_argument("--restart", action="store_true", help="start the newly installed version afterwards")
    parser.add_argument("--repair", action="store_true",
                        help="when this version is already installed, restore any missing or changed release file from the verified archive")
    args = parser.parse_args(argv)
    try:
        if args.latest:
            with tempfile.TemporaryDirectory() as temp:
                archive, tag = download_latest(Path(temp))
                print(f"downloaded {archive.name} ({tag})")
                result = install_archive(archive, args.install_root, expected_version=args.expected_version or tag,
                                         carry_from=REPO_DIR, repair=args.repair)
        else:
            result = install_archive(args.archive, args.install_root, expected_version=args.expected_version,
                                     carry_from=REPO_DIR, repair=args.repair)
    except ReleaseInstallError as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    if args.restart and result.get("folder"):
        os.execvp(launcher_for(Path(result["folder"]))[0], launcher_for(Path(result["folder"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
