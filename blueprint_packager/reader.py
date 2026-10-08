"""Stage C: read a canonical (normalized) blueprint DOCX into the course model.

The reader is deterministic. It keys on the structure vocabulary only:
fixed headings, week-table row labels, and directive lines. It never guesses
an object type or a join; anything it cannot place becomes a diagnostic.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import vocabulary as V
from .docx_ingest import Cell, Document, Para, Table, read_docx

MODEL_SCHEMA = "blueprint_packager.course_model/0.1"

OPENER_TYPES = {
    V.D_MODULE: "module", V.D_PAGE: "page", V.D_LINK: "link", V.D_ASSIGNMENT: "assignment",
    V.D_DISCUSSION: "discussion", V.D_QUIZ: "quiz", V.D_CHECKLIST: "checklist",
}
ATTR_KEYS = {
    V.D_PAGE_HEADING: "page_heading", V.D_PLACEMENT: "placement", V.D_VISIBILITY: "visibility",
    V.D_URL: "url", V.D_POINTS: "points", V.D_GRADE_ITEM: "grade_item", V.D_RUBRIC: "rubric",
    V.D_FORUM: "forum", V.D_SOURCE: "source", V.D_ATTEMPTS: "attempts_allowed",
    V.D_TIME_LIMIT: "time_limit", V.D_SECTIONS: "sections", V.D_QUESTION_TYPES: "question_types",
    V.D_ITEMS: "items_source",
}
MULTI_VALUE = {"placement"}


class Diagnostics:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, severity: str, code: str, message: str, where: str = "") -> None:
        self.items.append({"severity": severity, "code": code, "message": message, "where": where})

    def error(self, code: str, message: str, where: str = "") -> None:
        self.add("error", code, message, where)

    def warn(self, code: str, message: str, where: str = "") -> None:
        self.add("warning", code, message, where)

    def info(self, code: str, message: str, where: str = "") -> None:
        self.add("info", code, message, where)


class Reader:
    def __init__(self, doc: Document) -> None:
        self.frame_level = V.FRAME_LEVEL
        self.doc = doc
        self.diag = Diagnostics()

    # ------------------------------------------------------------------ blocks
    def runs(self, para: Para) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for run in para.visible_runs():
            item = run.to_dict()
            item.pop("change", None)
            if out and {k: v for k, v in out[-1].items() if k != "text"} == {k: v for k, v in item.items() if k != "text"}:
                out[-1]["text"] += item["text"]
            else:
                out.append(item)
        return out

    def para_block(self, para: Para) -> dict[str, Any] | None:
        text = para.text()
        if not text.strip() and not any(run.image for run in para.runs):
            return None
        block: dict[str, Any] = {"runs": self.runs(para), "src": para.id}
        level = para.heading_level
        if level is not None:
            block.update(kind="heading", level=level)
        elif para.list_num_id is not None:
            block.update(kind="li", level=para.list_level or 0, list_id=para.list_num_id,
                         ordered=self.doc.list_format(para) not in (None, "bullet", "none"))
        else:
            block.update(kind="p")
        return block

    def table_block(self, table: Table) -> dict[str, Any]:
        return {
            "kind": "table",
            "src": table.id,
            "rows": [[self.blocks(cell.children, where=table.id) for cell in row] for row in table.rows],
        }

    def blocks(self, nodes: list[Para | Table], where: str = "") -> list[dict[str, Any]]:
        """Content nodes -> block tree, grouping dropdowns and visual cues."""
        root: list[dict[str, Any]] = []
        stack: list[tuple[str, dict[str, Any]]] = []

        def target() -> list[dict[str, Any]]:
            return stack[-1][1]["blocks"] if stack else root

        for node in nodes:
            if isinstance(node, Table):
                target().append(self.table_block(node))
                continue
            text = node.text().strip()
            parsed = V.parse_directive(text)
            if parsed:
                keyword, value = parsed
                if keyword == V.D_DROPDOWN:
                    block = {"kind": "dropdown", "title": value, "blocks": [], "src": node.id}
                    target().append(block)
                    stack.append(("dropdown", block))
                    continue
                if keyword == V.D_VISUAL:
                    block = {"kind": "visual", "cue": value, "blocks": [], "src": node.id}
                    attrs = V.parse_bracket_attrs(text)
                    if attrs:
                        block["attrs"] = attrs  # e.g. {"tone": "gold"} or {"color": "#b7791f"}
                    target().append(block)
                    stack.append(("visual", block))
                    continue
                if keyword in (V.D_DROPDOWN_END, V.D_VISUAL_END):
                    expected = "dropdown" if keyword == V.D_DROPDOWN_END else "visual"
                    if not stack or stack[-1][0] != expected:
                        self.diag.error("BLOCK_END_UNMATCHED", f"'{keyword}' without a matching opener", where or node.id)
                    else:
                        stack.pop()
                    continue
                if keyword == V.D_VIDEO:
                    link = next((run.href for run in node.visible_runs() if run.href), "")
                    target().append({"kind": "video", "title": value, "href": link, "src": node.id,
                                     "list_item": node.list_num_id is not None})
                    continue
                if keyword == V.D_IMAGE:
                    target().append({"kind": "image", "text": value, "src": node.id})
                    continue
            block = self.para_block(node)
            if block is not None:
                target().append(block)
        for kind, block in stack:
            self.diag.error("BLOCK_NOT_CLOSED", f"{kind} '{block.get('title') or block.get('cue')}' has no end marker", where or block["src"])
        return root

    # ----------------------------------------------------------------- objects
    def objects(self, nodes: list[Para | Table], where: str, allowed: tuple[str, ...]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Split nodes into directive-headed objects. Returns (objects, loose_blocks).

        Openers are scoped: only the object types allowed in this section can
        start an object, and never inside an open dropdown or visual cue. An
        authored line such as "Checklist: Consider duties..." inside an overview
        page is therefore content, not structure.
        """
        objects: list[dict[str, Any]] = []
        depth = 0
        loose_nodes: list[Para | Table] = []
        current: dict[str, Any] | None = None
        current_nodes: list[Para | Table] = []
        in_header = False

        def close() -> None:
            nonlocal current, current_nodes
            if current is not None:
                current["blocks"] = self.blocks(current_nodes, where=f"{where} / {current['type']} '{current['title']}'")
                objects.append(current)
            current, current_nodes = None, []

        for node in nodes:
            if isinstance(node, Para):
                parsed = V.parse_directive(node.text().strip())
                if parsed and parsed[0] in (V.D_DROPDOWN, V.D_VISUAL):
                    depth += 1
                elif parsed and parsed[0] in V.BLOCK_END_MARKERS:
                    depth = max(0, depth - 1)
                if parsed and parsed[0] in allowed and depth == 0:
                    close()
                    current = {"type": OPENER_TYPES[parsed[0]], "title": parsed[1], "src": node.id}
                    in_header = True
                    continue
                if parsed and parsed[0] in ATTR_KEYS and current is not None and in_header:
                    key = ATTR_KEYS[parsed[0]]
                    if key in MULTI_VALUE:
                        current.setdefault(key, []).append(parsed[1])
                    elif key in current:
                        self.diag.error("ATTRIBUTE_REPEATED", f"'{parsed[0]}' appears twice", f"{where} / '{current['title']}'")
                    else:
                        current[key] = parsed[1]
                    continue
                if not node.text().strip():
                    continue
            in_header = False
            if current is None:
                loose_nodes.append(node)
            else:
                current_nodes.append(node)
        close()
        for obj in objects:
            if "points" in obj:
                value = V.parse_points(obj["points"])
                if value is None:
                    self.diag.error("POINTS_UNREADABLE", f"Cannot read points '{obj['points']}'", f"{where} / '{obj['title']}'")
                obj["points"] = value
        return objects, self.blocks(loose_nodes, where=where)

    # ------------------------------------------------------------------ tables
    def grade_plan(self, table: Table) -> dict[str, Any]:
        items = []
        total_stated = None
        for row in table.rows[1:]:
            if len(row) < 2:
                continue
            name = row[0].text().strip()
            raw = row[1].text().strip()
            if not name and not raw:
                continue
            points = V.parse_points(raw)
            if name == V.GRADE_PLAN_TOTAL:
                total_stated = points
                continue
            if points is None:
                self.diag.error("GRADE_PLAN_POINTS", f"Points table row '{name}' has unreadable points '{raw}'", "points table")
                continue
            items.append({"name": name, "points": points})
        computed = sum(item["points"] for item in items)
        if total_stated is not None and abs(computed - total_stated) > 1e-9:
            self.diag.error("GRADE_PLAN_TOTAL", f"Points table rows add to {computed:g}, stated total is {total_stated:g}", "points table")
        return {"items": items, "total_stated": total_stated, "total_computed": computed, "src": table.id}

    LEVEL_RE = re.compile(r"^(?P<name>.*?)[\s—–\-]*?(?P<pct>\d+(?:\.\d+)?)\s*%\+?\s*$", re.S)
    WEIGHT_RE = re.compile(r"\(?\s*(\d+(?:\.\d+)?)\s*%\s*\)?\s*$")

    def rubric_grid(self, table: Table, name: str) -> dict[str, Any]:
        where = f"rubric '{name}'"
        header = [cell.text().strip() for cell in table.rows[0]]
        levels = []
        for cell_text in header[1:]:
            flat = " ".join(cell_text.split())
            match = self.LEVEL_RE.match(flat)
            if not match:
                self.diag.error("RUBRIC_LEVEL", f"Level header '{flat}' has no percentage", where)
                levels.append({"name": flat, "percent": None})
            else:
                levels.append({"name": match.group("name").strip(" —–-"), "percent": float(match.group("pct")), "header": flat})
        criteria = []
        for row in table.rows[1:]:
            cells = list(row)
            label = " ".join(cells[0].text().split())
            if not label:
                continue
            weight_match = self.WEIGHT_RE.search(label)
            weight = float(weight_match.group(1)) if weight_match else None
            if weight is None:
                self.diag.error("RUBRIC_WEIGHT", f"Criterion '{label}' has no weight", where)
            criteria.append({
                "name": label,
                "weight": weight,
                "cells": [self.blocks(cell.children, where=where) for cell in cells[1:]],
            })
        total = sum(c["weight"] or 0 for c in criteria)
        if criteria and abs(total - 100) > 1e-9:
            self.diag.error("RUBRIC_WEIGHT_TOTAL", f"Criterion weights add to {total:g}, not 100", where)
        for criterion in criteria:
            if len(criterion["cells"]) != len(levels):
                self.diag.error("RUBRIC_SHAPE", f"Criterion '{criterion['name']}' has {len(criterion['cells'])} cells for {len(levels)} levels", where)
        return {"levels": levels, "criteria": criteria, "criterion_header": header[0] if header else "", "src": table.id}

    # -------------------------------------------------------------------- read
    BARE_LINK_TEXT = {"here", "click here", "link", "this link", "read more", "more", "this", "this page", "learn more"}

    def _page_checks(self, model: dict[str, Any]) -> None:
        """Page-gate rules run early, with paragraph ids (13a, agreed 2026-10-08): heading level jumps,
        tables without a header row, and bare link text. Warnings, never blocking."""
        top = V.content_top(self.frame_level)

        def walk(blocks: list[dict[str, Any]], where: str, previous: list[int]) -> None:
            for block in blocks:
                kind = block.get("kind")
                if kind == "heading":
                    level = int(block["level"])
                    if level > (previous[0] + 1 if previous else top):
                        self.diag.warn("HEADING_LEVEL_JUMP",
                                       f"Heading level jumps to {level} after {previous[0] if previous else 'the page heading'}; "
                                       f"the page gate will report this", block.get("src", where))
                    previous[:] = [level]
                if kind == "table":
                    rows = block.get("rows") or []
                    if rows and (len(rows) > 1 or len(rows[0]) > 1):  # a one-cell table is a box, not data
                        head = rows[0]
                        texts = [[r for b in cell for r in (b.get("runs") or []) if r.get("text", "").strip()] for cell in head]
                        if not all(cell and all(r.get("b") for r in cell) for cell in texts):
                            self.diag.warn("TABLE_HEADER_MISSING",
                                           "Table's first row is not a bold header row; make the header bold so it reads as a header",
                                           block.get("src", where))
                        for row in rows:
                            for cell in row:
                                walk(cell, where, previous)
                for run in block.get("runs") or []:
                    href, text = run.get("href", ""), run.get("text", "").strip()
                    if href and (text.lower().rstrip(".") in self.BARE_LINK_TEXT or text == href):
                        self.diag.warn("LINK_TEXT_BARE", f"Link text '{text[:40]}' says nothing about its target; name the destination",
                                       block.get("src", where))
                for key in ("blocks", "children"):
                    if isinstance(block.get(key), list):
                        walk(block[key], where, previous)

        for page in model.get("course_pages", []):
            walk(page.get("blocks", []), f"Page: {page['title']}", [])
        for week in model.get("weeks", []):
            previous: list[int] = []
            walk(week["overview_page"].get("blocks", []), f"Week {week['number']} page", previous)
            for key in ("assignments", "discussions", "quizzes"):
                for activity in week.get(key, []):
                    walk(activity.get("blocks", []), f"Week {week['number']} / {activity['title']}", [])
        for activity in model.get("course_activities", []):
            walk(activity.get("blocks", []), activity["title"], [])

    def read(self) -> dict[str, Any]:
        doc = self.doc
        model: dict[str, Any] = {
            "schema": MODEL_SCHEMA,
            "vocabulary": V.VOCABULARY_VERSION,
            "source": {"name": doc.path.name, "sha256": doc.sha256},
            "title_lines": [],
            "front_matter": {},
            "grade_plan": None,
            "pages": [],
            "modules": [],
            "links": [],
            "weeks": [],
            "course_activities": [],
            "rubrics": [],
            "retired_rubrics": {"paragraphs": 0, "tables": 0, "names": []},
            "notes": [],
        }
        # the frame level: Heading 1 by convention; Heading 2 in older blueprints
        levels = {node.heading_level for node in doc.body if isinstance(node, Para) and node.heading_level and node.text().strip()}
        frame_level = V.FRAME_LEVEL if V.FRAME_LEVEL in levels else (V.LEGACY_FRAME_LEVEL if V.LEGACY_FRAME_LEVEL in levels else V.FRAME_LEVEL)
        self.frame_level = frame_level
        model["conventions"] = {"frame_level": frame_level, "content_top": V.content_top(frame_level),
                                "heading_offset": frame_level - V.FRAME_LEVEL}
        if frame_level != V.FRAME_LEVEL:
            self.diag.info("FRAME_LEVEL_LEGACY", f"The frame is at Heading {frame_level}; the convention is Heading {V.FRAME_LEVEL}. "
                           f"Every heading is read one level up so page levels still map one to one", "document")
        # split the body into regions at frame-level / Title paragraphs
        regions: list[tuple[str, Para | None, list[Para | Table]]] = [("front", None, [])]
        for node in doc.body:
            if isinstance(node, Para) and (node.heading_level == frame_level or node.style == "Title") and node.text().strip():
                text = node.text().strip()
                if node.style == "Title" and not regions[-1][2] and regions[-1][0] == "front":
                    regions[-1][2].append(node)
                    continue
                regions.append((text, node, []))
            else:
                regions[-1][2].append(node)

        for name, heading, nodes in regions:
            if name == "front":
                self._front(nodes, model)
            elif name == V.H_COURSE_INTRO:
                objects, loose = self.objects(nodes, V.H_COURSE_INTRO, V.SCOPE_COURSE_PAGES)
                self._collect(objects, model, context=V.H_COURSE_INTRO)
                if loose:
                    self.diag.warn("LOOSE_CONTENT", f"{len(loose)} block(s) under '{name}' belong to no object", name)
            elif name == V.H_BEFORE_WEEK_1:
                for node in nodes:
                    if isinstance(node, Table):
                        self._pre_week_table(node, model)
            elif V.WEEK_HEADING_RE.match(name):
                self._week(name, nodes, model)
            elif name == V.H_COURSE_ACTIVITIES:
                objects, loose = self.objects(nodes, name, V.SCOPE_ACTIVITIES)
                for obj in objects:
                    obj["scope"] = "course"
                    model["course_activities"].append(obj)
                model["course_activities_notes"] = loose
            elif name == V.H_RUBRICS:
                self._rubrics(nodes, model)
            elif name == V.H_RETIRED_RUBRICS:
                retired = model["retired_rubrics"]
                for node in nodes:
                    if isinstance(node, Table):
                        retired["tables"] += 1
                    elif node.text().strip():
                        retired["paragraphs"] += 1
                        if node.is_heading:
                            retired["names"].append(node.text().strip())
            elif name == V.H_NOTES:
                model["notes"] = [n.text().strip() for n in nodes if isinstance(n, Para) and n.text().strip()]
            elif heading is not None and heading.style == "Title":
                continue  # e.g. the "Rubrics" tab title
            else:
                self.diag.warn("UNKNOWN_SECTION", f"Heading '{name}' at Heading {self.frame_level} is not part of the structure vocabulary. "
                               f"Heading {self.frame_level} is reserved for the frame; content inside a page starts at Heading {V.content_top(self.frame_level)}", name)
        self._page_checks(model)
        model["diagnostics"] = self.diag.items
        return model

    def _front(self, nodes: list[Para | Table], model: dict[str, Any]) -> None:
        for node in nodes:
            if isinstance(node, Para):
                if node.text().strip():
                    model["title_lines"].append({"text": node.text().strip(), "style": node.style, "src": node.id})
                continue
            first = node.rows[0][0].text().strip() if node.rows and node.rows[0] else ""
            header = tuple(cell.text().strip() for cell in node.rows[0]) if node.rows else ()
            if header == V.GRADE_PLAN_HEADER:
                model["grade_plan"] = self.grade_plan(node)
                continue
            for key, prefix in V.FRONT_LABELS.items():
                if first.startswith(prefix):
                    body_cells = [cell for row in node.rows[1:] for cell in row]
                    model["front_matter"][key] = {
                        "label": first,
                        "blocks": [b for cell in body_cells for b in self.blocks(cell.children, where=key)],
                        "src": node.id,
                    }
                    break
            else:
                self.diag.warn("FRONT_TABLE_UNKNOWN", f"Front-matter table starting '{first[:40]}' was not recognized", node.id)
        if model["grade_plan"] is None:
            self.diag.error("GRADE_PLAN_MISSING", "No 'Assignment | Points' table found", "front matter")

    def _collect(self, objects: list[dict[str, Any]], model: dict[str, Any], context: str) -> None:
        for obj in objects:
            obj["context"] = context
            if obj["type"] == "page":
                model["pages"].append(obj)
            elif obj["type"] == "module":
                model["modules"].append(obj)
            elif obj["type"] == "link":
                model["links"].append(obj)
            else:
                obj["scope"] = "course"
                model["course_activities"].append(obj)

    def _pre_week_table(self, table: Table, model: dict[str, Any]) -> None:
        rows = [row[0] for row in table.rows if row]
        for index in range(0, len(rows) - 1, 2):
            label = rows[index].text().strip()
            objects, loose = self.objects(rows[index + 1].children, f"{V.H_BEFORE_WEEK_1} / {label}", V.SCOPE_PRE_WEEK)
            if not objects:
                self.diag.warn("ROW_WITHOUT_OBJECT", f"Row '{label}' declares no object", V.H_BEFORE_WEEK_1)
            if loose:
                self.diag.warn("LOOSE_CONTENT", f"Row '{label}' has content before any object directive", V.H_BEFORE_WEEK_1)
            # a module row: the objects under the Module line belong to that module, and a
            # Placement line adds a further module rather than replacing this one
            modules = [obj for obj in objects if obj["type"] == "module"]
            if len(modules) > 1:
                self.diag.error("MODULE_ROW", f"Row '{label}' declares {len(modules)} modules; one module per row", V.H_BEFORE_WEEK_1)
            if modules:
                home = modules[0]["title"]
                for obj in objects:
                    if obj is modules[0]:
                        continue
                    placements = [home] + [p for p in (obj.get("placement") or []) if p != home]
                    obj["placement"] = placements
                    obj["placement_source"] = "module row"
            self._collect(objects, model, context=V.H_BEFORE_WEEK_1)

    def _week(self, heading_text: str, nodes: list[Para | Table], model: dict[str, Any]) -> None:
        match = V.WEEK_HEADING_RE.match(heading_text)
        week: dict[str, Any] = {
            "number": int(match.group(1)), "title": heading_text, "topic": match.group(2).strip(),
            "overview_page": None, "objectives": [], "resources": [], "assignments": [], "discussions": [],
            "quizzes": [], "checklist": None,
        }
        tables = [n for n in nodes if isinstance(n, Table)]
        stray = [n for n in nodes if isinstance(n, Para) and n.text().strip()]
        if stray:
            self.diag.warn("STRAY_PARAGRAPH", f"{len(stray)} paragraph(s) sit between the heading and the table", heading_text)
        if len(tables) != 1:
            self.diag.error("WEEK_TABLE", f"Expected one week table, found {len(tables)}", heading_text)
            model["weeks"].append(week)
            return
        cells = [row[0] for row in tables[0].rows if row]
        seen: list[str] = []
        for index in range(0, len(cells) - 1, 2):
            label_text = cells[index].text().strip()
            key = V.section_for_label(label_text)
            where = f"{heading_text} / {label_text.split(':')[0]}"
            if key is None:
                self.diag.error("SECTION_LABEL", f"Row label '{label_text[:50]}' is not a known section", heading_text)
                continue
            seen.append(key)
            body = cells[index + 1].children
            if key == "overview":
                objects, loose = self.objects(body, where, V.SCOPE_OVERVIEW)
                pages = [o for o in objects if o["type"] == "page"]
                if len(pages) != 1 or len(objects) != 1:
                    self.diag.error("OVERVIEW_PAGE", f"Overview must declare exactly one Page, found {len(pages)} page(s) in {len(objects)} object(s)", where)
                if pages:
                    week["overview_page"] = pages[0]
                if loose:
                    self.diag.error("LOOSE_CONTENT", "Overview content appears before the Page directive", where)
            elif key in ("objectives", "resources"):
                week[key] = self.blocks(body, where=where)
            elif key in ("assignments", "discussions"):
                objects, loose = self.objects(body, where, V.SCOPE_ASSIGNMENTS if key == "assignments" else V.SCOPE_DISCUSSIONS)
                if loose:
                    self.diag.error("LOOSE_CONTENT", f"{len(loose)} block(s) belong to no activity", where)
                for obj in objects:
                    obj["week"] = week["number"]
                    if obj["type"] == "quiz":
                        week["quizzes"].append(obj)
                    elif obj["type"] == "assignment" and key == "assignments":
                        week["assignments"].append(obj)
                    elif obj["type"] == "discussion" and key == "discussions":
                        week["discussions"].append(obj)
                    else:
                        self.diag.error("OBJECT_IN_WRONG_SECTION", f"{obj['type']} '{obj['title']}' sits in the {key} row", where)
            elif key == "checklist":
                objects, loose = self.objects(body, where, V.SCOPE_CHECKLIST)
                if objects:
                    if len(objects) > 1 or objects[0]["type"] != "checklist":
                        self.diag.error("CHECKLIST", "Checklist row must hold one Checklist object", where)
                    week["checklist"] = objects[0]
                    week["checklist"]["items"] = [b for b in objects[0]["blocks"] if b["kind"] in ("li", "p", "heading")]
                    source = objects[0].get("items_source")
                    if source and source != V.ITEMS_FROM_ACTIVITIES:
                        self.diag.error("CHECKLIST_ITEMS_SOURCE", f"'{V.D_ITEMS}: {source}' is not understood. Use '{V.ITEMS_FROM_ACTIVITIES}' or list the items.", where)
                    # derived: items are built from the week's activities; authored items are extras
                    week["checklist"]["derive"] = source == V.ITEMS_FROM_ACTIVITIES
                elif loose:
                    self.diag.error("LOOSE_CONTENT", "Checklist items without a Checklist directive", where)
        if seen != V.SECTION_KEYS:
            self.diag.error("WEEK_ROWS", f"Section rows are {seen}; expected {V.SECTION_KEYS}", heading_text)
        model["weeks"].append(week)

    def _rubrics(self, nodes: list[Para | Table], model: dict[str, Any]) -> None:
        current: dict[str, Any] | None = None
        pending_notes: list[str] = []
        intro: list[str] = []
        for node in nodes:
            if isinstance(node, Para):
                text = node.text().strip()
                if not text:
                    continue
                if node.heading_level == V.content_top(self.frame_level):
                    current = {"name": text, "used_by": [], "description": [], "grid": None, "notes_before": pending_notes, "src": node.id}
                    pending_notes = []
                    model["rubrics"].append(current)
                    continue
                parsed = V.parse_directive(text)
                if current is not None and current["grid"] is None:
                    if parsed and parsed[0] == V.D_RUBRIC_USED_BY:
                        current["used_by"].append(parsed[1])
                    else:
                        current["description"].append(text)
                elif current is None:
                    intro.append(text)
                else:
                    pending_notes.append(text)
            else:
                if current is None or current["grid"] is not None:
                    self.diag.error("RUBRIC_TABLE_ORPHAN", "A table in the Rubric Appendix has no rubric heading before it", node.id)
                    continue
                current["grid"] = self.rubric_grid(node, current["name"])
        model["rubric_appendix_intro"] = intro
        model["rubric_appendix_trailing_notes"] = pending_notes
        for rubric in model["rubrics"]:
            if rubric["grid"] is None:
                self.diag.error("RUBRIC_NO_GRID", "Rubric heading has no grid table", f"rubric '{rubric['name']}'")


def read_model(path: str | Path) -> dict[str, Any]:
    return Reader(read_docx(path)).read()
