#!/usr/bin/env python3
"""CourseCraft Page Kit compiler and Brightspace HTML conformance helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from html import escape
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any
from urllib.parse import parse_qs, urlsplit
import uuid

from course_artifact_contracts import (
    build_run_identity,
    new_run_id,
    sha256_file,
    utc_now,
    validate_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STYLESHEET = (
    REPO_ROOT
    / "workspace"
    / "reference"
    / "templates"
    / "brightspace-course-pages"
    / "page-kit.css"
)
PAGE_KIT_SCRIPT = Path(__file__).resolve()
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_page.py"
CONFORMANCE_SCRIPT = REPO_ROOT / "scripts" / "check_page_conformance.py"
SUPPORTED_MODES = {"review", "learner"}
REVIEW_ONLY_KINDS = {"review_note", "review_questions"}
CREATOR_RUNTIME_TYPES = {
    "sorting_v1": 0,
    "sequencing_v1": 1,
    "quick_quiz_choice_v1": 5,
    "quick_quiz_multi_select_v1": 6,
    "fill_in_blank_text_v1": 7,
}
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}


class PageKitError(ValueError):
    """Refusal carrying structured diagnostics suitable for a CLI response."""

    def __init__(self, message: str, diagnostics: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = list(diagnostics or [])


class PublicationGateError(PageKitError):
    """Learner compilation refused because release blockers remain."""


@dataclass
class AssetContext:
    source: Path
    target: str
    role: str
    expected_sha256: str
    required: bool
    valid: bool


@dataclass
class ActivityContext:
    activity_id: int
    mode: str
    runtime_type: int
    json_path: str
    json_source: Path | None
    json_sha256: str
    wrapper_html: str | None
    wrapper_sha256: str
    provider_state: str
    structurally_valid: bool


@dataclass
class PageContext:
    source_path: Path
    page: dict[str, Any]
    blockers: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    assets: list[AssetContext] = field(default_factory=list)
    activities: dict[tuple[str, int], ActivityContext] = field(default_factory=dict)


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _diagnostic(
    severity: str,
    code: str,
    message: str,
    remediation: str,
    *,
    page_id: str | None = None,
    block_id: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": "",
        "severity": severity,
        "code": code,
        "page_id": page_id,
        "block_id": block_id,
        "message": message,
        "remediation": remediation,
        "extensions": dict(extensions or {}),
    }


def _blocker(
    code: str,
    message: str,
    remediation: str,
    *,
    page_id: str,
    block_id: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "page_id": page_id,
        "block_id": block_id,
        "message": message,
        "remediation": remediation,
        "extensions": dict(extensions or {}),
    }


def _number_diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    numbered = []
    for index, row in enumerate(rows, start=1):
        item = dict(row)
        item["id"] = f"diag-{index:04d}"
        numbered.append(item)
    return numbered


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PageKitError(
            f"Contract does not exist: {path}",
            [_diagnostic("error", "CONTRACT_MISSING", f"Contract does not exist: {path.name}", "Supply the declared contract file.")],
        ) from exc
    except json.JSONDecodeError as exc:
        raise PageKitError(
            f"Contract is not valid JSON: {path}",
            [_diagnostic("error", "MALFORMED_JSON", f"{path.name}: {exc}", "Correct the JSON syntax and run preflight again.")],
        ) from exc
    if not isinstance(payload, dict):
        raise PageKitError(
            f"Contract root must be an object: {path}",
            [_diagnostic("error", "INVALID_CONTRACT_ROOT", f"{path.name} must contain a JSON object.", "Replace the root value with the required object envelope.")],
        )
    return payload


def _validate_schema(payload: dict[str, Any], expected_schema: str, source_name: str) -> None:
    if payload.get("schema") != expected_schema:
        raise PageKitError(
            f"Unexpected schema in {source_name}",
            [_diagnostic("error", "WRONG_SCHEMA", f"{source_name} declares {payload.get('schema')!r}; expected {expected_schema!r}.", "Use the declared CourseCraft contract version.")],
        )
    issues = validate_contract(payload, mode="transform")
    errors = [
        _diagnostic("error", "SCHEMA_VALIDATION", issue.message, "Correct the contract field named by the validation message.")
        for issue in issues
        if issue.severity == "error"
    ]
    if errors:
        raise PageKitError(f"Schema validation failed for {source_name}", errors)


def safe_relative_path(value: str, *, label: str) -> str:
    text = str(value or "").replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PageKitError(
            f"Unsafe relative path for {label}: {value!r}",
            [_diagnostic("error", "UNSAFE_PATH", f"{label} is not a safe package-relative path: {value!r}", "Use a non-empty relative path without dot segments or traversal.")],
        )
    return path.as_posix()


def resolve_within(base: Path, relative: str, *, label: str) -> Path:
    normalized = safe_relative_path(relative, label=label)
    base_resolved = base.resolve()
    candidate = (base / normalized).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise PageKitError(
            f"Path escapes source root for {label}: {relative!r}",
            [_diagnostic("error", "PATH_ESCAPE", f"{label} escapes its source root: {relative!r}", "Keep sources and assets beneath the declared contract directory.")],
        ) from exc
    return candidate


def file_identity(path: Path, display_path: str | None = None) -> dict[str, Any]:
    return {
        "path": display_path or path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "extensions": {},
    }


def file_source_identity(path: Path, composition_id: str) -> dict[str, Any]:
    digest = sha256_file(path)
    lineage_digest = hashlib.sha256(f"module-composition:{composition_id}".encode("utf-8")).hexdigest()
    return {
        "source_lineage_key": f"cc:lineage:{lineage_digest[:32]}",
        "source_instance_key": f"cc:source:{digest}",
        "lineage_state": "resolved",
        "lineage_basis": "composition_id",
        "source_name": path.name,
        "logical_fingerprint": {
            "algorithm": "sha256",
            "digest": digest,
            "scope": "page_composition_contract",
            "file_count": 1,
            "bytes": path.stat().st_size,
            "extensions": {},
        },
        "transport_fingerprint": None,
        "observed_identity": {"composition_id": composition_id},
        "extensions": {},
    }


def provider_state(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "missing"
    if text.startswith("REPLACE_WITH_"):
        return "placeholder"
    if text.lower().startswith(("http://", "https://")):
        return "provider_backed"
    return "unknown"


class _CreatorWrapperInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.practice_hrefs: list[str] = []
        self.iframes: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {(name or "").casefold(): value or "" for name, value in attrs}
        classes = set(attr_map.get("class", "").split())
        if tag.casefold() == "div" and "d2l-practice" in classes:
            self.practice_hrefs.append(attr_map.get("data-d2l-activity-href", ""))
        if tag.casefold() == "iframe":
            self.iframes.append(attr_map)


def inspect_creator_wrapper(
    wrapper_html: str,
    activity: dict[str, Any],
    *,
    page_id: str,
    block_id: str,
) -> tuple[list[dict[str, Any]], str]:
    errors: list[dict[str, Any]] = []
    inspector = _CreatorWrapperInspector()
    inspector.feed(wrapper_html)
    inspector.close()
    activity_id = activity["activity_id"]

    def add(code: str, message: str, remediation: str) -> None:
        errors.append(_blocker(code, message, remediation, page_id=page_id, block_id=block_id, extensions={"activity_id": activity_id}))

    if len(inspector.practice_hrefs) != 1:
        add("CREATORPLUS_WRAPPER_SHAPE", f"Creator+ activity {activity_id} must contain exactly one d2l-practice wrapper.", "Regenerate the wrapper with the evidence-backed Creator+ generator.")
    if len(inspector.iframes) != 1:
        add("CREATORPLUS_IFRAME_SHAPE", f"Creator+ activity {activity_id} must contain exactly one iframe.", "Regenerate the wrapper with one activity iframe.")
        return errors, provider_state(activity.get("provider_href", ""))

    iframe = inspector.iframes[0]
    if iframe.get("id") != str(activity_id):
        add("CREATORPLUS_ID_MISMATCH", f"Creator+ wrapper iframe id {iframe.get('id')!r} does not match activity id {activity_id}.", "Regenerate the wrapper so the contract, iframe, and JSON ids match.")
    if iframe.get("data-file") != activity["json_path"]:
        add("CREATORPLUS_DATA_FILE_MISMATCH", f"Creator+ activity {activity_id} points to {iframe.get('data-file')!r}, not {activity['json_path']!r}.", "Point the preserved wrapper to the declared package-local JSON path.")
    query = parse_qs(urlsplit(iframe.get("src", "").replace("&amp;", "&")).query)
    if query.get("id", [""])[0] != str(activity_id):
        add("CREATORPLUS_QUERY_ID_MISMATCH", f"Creator+ activity {activity_id} has a mismatched iframe query id.", "Regenerate the wrapper so both iframe id locations match the JSON id.")
    if query.get("t", [""])[0] != str(activity["runtime_type"]):
        add("CREATORPLUS_RUNTIME_TYPE_MISMATCH", f"Creator+ activity {activity_id} wrapper runtime type does not match {activity['runtime_type']}.", "Regenerate the wrapper from the admitted Creator+ mode.")
    wrapper_href = inspector.practice_hrefs[0] if inspector.practice_hrefs else ""
    if wrapper_href != activity.get("provider_href", ""):
        add("CREATORPLUS_PROVIDER_HREF_MISMATCH", f"Creator+ activity {activity_id} wrapper provider href differs from the page contract.", "Refresh the observed provider href from the preserved wrapper.")
    return errors, provider_state(wrapper_href)


class _HTMLConformanceInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[int] = []
        self.ids: list[str] = []
        self.images_without_alt: list[str] = []
        self.iframes_without_title: list[str] = []
        self.creatorplus_iframes_without_title: list[str] = []
        self.links_without_href = 0
        self.event_attributes: list[str] = []
        self.javascript_urls: list[str] = []
        self.dangerous_tags: list[str] = []
        self.details_count = 0
        self.summary_count = 0
        self.review_markers: list[str] = []
        self.raw_html_markers = 0
        self.external_links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attr_map = {(name or "").casefold(): value or "" for name, value in attrs}
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if attr_map.get("id"):
            self.ids.append(attr_map["id"])
        if tag == "img" and "alt" not in attr_map:
            self.images_without_alt.append(attr_map.get("src", ""))
        if tag == "iframe" and not attr_map.get("title", "").strip():
            target = attr_map.get("src", "")
            if attr_map.get("data-file", "").strip():
                self.creatorplus_iframes_without_title.append(target)
            else:
                self.iframes_without_title.append(target)
        if tag == "a" and not attr_map.get("href", "").strip():
            self.links_without_href += 1
        if tag in {"script", "form", "object", "embed"}:
            self.dangerous_tags.append(tag)
        if tag == "details":
            self.details_count += 1
        if tag == "summary":
            self.summary_count += 1
        classes = set(attr_map.get("class", "").split())
        for marker in {"cc-review-status", "cc-review-note", "cc-review-questions", "cc-review-meta"} & classes:
            self.review_markers.append(marker)
        if attr_map.get("data-cc-raw-html") == "true":
            self.raw_html_markers += 1
        for name, value in attr_map.items():
            if name.startswith("on"):
                self.event_attributes.append(name)
            if name in {"href", "src", "action", "formaction"}:
                scheme = urlsplit(value).scheme.casefold()
                if scheme == "javascript":
                    self.javascript_urls.append(value)
                if scheme in EXTERNAL_SCHEMES:
                    self.external_links.add(value)


def check_html_conformance(raw: str, *, mode: str, page_id: str | None = None) -> list[dict[str, Any]]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported page mode: {mode}")
    inspector = _HTMLConformanceInspector()
    inspector.feed(raw)
    inspector.close()
    rows: list[dict[str, Any]] = []

    def add(severity: str, code: str, message: str, remediation: str) -> None:
        rows.append(_diagnostic(severity, code, message, remediation, page_id=page_id))

    if inspector.headings.count(1) != 1:
        add("error", "H1_COUNT", f"Page must contain exactly one h1; found {inspector.headings.count(1)}.", "Keep one page title as h1 and use h2/h3 for content structure.")
    for previous, current in zip(inspector.headings, inspector.headings[1:]):
        if current > previous + 1:
            add("warning", "HEADING_LEVEL_JUMP", f"Heading hierarchy jumps from h{previous} to h{current}.", "Use the next sequential heading level where the structure is hierarchical.")
    duplicate_ids = sorted({value for value in inspector.ids if inspector.ids.count(value) > 1})
    if duplicate_ids:
        add("error", "DUPLICATE_HTML_ID", f"Duplicate HTML id values: {', '.join(duplicate_ids)}.", "Mint a unique id for each element, including Creator+ iframes.")
    if inspector.images_without_alt:
        add("error", "IMAGE_ALT_MISSING", f"{len(inspector.images_without_alt)} image(s) omit the alt attribute.", "Add meaningful alt text or an explicit empty alt attribute for decorative images.")
    if inspector.iframes_without_title:
        add("error", "IFRAME_TITLE_MISSING", f"{len(inspector.iframes_without_title)} iframe(s) omit a title.", "Add a concise iframe title describing the embedded content.")
    if inspector.creatorplus_iframes_without_title:
        add("warning", "CREATORPLUS_IFRAME_TITLE_UNCONFIRMED", f"{len(inspector.creatorplus_iframes_without_title)} preserved Creator+ iframe(s) omit a title.", "Confirm the tenant-supported wrapper shape and accessible name before promotion; do not mutate an evidence-backed wrapper silently.")
    if inspector.links_without_href:
        add("error", "LINK_HREF_MISSING", f"{inspector.links_without_href} anchor(s) omit href.", "Provide a valid link target or use a non-link element.")
    if inspector.dangerous_tags:
        add("error", "UNSAFE_HTML_TAG", f"Disallowed HTML tags found: {', '.join(sorted(set(inspector.dangerous_tags)))}.", "Remove active-form or script content from packaged lesson pages.")
    if inspector.event_attributes:
        add("error", "INLINE_EVENT_HANDLER", f"Inline event attributes found: {', '.join(sorted(set(inspector.event_attributes)))}.", "Use semantic HTML and supported platform behavior without inline event handlers.")
    if inspector.javascript_urls:
        add("error", "JAVASCRIPT_URL", "A javascript: URL appears in the page.", "Replace it with a safe package-local or HTTPS target.")
    if inspector.details_count != inspector.summary_count:
        add("error", "DISCLOSURE_SUMMARY_MISMATCH", f"Found {inspector.details_count} details element(s) and {inspector.summary_count} summary element(s).", "Give every details disclosure exactly one summary label.")
    if mode == "learner" and inspector.review_markers:
        add("error", "REVIEW_CONTENT_LEAK", "Reviewer-only component markers remain in learner HTML.", "Compile learner output from the page source instead of manually deleting review boxes.")
    if mode == "learner" and "REPLACE_WITH_" in raw:
        add("error", "PLACEHOLDER_LEAK", "An unresolved REPLACE_WITH_ placeholder remains in learner HTML.", "Resolve the dependency before compiling learner output.")
    if inspector.raw_html_markers:
        add("warning", "DECLARED_RAW_HTML", f"Page contains {inspector.raw_html_markers} declared raw-HTML block(s).", "Review the bespoke markup and promote recurring patterns into typed blocks.")
    return rows


def external_links(raw: str) -> list[str]:
    inspector = _HTMLConformanceInspector()
    inspector.feed(raw)
    inspector.close()
    return sorted(inspector.external_links)


def _page_type_map(kit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    duplicates = []
    for row in kit["page_types"]:
        page_type = row["page_type"]
        if page_type in mapping:
            duplicates.append(page_type)
        mapping[page_type] = row
    if duplicates:
        raise PageKitError(
            "Page Kit contains duplicate page types.",
            [_diagnostic("error", "DUPLICATE_PAGE_TYPE", f"Duplicate page types: {', '.join(sorted(set(duplicates)))}.", "Declare each page type once in the Page Kit.")],
        )
    return mapping


def _inspect_declared_asset(
    row: dict[str, Any],
    *,
    source_root: Path,
    page_id: str,
) -> tuple[AssetContext, list[dict[str, Any]], list[dict[str, Any]]]:
    diagnostics: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    source = resolve_within(source_root, row["source"], label=f"{page_id} support asset source")
    target = safe_relative_path(row["target"], label=f"{page_id} support asset target")
    required = bool(row["required_for_publication"])
    valid = source.is_file()
    if not valid:
        message = f"Support asset {row['source']!r} does not exist for page {page_id}."
        if required:
            blockers.append(_blocker("MISSING_REQUIRED_ASSET", message, "Supply the declared source asset or remove the required dependency.", page_id=page_id, extensions={"target": target, "role": row["role"]}))
        else:
            diagnostics.append(_diagnostic("warning", "OPTIONAL_ASSET_MISSING", message, "Supply the optional asset or remove its declaration.", page_id=page_id, extensions={"target": target, "role": row["role"]}))
    elif sha256_file(source) != row["sha256"]:
        valid = False
        message = f"Support asset checksum drifted for {row['source']!r}."
        if required:
            blockers.append(_blocker("SUPPORT_ASSET_HASH_DRIFT", message, "Review the changed asset and refresh its declared SHA-256 intentionally.", page_id=page_id, extensions={"target": target, "role": row["role"]}))
        else:
            diagnostics.append(_diagnostic("warning", "OPTIONAL_ASSET_HASH_DRIFT", message, "Review the changed optional asset and refresh or remove its declaration.", page_id=page_id, extensions={"target": target, "role": row["role"]}))
    return AssetContext(source, target, row["role"], row["sha256"], required, valid), blockers, diagnostics


def _inspect_activity(
    activity: dict[str, Any],
    *,
    source_root: Path,
    kit: dict[str, Any],
    page_id: str,
    block_id: str,
) -> tuple[ActivityContext, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    activity_id = activity["activity_id"]
    required = bool(activity["required_for_publication"])
    mode = activity["mode"]
    expected_runtime = CREATOR_RUNTIME_TYPES.get(mode)
    if mode not in set(kit["supported_creatorplus_modes"]):
        errors.append(_diagnostic("error", "UNSUPPORTED_CREATORPLUS_MODE", f"Creator+ mode {mode!r} is not admitted by kit {kit['kit_id']}.", "Use one of the Page Kit's evidence-backed modes.", page_id=page_id, block_id=block_id, extensions={"activity_id": activity_id}))
    if expected_runtime is None or activity["runtime_type"] != expected_runtime:
        errors.append(_diagnostic("error", "CREATORPLUS_MODE_RUNTIME_MISMATCH", f"Creator+ mode {mode!r} requires runtime type {expected_runtime!r}, not {activity['runtime_type']!r}.", "Regenerate the wrapper and page reference from the admitted mode.", page_id=page_id, block_id=block_id, extensions={"activity_id": activity_id}))

    json_path_parts = Path(activity["json_path"]).parts
    if not (
        len(json_path_parts) == 2
        and json_path_parts[0].casefold() == "practice"
        and json_path_parts[1].casefold().endswith(".practice.json")
    ):
        errors.append(
            _diagnostic(
                "error",
                "CREATORPLUS_ROOT_PATH_REQUIRED",
                f"Creator+ activity {activity_id} targets {activity['json_path']!r}, not a direct child of package-root practice/.",
                "Retain the observed physical filename and set json_path to practice/<observed-filename>.practice.json.",
                page_id=page_id,
                block_id=block_id,
                extensions={"activity_id": activity_id},
            )
        )

    json_source = resolve_within(source_root, activity["json_source"], label=f"Creator+ activity {activity_id} JSON")
    wrapper_source = resolve_within(source_root, activity["wrapper_source"], label=f"Creator+ activity {activity_id} wrapper")
    valid = True
    wrapper_html: str | None = None

    def lifecycle_issue(code: str, message: str, remediation: str) -> None:
        nonlocal valid
        valid = False
        extensions = {"activity_id": activity_id}
        if required:
            blockers.append(_blocker(code, message, remediation, page_id=page_id, block_id=block_id, extensions=extensions))
        else:
            diagnostics.append(_diagnostic("warning", code, message, remediation, page_id=page_id, block_id=block_id, extensions=extensions))

    if not json_source.is_file():
        lifecycle_issue("CREATORPLUS_JSON_MISSING", f"Creator+ JSON is missing for activity {activity_id}: {activity['json_source']}", "Generate or restore the declared practice JSON file.")
    elif sha256_file(json_source) != activity["json_sha256"]:
        lifecycle_issue("CREATORPLUS_JSON_HASH_DRIFT", f"Creator+ JSON checksum drifted for activity {activity_id}.", "Review the changed practice payload and refresh its declared SHA-256 intentionally.")
    else:
        try:
            payload = json.loads(json_source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            lifecycle_issue("CREATORPLUS_JSON_INVALID", f"Creator+ JSON is unreadable for activity {activity_id}: {exc}", "Regenerate a valid practice JSON payload.")
        else:
            if payload.get("id") != activity_id:
                lifecycle_issue("CREATORPLUS_JSON_ID_MISMATCH", f"Creator+ JSON id {payload.get('id')!r} does not match activity id {activity_id}.", "Regenerate the payload so the contract, JSON, and wrapper share one id.")

    derived_provider_state = provider_state(activity.get("provider_href", ""))
    if not wrapper_source.is_file():
        lifecycle_issue("CREATORPLUS_WRAPPER_MISSING", f"Creator+ wrapper is missing for activity {activity_id}: {activity['wrapper_source']}", "Regenerate or restore the preserved wrapper snippet.")
    elif sha256_file(wrapper_source) != activity["wrapper_sha256"]:
        lifecycle_issue("CREATORPLUS_WRAPPER_HASH_DRIFT", f"Creator+ wrapper checksum drifted for activity {activity_id}.", "Review the changed wrapper and refresh its declared SHA-256 intentionally.")
    else:
        wrapper_html = wrapper_source.read_text(encoding="utf-8").strip()
        wrapper_blockers, derived_provider_state = inspect_creator_wrapper(
            wrapper_html,
            activity,
            page_id=page_id,
            block_id=block_id,
        )
        if wrapper_blockers:
            valid = False
            if required:
                blockers.extend(wrapper_blockers)
            else:
                diagnostics.extend(
                    _diagnostic("warning", row["code"], row["message"], row["remediation"], page_id=page_id, block_id=block_id, extensions=row["extensions"])
                    for row in wrapper_blockers
                )

    provider_policy = kit["lifecycle"]["creatorplus_provider_policy"]
    if required and provider_policy == "provider_backed_required" and derived_provider_state != "provider_backed":
        blockers.append(_blocker("CREATORPLUS_PROVIDER_UNRESOLVED", f"Creator+ activity {activity_id} provider href state is {derived_provider_state!r}.", "Insert or refresh the activity in Brightspace and record its provider-backed href before learner release.", page_id=page_id, block_id=block_id, extensions={"activity_id": activity_id, "observed_state": derived_provider_state}))

    context = ActivityContext(
        activity_id=activity_id,
        mode=mode,
        runtime_type=activity["runtime_type"],
        json_path=activity["json_path"],
        json_source=json_source if json_source.is_file() else None,
        json_sha256=activity["json_sha256"],
        wrapper_html=wrapper_html,
        wrapper_sha256=activity["wrapper_sha256"],
        provider_state=derived_provider_state,
        structurally_valid=valid,
    )
    return context, errors, blockers, diagnostics


def preflight(
    kit_path: Path,
    composition_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[PageContext], list[dict[str, Any]]]:
    kit_path = kit_path.resolve()
    composition_path = composition_path.resolve()
    kit = _read_json(kit_path)
    composition = _read_json(composition_path)
    _validate_schema(kit, "coursecraft.page_kit/1", kit_path.name)
    _validate_schema(composition, "coursecraft.module_composition/1", composition_path.name)
    type_map = _page_type_map(kit)
    supported_blocks = set(kit["supported_block_kinds"])
    blocking_states = set(kit["lifecycle"]["blocking_review_states"])
    source_root = composition_path.parent
    errors: list[dict[str, Any]] = []
    contexts: list[PageContext] = []
    item_ids: set[str] = set()
    page_ids: set[str] = set()
    filenames: set[str] = set()
    output_targets: dict[str, str] = {}

    for item in composition["module"]["items"]:
        item_id = item["item_id"]
        if item_id in item_ids:
            errors.append(_diagnostic("error", "DUPLICATE_COMPOSITION_ITEM", f"Duplicate composition item id: {item_id}.", "Mint a unique item id for every module placement."))
        item_ids.add(item_id)
        if item["type"] != "page":
            continue
        page_source = resolve_within(source_root, item["source"], label=f"composition page source {item_id}")
        page = _read_json(page_source)
        _validate_schema(page, "coursecraft.page/1", page_source.name)
        page_id = page["page_id"]
        context = PageContext(page_source, page)
        contexts.append(context)
        if page_id != item["page_id"]:
            errors.append(_diagnostic("error", "PAGE_REFERENCE_MISMATCH", f"Composition item {item_id} names page {item['page_id']!r}, but {page_source.name} declares {page_id!r}.", "Make the composition reference and page contract identity match.", page_id=page_id))
        if page_id in page_ids:
            errors.append(_diagnostic("error", "DUPLICATE_PAGE_ID", f"Duplicate page id: {page_id}.", "Mint a unique page id within the composition.", page_id=page_id))
        page_ids.add(page_id)
        if page["filename"] in filenames:
            errors.append(_diagnostic("error", "DUPLICATE_PAGE_FILENAME", f"Duplicate page filename: {page['filename']}.", "Use a unique package-relative HTML filename.", page_id=page_id))
        filenames.add(page["filename"])
        output_targets[page["filename"]] = f"page:{page_id}"
        if page["kit_id"] != kit["kit_id"]:
            errors.append(_diagnostic("error", "KIT_ID_MISMATCH", f"Page {page_id} names kit {page['kit_id']!r}, not {kit['kit_id']!r}.", "Compile the page with its declared kit or update the page through review.", page_id=page_id))
        page_type = type_map.get(page["page_type"])
        if page_type is None:
            errors.append(_diagnostic("error", "UNKNOWN_PAGE_TYPE", f"Page {page_id} uses unknown page type {page['page_type']!r}.", "Use a page type declared by the Page Kit.", page_id=page_id))
            allowed_blocks: set[str] = set()
            required_slots: set[str] = set()
        else:
            allowed_blocks = set(page_type["allowed_blocks"])
            required_slots = set(page_type["required_slots"])
        slot_ids = [slot["slot_id"] for slot in page["slots"]]
        duplicate_slots = sorted({value for value in slot_ids if slot_ids.count(value) > 1})
        if duplicate_slots:
            errors.append(_diagnostic("error", "DUPLICATE_SLOT_ID", f"Page {page_id} repeats slot ids: {', '.join(duplicate_slots)}.", "Declare each page slot once.", page_id=page_id))
        missing_slots = sorted(required_slots - set(slot_ids))
        if missing_slots:
            errors.append(_diagnostic("error", "REQUIRED_SLOT_MISSING", f"Page {page_id} is missing required slots: {', '.join(missing_slots)}.", "Fill every required slot for the selected page type.", page_id=page_id))
        if page["review_state"] in blocking_states:
            context.blockers.append(_blocker("PAGE_REVIEW_OPEN", f"Page {page_id} review state is {page['review_state']!r}.", "Approve the page or explicitly mark review as not required before learner release.", page_id=page_id))

        block_ids: set[str] = set()
        for slot in page["slots"]:
            for block in slot["blocks"]:
                block_id = block["block_id"]
                if block_id in block_ids:
                    errors.append(_diagnostic("error", "DUPLICATE_BLOCK_ID", f"Page {page_id} repeats block id {block_id!r}.", "Mint a unique block id within the page.", page_id=page_id, block_id=block_id))
                block_ids.add(block_id)
                if block["kind"] not in supported_blocks or block["kind"] not in allowed_blocks:
                    errors.append(_diagnostic("error", "BLOCK_NOT_ADMITTED", f"Block {page_id}/{block_id} uses {block['kind']!r}, which is not admitted for page type {page['page_type']!r}.", "Use an allowed typed block or revise the Page Kit through review.", page_id=page_id, block_id=block_id))
                if block["origin"] != "generated" and not block["source_refs"]:
                    errors.append(_diagnostic("error", "SOURCE_REFERENCE_MISSING", f"Block {page_id}/{block_id} is {block['origin']!r} but has no source reference.", "Add at least one durable source reference or mark genuinely generated content accurately.", page_id=page_id, block_id=block_id))
                if block["review_state"] in blocking_states:
                    context.blockers.append(_blocker("BLOCK_REVIEW_OPEN", f"Block {page_id}/{block_id} review state is {block['review_state']!r}.", "Resolve or approve the block before learner release.", page_id=page_id, block_id=block_id))
                if block["kind"] == "video" and block["required_for_publication"] and not block.get("embed_url"):
                    context.blockers.append(_blocker("REQUIRED_VIDEO_UNRESOLVED", f"Required video embed is unresolved for {page_id}/{block_id}.", "Supply and review the final embed URL before learner release.", page_id=page_id, block_id=block_id))
                if block["kind"] == "raw_html":
                    raw_policy = kit["lifecycle"]["raw_html_policy"]
                    if raw_policy == "block":
                        context.blockers.append(_blocker("RAW_HTML_BLOCKED", f"Raw HTML block {page_id}/{block_id} is blocked by the Page Kit.", "Replace the bespoke markup with typed blocks or revise the kit policy through review.", page_id=page_id, block_id=block_id))
                    elif raw_policy == "warn":
                        context.diagnostics.append(_diagnostic("warning", "RAW_HTML_REVIEW_REQUIRED", f"Raw HTML block {page_id}/{block_id} uses the declared escape hatch.", "Review the bespoke markup and promote recurring patterns into typed blocks.", page_id=page_id, block_id=block_id))
                if block["kind"] == "creatorplus_group":
                    activity_ids: set[int] = set()
                    for activity in block["activities"]:
                        activity_id = activity["activity_id"]
                        if activity_id in activity_ids:
                            errors.append(_diagnostic("error", "DUPLICATE_CREATORPLUS_ID", f"Block {page_id}/{block_id} repeats Creator+ activity id {activity_id}.", "Use one unique activity id per practice wrapper.", page_id=page_id, block_id=block_id))
                        activity_ids.add(activity_id)
                        activity_context, activity_errors, activity_blockers, activity_diagnostics = _inspect_activity(
                            activity,
                            source_root=source_root,
                            kit=kit,
                            page_id=page_id,
                            block_id=block_id,
                        )
                        context.activities[(block_id, activity_id)] = activity_context
                        errors.extend(activity_errors)
                        context.blockers.extend(activity_blockers)
                        context.diagnostics.extend(activity_diagnostics)

        for asset in page["support_assets"]:
            asset_context, asset_blockers, asset_diagnostics = _inspect_declared_asset(asset, source_root=source_root, page_id=page_id)
            context.assets.append(asset_context)
            context.blockers.extend(asset_blockers)
            context.diagnostics.extend(asset_diagnostics)

        for target, role in [
            *((asset.target, f"asset:{page_id}:{asset.role}") for asset in context.assets),
            *((activity.json_path, f"creatorplus:{page_id}:{activity.activity_id}") for activity in context.activities.values()),
        ]:
            prior = output_targets.get(target)
            if prior and prior != role:
                errors.append(_diagnostic("error", "OUTPUT_PATH_COLLISION", f"Output path {target!r} is claimed by both {prior} and {role}.", "Give every page and support artifact a unique target path.", page_id=page_id))
            output_targets[target] = role

    if not contexts:
        errors.append(_diagnostic("error", "NO_PAGE_ITEMS", "The module composition contains no page items.", "Add at least one page source to compile."))
    if errors:
        raise PageKitError("Page Kit preflight failed.", _number_diagnostics(errors))
    return kit, composition, contexts, _number_diagnostics([row for context in contexts for row in context.diagnostics])


def _theme_style(kit: dict[str, Any]) -> str:
    tokens = kit["theme"]["tokens"]
    return "; ".join(f"--cc-{name.replace('_', '-')}: {value}" for name, value in tokens.items())


def _review_meta(block: dict[str, Any]) -> str:
    refs = ", ".join(escape(value) for value in block["source_refs"]) or "none"
    return (
        '<p class="cc-review-meta"><strong>Origin:</strong> '
        f"{escape(block['origin'].replace('_', ' '))} · <strong>Review:</strong> "
        f"{escape(block['review_state'].replace('_', ' '))} · <strong>Sources:</strong> {refs}</p>"
    )


def _render_block(
    block: dict[str, Any],
    *,
    page_id: str,
    mode: str,
    activity_contexts: dict[tuple[str, int], ActivityContext],
) -> str:
    kind = block["kind"]
    block_id = escape(block["block_id"], quote=True)
    if mode == "learner" and kind in REVIEW_ONLY_KINDS:
        return ""
    review_meta = _review_meta(block) if mode == "review" and kind not in REVIEW_ONLY_KINDS else ""
    attrs = f'id="{escape(page_id, quote=True)}--{block_id}" class="cc-block cc-{kind.replace("_", "-")}"'

    if kind == "prose":
        body = block["block_html"]
    elif kind == "outcomes":
        items = "".join(f"<li>{value}</li>" for value in block["items_html"])
        body = f"<h2>{escape(block['heading'])}</h2><ul>{items}</ul>"
    elif kind == "video":
        links = "".join(f'<li><a href="{escape(link["url"], quote=True)}">{escape(link["label"])}</a></li>' for link in block["links"])
        if block.get("embed_url"):
            media = (
                '<div class="cc-video-shell"><iframe '
                f'src="{escape(block["embed_url"], quote=True)}" title="{escape(block["iframe_title"], quote=True)}" '
                'loading="lazy" allowfullscreen></iframe></div>'
            )
        else:
            media = '<div class="cc-unresolved" role="note">Required video embed is unresolved.</div>'
        body = f"<h2>{escape(block['heading'])}</h2>{media}{f'<ul>{links}</ul>' if links else ''}"
    elif kind == "disclosure":
        body = f"<details><summary>{escape(block['summary_text'])}</summary><div class=\"cc-details-body\">{block['block_html']}</div></details>"
    elif kind == "route_list":
        items = "".join(f'<li><strong>{escape(item["label"])}</strong><div>{item["block_html"]}</div></li>' for item in block["route_items"])
        body = f"<h2>{escape(block['heading'])}</h2><ol class=\"cc-route-list\">{items}</ol>"
    elif kind == "resources":
        items = "".join(
            '<li>'
            f'<h3><a href="{escape(item["url"], quote=True)}">{escape(item["title"])}</a></h3>'
            f'<div>{item["description_html"]}</div>'
            f'<div class="cc-resource-note">{item.get("note_html", "")}</div>'
            '</li>'
            for item in block["resource_items"]
        )
        body = f"<h2>{escape(block['heading'])}</h2><ul class=\"cc-resource-list\">{items}</ul>"
    elif kind == "creatorplus_group":
        activities = []
        for activity in block["activities"]:
            context = activity_contexts[(block["block_id"], activity["activity_id"])]
            if context.structurally_valid and context.wrapper_html:
                activities.append(f'<div class="cc-practice-shell">{context.wrapper_html}</div>')
            elif mode == "review":
                activities.append(f'<div class="cc-unresolved" role="note">Creator+ activity {context.activity_id} is not structurally ready.</div>')
        body = f"<h2>{escape(block['heading'])}</h2>{''.join(activities)}"
    elif kind == "callout":
        body = f'<aside class="cc-callout cc-callout--{escape(block["callout_variant"], quote=True)}">{block["block_html"]}</aside>'
    elif kind == "review_note":
        return f'<aside id="{escape(page_id, quote=True)}--{block_id}" class="cc-review-note"><strong>{escape(block["label"])}</strong>{block["block_html"]}</aside>'
    elif kind == "review_questions":
        items = "".join(f"<li>{value}</li>" for value in block["items_html"])
        return f'<aside id="{escape(page_id, quote=True)}--{block_id}" class="cc-review-questions"><h2>{escape(block["heading"])}</h2><ol>{items}</ol></aside>'
    elif kind == "raw_html":
        body = f'<div data-cc-raw-html="true">{block["raw_html"]}</div>'
    else:  # protected by schema and Page Kit admission checks
        raise AssertionError(f"Unhandled block kind: {kind}")
    return f"<section {attrs}>{review_meta}{body}</section>"


def render_page(
    kit: dict[str, Any],
    context: PageContext,
    *,
    mode: str,
    css: str,
    kit_sha256: str,
    page_sha256: str,
) -> str:
    page = context.page
    page_blockers = [row for row in context.blockers if row["page_id"] == page["page_id"]]
    review_status = ""
    if mode == "review":
        blocker_items = "".join(f"<li>{escape(row['message'])}</li>" for row in page_blockers)
        review_status = (
            '<aside class="cc-review-status" aria-label="Page review status">'
            f"<strong>Review build · {len(page_blockers)} release blocker(s)</strong>"
            f"{f'<ul>{blocker_items}</ul>' if blocker_items else '<p>No release blockers are currently recorded.</p>'}"
            "</aside>"
        )
    blocks = []
    for slot in page["slots"]:
        rendered = "".join(
            _render_block(
                block,
                page_id=page["page_id"],
                mode=mode,
                activity_contexts=context.activities,
            )
            for block in slot["blocks"]
        )
        if rendered:
            blocks.append(f'<div class="cc-slot" data-cc-slot="{escape(slot["slot_id"], quote=True)}">{rendered}</div>')
    generated_comment = (
        "<!-- Generated by CourseCraft Page Kit; "
        f"schema=coursecraft.page/1; page={page['page_id']}; mode={mode}; "
        f"source_sha256={page_sha256}; kit_sha256={kit_sha256}. -->"
    )
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(page['title'])}</title>",
            f"<style>\n{css.rstrip()}\n</style>",
            "</head>",
            "<body>",
            generated_comment,
            '<a class="cc-skip-link" href="#cc-main">Skip to main content</a>',
            f'<main id="cc-main" class="cc-page" data-cc-mode="{mode}" style="{escape(_theme_style(kit), quote=True)}">',
            '<header class="cc-page-header">',
            f'<p class="cc-eyebrow">{escape(page["eyebrow"])}</p>',
            f"<h1>{escape(page['title'])}</h1>",
            f'<p class="cc-lede">{escape(page["lede"])}</p>',
            review_status,
            "</header>",
            '<div class="cc-page-body">',
            *blocks,
            "</div>",
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _copy_asset(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _replace_output(temp_root: Path, output_dir: Path, *, force: bool) -> None:
    if output_dir.exists() and not force:
        raise PageKitError(
            f"Output directory already exists: {output_dir}",
            [_diagnostic("error", "OUTPUT_EXISTS", f"Output directory already exists: {output_dir.name}", "Choose a fresh output directory or use --force for transactional replacement.")],
        )
    backup: Path | None = None
    try:
        if output_dir.exists():
            backup = output_dir.with_name(f".{output_dir.name}.backup-{uuid.uuid4().hex}")
            output_dir.rename(backup)
        temp_root.rename(output_dir)
    except Exception:
        if backup is not None and backup.exists() and not output_dir.exists():
            backup.rename(output_dir)
        raise
    else:
        if backup is not None:
            shutil.rmtree(backup)


def build_pages(
    *,
    kit_path: Path,
    composition_path: Path,
    output_dir: Path,
    mode: str,
    stylesheet_path: Path = DEFAULT_STYLESHEET,
    force: bool = False,
) -> dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        raise PageKitError(
            f"Unsupported mode: {mode}",
            [_diagnostic("error", "UNSUPPORTED_MODE", f"Mode must be review or learner, not {mode!r}.", "Choose one of the two lifecycle outputs.")],
        )
    kit_path = kit_path.resolve()
    composition_path = composition_path.resolve()
    stylesheet_path = stylesheet_path.resolve()
    output_dir = output_dir.resolve()
    if not stylesheet_path.is_file():
        raise PageKitError(
            f"Stylesheet does not exist: {stylesheet_path}",
            [_diagnostic("error", "STYLESHEET_MISSING", f"Stylesheet does not exist: {stylesheet_path.name}", "Supply the canonical Page Kit stylesheet.")],
        )
    kit, composition, contexts, preflight_diagnostics = preflight(kit_path, composition_path)
    blockers = [row for context in contexts for row in context.blockers]
    if mode == "learner" and blockers:
        raise PublicationGateError("Learner publication gate failed.", blockers)
    if output_dir.exists() and not force:
        raise PageKitError(
            f"Output directory already exists: {output_dir}",
            [_diagnostic("error", "OUTPUT_EXISTS", f"Output directory already exists: {output_dir.name}", "Choose a fresh output directory or use --force for transactional replacement.")],
        )

    css = stylesheet_path.read_text(encoding="utf-8")
    kit_sha = sha256_file(kit_path)
    composition_sha = sha256_file(composition_path)
    run_id = new_run_id()
    started_at = utc_now()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.build-", dir=output_dir.parent))
    page_receipts: list[dict[str, Any]] = []
    conformance_rows: list[dict[str, Any]] = []
    try:
        copied_targets: dict[str, str] = {}
        for context in contexts:
            page = context.page
            page_sha = sha256_file(context.source_path)
            raw = render_page(kit, context, mode=mode, css=css, kit_sha256=kit_sha, page_sha256=page_sha)
            page_diagnostics = check_html_conformance(raw, mode=mode, page_id=page["page_id"])
            conformance_rows.extend(page_diagnostics)
            target = temp_root / safe_relative_path(page["filename"], label=f"page {page['page_id']} filename")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(raw, encoding="utf-8")
            support_receipts: list[dict[str, Any]] = []

            for asset in context.assets:
                if not asset.valid:
                    continue
                actual = sha256_file(asset.source)
                prior = copied_targets.get(asset.target)
                if prior and prior != actual:
                    raise PageKitError(
                        "Support asset target collision during build.",
                        [_diagnostic("error", "OUTPUT_HASH_COLLISION", f"Output target {asset.target!r} has two different source hashes.", "Give the assets unique target paths.", page_id=page["page_id"])],
                    )
                destination = temp_root / asset.target
                if not destination.exists():
                    _copy_asset(asset.source, destination)
                copied_targets[asset.target] = actual
                support_receipts.append({"path": asset.target, "role": asset.role, "bytes": destination.stat().st_size, "sha256": actual, "extensions": {}})

            creator_receipts: list[dict[str, Any]] = []
            for activity in context.activities.values():
                if activity.structurally_valid and activity.json_source is not None:
                    destination = temp_root / safe_relative_path(activity.json_path, label=f"Creator+ activity {activity.activity_id} JSON target")
                    actual = sha256_file(activity.json_source)
                    prior = copied_targets.get(activity.json_path)
                    if prior and prior != actual:
                        raise PageKitError(
                            "Creator+ output target collision during build.",
                            [_diagnostic("error", "OUTPUT_HASH_COLLISION", f"Creator+ target {activity.json_path!r} has two different source hashes.", "Give the practice payloads unique target paths.", page_id=page["page_id"])],
                        )
                    if not destination.exists():
                        _copy_asset(activity.json_source, destination)
                    copied_targets[activity.json_path] = actual
                    support_receipts.append({"path": activity.json_path, "role": "creatorplus_practice", "bytes": destination.stat().st_size, "sha256": actual, "extensions": {}})
                creator_receipts.append({
                    "activity_id": activity.activity_id,
                    "mode": activity.mode,
                    "runtime_type": activity.runtime_type,
                    "json_path": activity.json_path,
                    "provider_state": activity.provider_state,
                    "extensions": {"wrapper_sha256": activity.wrapper_sha256},
                })

            page_receipts.append({
                "page_id": page["page_id"],
                "page_type": page["page_type"],
                "title": page["title"],
                "filename": page["filename"],
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
                "external_links": external_links(raw),
                "support_assets": sorted(support_receipts, key=lambda row: (row["path"], row["role"])),
                "creatorplus_activities": sorted(creator_receipts, key=lambda row: row["activity_id"]),
                "extensions": {"source_contract": context.source_path.name, "source_contract_sha256": page_sha},
            })

        conformance_rows = _number_diagnostics(conformance_rows)
        conformance_errors = [row for row in conformance_rows if row["severity"] == "error"]
        if conformance_errors:
            raise PageKitError("Generated page conformance failed.", conformance_errors)
        all_diagnostics = _number_diagnostics(
            [
                *[{key: value for key, value in row.items() if key != "id"} for row in preflight_diagnostics],
                *[{key: value for key, value in row.items() if key != "id"} for row in conformance_rows],
            ]
        )
        conformance_report = {
            "schema": "coursecraft.page_conformance/1",
            "mode": mode,
            "status": "pass_with_warnings" if any(row["severity"] == "warning" for row in conformance_rows) else "pass",
            "diagnostics": conformance_rows,
            "extensions": {"live_brightspace_operations": "not_performed"},
        }
        (temp_root / "page-conformance.json").write_text(json.dumps(conformance_report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        declared_dates = [date.fromisoformat(context.page["provenance"]["declared_as_of"]) for context in contexts]
        build_receipt = {
            "schema": "coursecraft.page_build/1",
            "run_id": run_id,
            "mode": mode,
            "declared_as_of": max(declared_dates).isoformat(),
            "kit": file_identity(kit_path, kit_path.name),
            "composition": file_identity(composition_path, composition_path.name),
            "stylesheet": file_identity(stylesheet_path, stylesheet_path.name),
            "producer_files": [
                file_identity(path, path.relative_to(REPO_ROOT).as_posix())
                for path in (PAGE_KIT_SCRIPT, BUILD_SCRIPT, CONFORMANCE_SCRIPT)
            ],
            "publication_hold": bool(blockers),
            "release_blockers": blockers,
            "diagnostics": all_diagnostics,
            "pages": page_receipts,
            "extensions": {
                "kit_id": kit["kit_id"],
                "composition_id": composition["composition_id"],
                "course": composition["course"],
                "module": {"module_id": composition["module"]["module_id"], "title": composition["module"]["title"]},
                "native_objects": [item for item in composition["module"]["items"] if item["type"] == "native_object"],
                "live_brightspace_operations": "not_performed",
            },
        }
        build_issues = [issue for issue in validate_contract(build_receipt) if issue.severity == "error"]
        if build_issues:
            raise PageKitError(
                "Internal page-build receipt validation failed.",
                [_diagnostic("error", "INTERNAL_RECEIPT_INVALID", issue.message, "Correct the producer and schema together.") for issue in build_issues],
            )
        (temp_root / "page-build.json").write_text(json.dumps(build_receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        steps = [
            {"name": "page_preflight", "status": "completed", "started_at": None, "finished_at": None, "artifact_paths": [], "diagnostic_ids": [], "notes": [], "extensions": {}},
            {"name": "page_compile", "status": "unresolved" if blockers else "completed", "started_at": None, "finished_at": None, "artifact_paths": [row["filename"] for row in page_receipts], "diagnostic_ids": [], "notes": [f"{len(blockers)} release blocker(s) retained in review output"] if blockers else [], "extensions": {}},
            {"name": "page_conformance", "status": "completed", "started_at": None, "finished_at": None, "artifact_paths": ["page-conformance.json"], "diagnostic_ids": [row["id"] for row in conformance_rows], "notes": [], "extensions": {}},
        ]
        contract_by_name = {
            **{row["filename"]: "coursecraft.page/1" for row in page_receipts},
            "page-build.json": "coursecraft.page_build/1",
        }
        run_receipt = build_run_identity(
            run_id=run_id,
            source=file_source_identity(composition_path, composition["composition_id"]),
            bundle_dir=temp_root,
            receipt_name="page-build.run.json",
            started_at=started_at,
            steps=steps,
            parameters={
                "mode": mode,
                "kit_id": kit["kit_id"],
                "composition_id": composition["composition_id"],
                "stylesheet_sha256": sha256_file(stylesheet_path),
            },
            contract_by_name=contract_by_name,
            diagnostics=all_diagnostics,
        )
        run_issues = [issue for issue in validate_contract(run_receipt) if issue.severity == "error"]
        if run_issues:
            raise PageKitError(
                "Internal run receipt validation failed.",
                [_diagnostic("error", "INTERNAL_RUN_RECEIPT_INVALID", issue.message, "Correct the producer and shared run contract together.") for issue in run_issues],
            )
        (temp_root / "page-build.run.json").write_text(json.dumps(run_receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        _replace_output(temp_root, output_dir, force=force)
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    return {
        "output_dir": output_dir,
        "build_receipt": output_dir / "page-build.json",
        "run_receipt": output_dir / "page-build.run.json",
        "conformance_report": output_dir / "page-conformance.json",
        "page_count": len(page_receipts),
        "publication_hold": bool(blockers),
        "release_blocker_count": len(blockers),
        "kit_sha256": kit_sha,
        "composition_sha256": composition_sha,
    }
