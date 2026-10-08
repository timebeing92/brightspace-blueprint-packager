"""Plain Markdown rendering of model blocks, for review packets and companions.

This is a reading aid. It is not a delivery surface and it is never parsed.
"""
from __future__ import annotations

from typing import Any


def runs_text(runs: list[dict[str, Any]], links: bool = True) -> str:
    out = []
    for run in runs:
        text = run.get("text", "").replace("\n", " ")
        if not text:
            continue
        if run.get("href") and links:
            text = f"[{text}]({run['href']})"
        if run.get("b") and text.strip():
            text = f"**{text.strip()}**" + (" " if text.endswith(" ") else "")
        if run.get("i") and text.strip():
            text = f"*{text.strip()}*" + (" " if text.endswith(" ") else "")
        out.append(text)
    return "".join(out).strip()


def plain(runs: list[dict[str, Any]]) -> str:
    return "".join(run.get("text", "") for run in runs).replace("\n", " ").strip()


def blocks_markdown(blocks: list[dict[str, Any]], depth: int = 0, show_src: bool = False) -> str:
    lines: list[str] = []
    pad = "  " * depth
    for block in blocks:
        kind = block["kind"]
        src = f" `{block['src']}`" if show_src and block.get("src") else ""
        if kind == "heading":
            lines.append(f"{pad}{'#' * min(6, block['level'])} {plain(block['runs'])}{src}")
        elif kind == "p":
            lines.append(f"{pad}{runs_text(block['runs'])}{src}")
        elif kind == "li":
            marker = "1." if block.get("ordered") else "-"
            lines.append(f"{pad}{'  ' * block.get('level', 0)}{marker} {runs_text(block['runs'])}{src}")
        elif kind == "dropdown":
            lines.append(f"{pad}> **[Dropdown] {block['title']}**{src}")
            inner = blocks_markdown(block["blocks"], depth, show_src)
            lines.extend(f"{pad}> {line}" if line else f"{pad}>" for line in inner.splitlines())
            lines.append(f"{pad}> **[End dropdown]**")
        elif kind == "visual":
            lines.append(f"{pad}> **[Visual cue: {block['cue']}]**{src}")
            inner = blocks_markdown(block["blocks"], depth, show_src)
            lines.extend(f"{pad}> {line}" if line else f"{pad}>" for line in inner.splitlines())
            lines.append(f"{pad}> **[End visual cue]**")
        elif kind == "video":
            lines.append(f"{pad}**[Video embed]** [{block['title']}]({block.get('href', '')}){src}")
        elif kind == "image":
            lines.append(f"{pad}**[Embedded image]** {block.get('text', '')}{src}")
        elif kind == "table":
            for r_index, row in enumerate(block["rows"]):
                cells = [" / ".join(l for l in blocks_markdown(cell).splitlines() if l) for cell in row]
                lines.append(f"{pad}| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
                if r_index == 0:
                    lines.append(f"{pad}|" + "---|" * len(row))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _activity_markdown(activity: dict[str, Any]) -> list[str]:
    label = {"assignment": "Assignment", "discussion": "Discussion", "quiz": "Quiz", "checklist": "Checklist",
             "page": "Page", "link": "Link", "module": "Module"}[activity["type"]]
    lines = [f"#### {label}: {activity['title']}", ""]
    facts = []
    for key, name in (("points", "Points"), ("grade_item", "Gradebook item"), ("rubric", "Rubric"), ("forum", "Forum"),
                      ("page_heading", "Page heading"), ("url", "URL"), ("visibility", "Visibility"), ("source", "Source"),
                      ("items_source", "Items")):
        if activity.get(key) not in (None, "", []):
            value = activity[key]
            facts.append(f"- {name}: {value:g} pts" if key == "points" else f"- {name}: {value}")
    for placement in activity.get("placement") or []:
        facts.append(f"- Placement: {placement}")
    lines += facts + ([""] if facts else [])
    if activity.get("blocks"):
        lines += [blocks_markdown(activity["blocks"])]
    return lines


def model_markdown(model: dict[str, Any]) -> str:
    """A readable companion to the course model. Reading aid only; never parsed."""
    lines = [f"# {' — '.join(t['text'] for t in model['title_lines'])}", "",
             "> Readable companion generated from the normalized blueprint. The Word file is the editable surface; "
             "the course model JSON is the machine surface. This file is neither.", ""]
    for key, section in model["front_matter"].items():
        lines += [f"## {section['label']}", "", blocks_markdown(section["blocks"])]
    plan = model.get("grade_plan") or {"items": []}
    lines += ["## Points table", "", "| Gradebook item | Points |", "|---|---|"]
    lines += [f"| {item['name']} | {item['points']:g} |" for item in plan["items"]]
    lines += [f"| **Total** | **{plan.get('total_computed', 0):g}** |", ""]
    lines += ["## Course modules, pages, and links", ""]
    for obj in model["modules"] + model["pages"] + model["links"]:
        lines += _activity_markdown(obj)
    for week in model["weeks"]:
        lines += [f"## {week['title']}", ""]
        if week["overview_page"]:
            lines += ["### Overview", ""] + _activity_markdown(week["overview_page"])
        lines += ["### Learning objectives", "", blocks_markdown(week["objectives"]), "### Assigned reading and multimedia", "",
                  blocks_markdown(week["resources"]), "### Assignments", ""]
        for activity in week["assignments"] + week["quizzes"]:
            lines += _activity_markdown(activity)
        if not week["assignments"] and not week["quizzes"]:
            lines += ["None.", ""]
        lines += ["### Discussions", ""]
        for activity in week["discussions"]:
            lines += _activity_markdown(activity)
        if not week["discussions"]:
            lines += ["None.", ""]
        lines += ["### Checklist", ""]
        lines += _activity_markdown(week["checklist"]) if week["checklist"] else ["None.", ""]
    lines += ["## Course-level activities", ""]
    for activity in model["course_activities"]:
        lines += _activity_markdown(activity)
    lines += ["## Rubrics", ""]
    for rubric in model["rubrics"]:
        lines += [f"### {rubric['name']}", ""]
        lines += [f"- Used by: {user}" for user in rubric["used_by"]] or ["- Used by: (no activity)"]
        lines += [f"- Note: {text}" for text in rubric.get("description", [])] + [""]
        grid = rubric.get("grid")
        if grid:
            def num(value):  # a weight or percent the reader could not parse shows as "?" instead of stopping the companion
                return f"{value:g}" if isinstance(value, (int, float)) else "?"

            lines += ["| Criterion | Weight | " + " | ".join(f"{l['name']} ({num(l.get('percent'))}%)" for l in grid["levels"]) + " |",
                      "|---|---|" + "---|" * len(grid["levels"])]
            for criterion in grid["criteria"]:
                cells = [" ".join(plain(b["runs"]) for b in cell if b.get("runs")).replace("|", "\\|") for cell in criterion["cells"]]
                lines.append(f"| {criterion['name']} | {num(criterion.get('weight'))} | " + " | ".join(cells) + " |")
            lines.append("")
    return "\n".join(lines) + "\n"
