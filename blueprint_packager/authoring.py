"""Explicit authoring markers, readiness, and supported media URL handling.

These are authoring conventions, never inferred from styling or arbitrary prose.
"""
from __future__ import annotations

import re
from typing import Any, Iterator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

# Reserved, human-readable guidance written by the blank-template generator.
# Recognition is exact: similar prose, changed punctuation, and longer sentences
# remain authored content. These are authoring conventions, not text-removal rules.
AUTHOR_NOTE_PREFIX = "Author note:"
WRITING_PROMPTS = {
    "course_description": "Write the course description here.",
    "required_materials": "List the required materials here.",
    "course_learning_outcome": "Write a course learning outcome here.",
    "welcome": "Write the welcome message here.",
    "student_resources": "Write the student and course resources here.",
    "week_introduction": "Write the week introduction here.",
    "learning_objective": "Write a learning objective here.",
    "readings_multimedia": "Add the readings and multimedia here.",
    "assignment_instructions": "Write the assignment instructions here.",
    "discussion_prompt": "Write the discussion prompt here.",
    "panel_content": "Write the panel content here.",
    "rubric_descriptor": "Write the rubric descriptor here.",
}
_WRITING_PROMPT_TEXTS = frozenset(WRITING_PROMPTS.values())

MARKER = re.compile(r"^\[\s*(authoring|placeholder|video placeholder|video)\s*:\s*(.*?)\s*\]$", re.I | re.S)


def marker(text: str) -> tuple[str, str] | None:
    """Recognize a whole-paragraph authoring convention, leaving other prose alone."""
    stripped = text.strip()
    if stripped.startswith(AUTHOR_NOTE_PREFIX):
        return "authoring", stripped[len(AUTHOR_NOTE_PREFIX):].strip()
    if stripped in _WRITING_PROMPT_TEXTS:
        return "placeholder", stripped
    match = MARKER.fullmatch(stripped)
    return (match[1].lower(), match[2].strip()) if match else None


def absolute_web_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
        return (parts.scheme in ("http", "https") and bool(parts.hostname)
                and not parts.username and not parts.password
                and not re.search(r"[\s<>\[\]]", value) and parts.port != 0)
    except ValueError:
        return False


def video_player_url(value: str) -> str | None:
    """Recognize an exact provider host and convert supported share URLs locally.

    No network request, arbitrary iframe HTML, or provider URL guessing is used.
    Vimeo player query parameters (including private-video hashes) are preserved.
    """
    if not absolute_web_url(value):
        return None
    p = urlsplit(value)
    if p.scheme != "https" or p.port not in (None, 443):
        return None
    host, path = p.hostname.lower(), p.path.rstrip("/")
    query = parse_qs(p.query)

    def youtube_query() -> str | None:
        extras = [(k, v) for k, values in query.items() if k not in ("v", "t", "si", "feature") for v in values]
        time = (query.get("t") or parse_qs(p.fragment).get("t") or [None])[0]
        if time is not None and "start" not in query:
            match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
            if time.isdigit():
                start = int(time)
            elif match and any(match.groups()):
                start = sum(int(v or 0) * unit for v, unit in zip(match.groups(), (3600, 60, 1)))
            else:
                return None
            extras.append(("start", str(start)))
        return urlencode(extras)
    if host == "player.vimeo.com" and re.fullmatch(r"/video/\d+", path):
        return value
    if host in ("vimeo.com", "www.vimeo.com") and re.fullmatch(r"/\d+", path):
        return urlunsplit(("https", "player.vimeo.com", "/video" + path, p.query, p.fragment))
    if host in ("www.youtube.com", "youtube.com", "www.youtube-nocookie.com", "youtube-nocookie.com"):
        match = re.fullmatch(r"/embed/([A-Za-z0-9_-]{11})", path)
        if match:
            return value
        if path == "/watch" and host in ("www.youtube.com", "youtube.com"):
            ids = parse_qs(p.query).get("v", [])
            if len(ids) == 1 and re.fullmatch(r"[A-Za-z0-9_-]{11}", ids[0]):
                extras = youtube_query()
                return urlunsplit(("https", "www.youtube.com", "/embed/" + ids[0], extras, "")) if extras is not None else None
    if host == "youtu.be" and re.fullmatch(r"/[A-Za-z0-9_-]{11}", path):
        extras = youtube_query()
        return urlunsplit(("https", "www.youtube.com", "/embed" + path, extras, "")) if extras is not None else None
    return None


def walk_blocks(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if value.get("kind"):
            yield value
        for key, child in value.items():
            if key not in ("source_accounting", "diagnostics", "readiness", "joins", "title_lines"):
                yield from walk_blocks(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_blocks(child)


def readiness(model: dict[str, Any], settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = settings or {}
    retained = set(settings.get("retain_video_placeholders", []))
    fallbacks = set(settings.get("video_link_fallbacks", []))
    findings: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(code: str, message: str, where: str, *, retained: bool = False) -> None:
        key = code, message, where
        if key not in seen:
            findings.append({"code": code, "message": message, "where": where,
                             "severity": "info" if retained else "error", "status": "retained" if retained else "unresolved"})
            seen.add(key)

    for d in model.get("diagnostics", []):
        if d.get("severity") == "error":
            add(d["code"], d["message"], d.get("where", d.get("location", "document")))
    for block in walk_blocks(model):
        where = block.get("src", "document")
        if block["kind"] == "placeholder":
            add("AUTHORING_PLACEHOLDER", block["text"], where)
        if block["kind"] == "video":
            title = block.get("title", "")
            if not title.strip():
                add("VIDEO_TITLE_MISSING", "Give the video an accessible title.", where)
            if block.get("placeholder"):
                add("VIDEO_PLACEHOLDER", f"Video pending: {title}", where, retained=title in retained)
            elif not video_player_url(block.get("href", "")):
                allowed = title in fallbacks and absolute_web_url(block.get("href", ""))
                add("VIDEO_URL_UNSUPPORTED", f"Video '{title}' needs a supported player URL or an explicit link fallback.", where, retained=allowed)

    # Only exact known generator prompts and explicit scaffold tokens are pending.
    # Parentheses in ordinary authored prose are never treated as instructions.
    old_prompts = {"(Catalog description.)", "(Textbook or required materials, with citations.)",
                        "(One outcome per paragraph.)",
                        "(Welcome text. Add more pages with their own Page: and Page heading: lines.)",
                        "(Resources text.)",
                        "(Introduce the week here. Headings inside a page start at Heading 2.)",
                        "(Introduce the week here. The four examples below are real: keep, change, or delete them.)",
                        "(Leave the Items line to build the list from this week's activities, or replace it with typed items.)",
                        "(descriptor)", "(One objective per bullet.)",
                        "(Readings, media, and links. Use a Heading 2 for each group if you group them.)",
                        "(Instructions. Headings inside an activity start at Heading 2. Change the points here and in the points table together.)",
                        "(Prompt. Say when the first post and the responses are due by day of the week, not by date.)",
                        "(Anything between the bracket lines is inside the panel: paragraphs, bullets, links.)",
                        "(A callout: a highlighted box for a note, a reminder, or a short aside. Shaded blue on the page.)",
                        "(The warm callout, for something to keep in mind. The tone word is the only difference.)"}
    for entry in model.get("source_accounting", {}).get("entries", []):
        if entry.get("disposition") in ("authoring_guidance", "notes", "retired", "empty"):
            continue
        text = entry.get("text", "").strip()
        if text in old_prompts or (entry.get("disposition") != "authoring_metadata" and re.search(r"\((?:title|topic|descriptor|first criterion|second criterion)\)", text)):
            add("TEMPLATE_SCAFFOLD", f"Complete the template field: {text[:120]}", entry["id"])
    unresolved = [f for f in findings if f["status"] == "unresolved"]
    return {"schema": "blueprint_packager.readiness/1", "state": "draft" if unresolved else "ready",
            "ready": not unresolved, "findings": findings}
