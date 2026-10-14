"""Identity, receipt, and diagnostic record shapes.

These mirror the CourseCraft Workbench conventions on purpose
(`scripts/course_artifact_contracts.py`: `cc:<prefix>:<hash>` keys, identity
quality, relationship records, transport fingerprints, run receipts) so that a
later promotion upstream, or intake by a consumer such as the Catalog, is a
contract alignment and not a redesign. The functions are reimplemented here in
a few lines so this tool has no import-time dependency on the Workbench.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOL = "blueprint-packager"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def scoped_key(prefix: str, *parts: object, length: int = 32) -> str:
    """Same construction as the Workbench `_scoped_key`."""
    return f"cc:{prefix}:{canonical_sha256([str(part) for part in parts])[:length]}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def transport_fingerprint(path: Path) -> dict[str, Any]:
    return {"algorithm": "sha256", "digest": sha256_file(path), "scope": "transport_file",
            "bytes": path.stat().st_size, "extensions": {}}


def document_source(path: Path, lineage_basis: str, lineage_value: str) -> dict[str, Any]:
    """Source identity for a blueprint document (the Workbench builds the same block for exports)."""
    fingerprint = transport_fingerprint(path)
    return {
        "source_lineage_key": scoped_key("lineage", lineage_basis, lineage_value),
        "source_instance_key": f"cc:source:{fingerprint['digest']}",
        "lineage_state": "resolved",
        "lineage_basis": lineage_basis,
        "source_name": path.name,
        "transport_fingerprint": fingerprint,
        "extensions": {"source_kind": "flat_blueprint_document"},
    }


def entity_key(lineage_key: str, kind: str, title: str) -> str:
    return scoped_key("entity", lineage_key, kind, "title", title)


def entity_identity(lineage_key: str, kind: str, title: str, resource_code: str | None = None) -> dict[str, Any]:
    """Authored objects are identified by title until a resource code is minted for them."""
    aliases = [{"kind": "title", "value": title}]
    if resource_code:
        aliases.append({"kind": "resource_code", "value": resource_code})
    return {
        "entity_key": entity_key(lineage_key, kind, title),
        "identity": {"quality": "fallback", "basis": "title", "source_aliases": aliases,
                     "provenance": "authored"},
    }


def relationship(lineage_key: str, join_type: str, source: tuple[str, str], target: tuple[str, str] | None,
                 quality: str, evidence: str = "") -> dict[str, Any]:
    source_key = entity_key(lineage_key, *source)
    target_key = entity_key(lineage_key, *target) if target else None
    return {
        "join_type": join_type,
        "source_kind": source[0], "source_title": source[1], "source_entity_key": source_key,
        "target_kind": target[0] if target else None, "target_title": target[1] if target else None,
        "target_entity_key": target_key,
        "resolved": "yes" if target else "no",
        "relationship_key": scoped_key("relationship", source_key, join_type, target_key or ""),
        "identity": {"quality": quality},
        "evidence": evidence,
    }


def diagnostic(index: int, code: str, severity: str, message: str, location: str = "", remediation: str = "") -> dict[str, Any]:
    return {"id": f"diag-{index:04d}", "code": code, "severity": severity, "message": message,
            "location": location, "remediation": remediation, "extensions": {}}


def producer(repo_root: Path, version: str) -> dict[str, Any]:
    """Who built this: the release manifest when running from an installed release, this
    repository's git state when running from a checkout of it, otherwise unknown.

    A copy inside another repository (a release unpacked in a course build, an install
    under some checkout) must not report that repository's commit as its own."""
    extensions = {"host_repository": repo_root.name,
                  "status": "standalone producer repository since 2026-10-08; Workbench libraries vendored"}
    manifest_path = repo_root / "release_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = None
        if isinstance(manifest, dict) and manifest.get("commit"):
            build = manifest.get("build") if isinstance(manifest.get("build"), dict) else {}
            return {
                "component": TOOL, "identity_state": "release", "version": version,
                "repository": None, "ref": manifest.get("tag") or None, "commit": str(manifest["commit"]),
                "dirty": bool(build.get("dirty_worktree")),
                "extensions": {**extensions, "identity_source": "release_manifest.json",
                               "release_version": str(manifest.get("version") or ""),
                               "tag_verified": bool(build.get("tag_verified"))},
            }

    def git(*args: str) -> str:
        result = subprocess.run(["git", "-C", str(repo_root), *args], text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    toplevel = git("rev-parse", "--show-toplevel")
    own_repository = bool(toplevel) and Path(toplevel).resolve() == repo_root.resolve()
    commit = git("rev-parse", "HEAD") if own_repository else ""
    return {
        "component": TOOL, "identity_state": "git" if commit else "unknown", "version": version,
        "repository": None, "ref": (git("branch", "--show-current") or None) if commit else None, "commit": commit or None,
        "dirty": bool(git("status", "--porcelain")) if commit else None,
        "extensions": {**extensions,
                       "identity_source": "git" if commit else ("a repository that is not this tool's" if toplevel else "none")},
    }


def new_run_id() -> str:
    return f"cc:run:{uuid.uuid4()}"


def emitted_files(bundle_dir: Path, contract_by_name: dict[str, str], exclude: set[str]) -> list[dict[str, Any]]:
    import mimetypes

    out = []
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file() and not p.is_symlink()):
        relative = path.relative_to(bundle_dir).as_posix()
        if relative in exclude:
            continue
        out.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path),
                    "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                    "contract": contract_by_name.get(relative, contract_by_name.get(path.name)), "extensions": {}})
    return out


def run_receipt(*, run_id: str, source: dict[str, Any], bundle_dir: Path, receipt_name: str, started_at: str,
                steps: list[dict[str, Any]], parameters: dict[str, Any], contract_by_name: dict[str, str],
                diagnostics: list[Any], repo_root: Path, version: str) -> dict[str, Any]:
    status = "partial" if any(step.get("status") in {"failed", "unresolved"} for step in steps) else "ok"
    return {
        "schema": "blueprint_packager.run/0.1",
        "modeled_on": "coursecraft.run/1",
        "run_id": run_id, "status": status, "started_at": started_at, "finished_at": utc_now(),
        "source": source, "producer": producer(repo_root, version), "contracts": [],
        "parameters": parameters, "steps": steps,
        "emitted_files": emitted_files(bundle_dir, contract_by_name, {receipt_name}),
        "receipt_path": receipt_name, "diagnostics": diagnostics,
        "extensions": {"coursecraft.live_brightspace_operations": "not_performed"},
    }
