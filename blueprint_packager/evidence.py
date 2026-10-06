"""Evidence helpers: use a source Brightspace export to recover structure the
flat blueprint lost (for example where an inherited dropdown panel ends).

These helpers only propose ranges. The course map records the result and a
human reviews it; the normalizer never guesses silently.
"""
from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path

from .docx_ingest import Document, Para, Table
from .vocabulary import D_DROPDOWN


def squash(text: str) -> str:
    """Whitespace- and punctuation-spacing-insensitive form used only for matching."""
    text = unicodedata.normalize("NFKC", html.unescape(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("‑", "-").replace(" ", " ")
    return re.sub(r"\s+", "", text)


def export_details(unpacked_dir: Path) -> dict[str, str]:
    """Map squashed <summary> title -> squashed panel body, across all HTML pages."""
    panels: dict[str, str] = {}
    for path in sorted(unpacked_dir.glob("*.html")):
        source = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"<details[^>]*>(.*?)</details>", source, re.S | re.I):
            block = match.group(1)
            summary = re.search(r"<summary[^>]*>(.*?)</summary>", block, re.S | re.I)
            if not summary:
                continue
            panels[squash(summary.group(1))] = squash(block[summary.end():])
    return panels


def propose_dropdown_ranges(doc: Document, unpacked_dir: Path) -> dict[str, dict]:
    """For each dropdown opener, propose the last paragraph of its panel.

    A following paragraph belongs to the panel while its text is found, in
    order, inside the corresponding <details> body of the source export.
    Openers with no matching export panel are returned with `evidence: none`.
    """
    panels = export_details(unpacked_dir)
    proposals: dict[str, dict] = {}

    def scan(children: list[Para | Table]) -> None:
        for index, node in enumerate(children):
            if isinstance(node, Table):
                for row in node.rows:
                    for cell in row:
                        scan(cell.children)
                continue
            text = node.text().strip()
            if not text.startswith(D_DROPDOWN + ":") or node.fully_deleted:
                continue
            title = text.split(":", 1)[1].strip()
            body = panels.get(squash(title))
            if body is None:
                proposals[node.id] = {"title": title, "evidence": "none", "last": None, "members": []}
                continue
            cursor = 0
            members: list[str] = []
            for follower in children[index + 1:]:
                if isinstance(follower, Table):
                    break
                ftext = squash(follower.text())
                if not ftext:
                    continue
                found = body.find(ftext, cursor)
                if found < 0:
                    break
                cursor = found + len(ftext)
                members.append(follower.id)
            proposals[node.id] = {
                "title": title,
                "evidence": "export_details",
                "last": members[-1] if members else None,
                "members": members,
                "panel_fully_matched": cursor == len(body),
            }

    scan(doc.body)
    return proposals
