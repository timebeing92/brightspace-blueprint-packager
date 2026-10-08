"""Stage B: structure-only normalization of a flat blueprint.

Inputs: a source DOCX and a course map (reviewable JSON of structural
decisions). Output: a normalized DOCX in the canonical layout, plus a
paragraph-level ledger that accounts for every source paragraph.

The normalizer can only do five things to authored text, all recorded:
move a paragraph, change its paragraph style, remove accidental block bold,
merge a split heading, or carry a title line into a directive value.
A directive value may also copy the words of a paragraph that stays in place.

Wording changes happen only on the operator's say-so, and only as entries in
the map. ``additions`` place named paragraphs. ``edits`` drop whole paragraphs
or replace one exact stretch of text. A rubric ``clone`` copies an authored
rubric with named cell edits. Every entry says who authorized it and why, and
the fidelity proof lists these changes apart from authored text and fails if
any other wording differs. The normalizer never decides an edit; it applies
the ones it is given.
It cannot edit, add, or delete authored words.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree

from . import vocabulary as V
from .docx_emit import (
    LABEL_FILL,
    STRUCTURE_FILL,
    _run,
    clone_clean,
    copy_numbering,
    make_link_run,
    make_para,
    make_single_column_table,
    remove_numbering,
    replace_text,
    set_style,
    style_ids_by_name,
    unbold,
    write_docx,
)
from .docx_ingest import Document, Para, Table, read_docx, w

REC_ATTR = "bpkrec"  # temporary attribute linking output paragraphs to ledger records
BACK_TO_TOP_RE = re.compile(r"^↑?\s*Back to top\s*(\(#top\))?$")


class MapError(ValueError):
    pass


@dataclass
class OutRecord:
    origin: str  # source paragraph id, or "generated"
    role: str
    text: str
    note: str = ""
    style_from: str = ""
    style_to: str = ""
    section: str = ""
    edited: bool = False
    listed: bool = False  # made a list item by the "bullet" operation


@dataclass
class Disposition:
    id: str
    disposition: str
    section: str = ""
    note: str = ""
    carried_into: str = ""


class Normalizer:
    def __init__(self, doc: Document, cmap: dict[str, Any]) -> None:
        self.doc = doc
        self.cmap = cmap
        self.view = cmap.get("policy", {}).get("suggestions", "proposed")
        self.by_id: dict[str, Para] = doc.by_id()
        self.tables: dict[str, Table] = {t.id: t for t in doc.tables()}
        self.cells = {cell.id: cell for t in doc.tables() for row in t.rows for cell in row}
        self.styles = style_ids_by_name(doc.path)
        # Heading convention. The course map states heading levels in the source
        # document's own terms. The normalized blueprint is written with the frame
        # at V.FRAME_LEVEL; every heading moves by the difference (the "frame shift").
        policy = cmap.get("policy", {})
        body_levels = {node.heading_level for node in doc.body if isinstance(node, Para) and node.heading_level and node.text().strip()}
        self.source_frame_level = int(policy.get("source_frame_level") or
                                      (V.FRAME_LEVEL if V.FRAME_LEVEL in body_levels else V.LEGACY_FRAME_LEVEL))
        self.frame_level = int(policy.get("frame_level", V.FRAME_LEVEL))
        self.frame_shift = self.source_frame_level - self.frame_level
        self.records: list[OutRecord] = []
        self.dispositions: dict[str, Disposition] = {}
        self.generated: list[dict[str, str]] = []
        self.section = ""
        # sibling index: node id -> (siblings list, position)
        self.siblings: dict[str, tuple[list[Para | Table], int]] = {}
        self._index(doc.body)
        # global per-paragraph operations
        self.restyle: dict[str, str] = dict(cmap.get("restyle", {}))
        self.subheads: dict[str, int] = {k: int(v) for k, v in cmap.get("subheads", {}).items()}
        self.unbold_ids: set[str] = set(self._expand(cmap.get("unbold", [])))
        # "bullet": [{"ids": [...], "like": "p00451", "reason": "..."}]: make paragraphs list items
        # with the same list definition as the paragraph named in "like". Words unchanged.
        self.bullet_like: dict[str, str] = {}
        for entry in cmap.get("bullet", []):
            for pid in self._expand(entry["ids"]):
                self.bullet_like[pid] = entry["like"]
        self.supersede: dict[str, str] = {}
        for entry in cmap.get("supersede", []):
            for pid in self._expand(entry["ids"]):
                self.supersede[pid] = entry.get("reason", "superseded structure line")
        self.dropdown_last: dict[str, str | None] = {k: v for k, v in cmap.get("dropdowns", {}).items()}
        self.visual_last: dict[str, str | None] = {k: v for k, v in cmap.get("visuals", {}).items()}
        self.grade_plan = self._read_grade_plan()
        # operator-authorized additions: the only operation that adds words. Each
        # entry names who authorized it and where the words came from.
        self.additions: dict[str, list[dict[str, Any]]] = {}
        for entry in cmap.get("additions", []):
            for key in ("after", "authorized_by", "source", "paragraphs"):
                if not entry.get(key):
                    raise MapError(f"An addition needs '{key}': {entry}")
            self.additions.setdefault(entry["after"], []).append(entry)
        self.additions_written: list[dict[str, Any]] = []
        self.extra_links: dict[str, str] = {}
        self.points_decisions: list[dict[str, Any]] = []
        # operator-authorized edits to authored text: whole paragraphs dropped, or one
        # exact stretch of text replaced. Each names its authorizer and its reason.
        self.edit_drops: dict[str, dict[str, Any]] = {}
        self.edit_replacements: dict[str, list[dict[str, Any]]] = {}
        for entry in cmap.get("edits", []):
            for key in ("authorized_by", "reason"):
                if not entry.get(key):
                    raise MapError(f"An edit needs '{key}': {entry}")
            for pid in self._expand(entry.get("drop", [])):
                if pid in self.edit_drops:
                    raise MapError(f"Paragraph {pid} is dropped by two edits")
                self.edit_drops[pid] = entry
            for item in entry.get("replace", []):
                self.edit_replacements.setdefault(item["para"], []).append({**item, "entry": entry})
            if not entry.get("drop") and not entry.get("replace"):
                raise MapError(f"An edit needs 'drop' or 'replace': {entry}")
        self.edits_written: list[dict[str, Any]] = []
        self._replacements_applied: set[tuple[str, int]] = set()

    # ------------------------------------------------------------------ helpers
    def _index(self, nodes: list[Para | Table]) -> None:
        for position, node in enumerate(nodes):
            self.siblings[node.id] = (nodes, position)
            if isinstance(node, Table):
                for row in node.rows:
                    for cell in row:
                        self._index(cell.children)

    def _nodes(self, spec: str) -> list[Para | Table]:
        """Resolve 'p00001', 'p00001:p00009', or '@c0001' (a whole cell) to sibling nodes."""
        if spec.startswith("@"):
            if spec[1:] not in self.cells:
                raise MapError(f"Unknown cell in {spec!r}")
            return list(self.cells[spec[1:]].children)
        if ":" in spec:
            first, last = spec.split(":", 1)
        else:
            first = last = spec
        if first not in self.siblings or last not in self.siblings:
            raise MapError(f"Unknown node id in range {spec!r}")
        siblings, a = self.siblings[first]
        siblings_b, b = self.siblings[last]
        if siblings is not siblings_b:
            raise MapError(f"Range {spec!r} spans different containers")
        if b < a:
            raise MapError(f"Range {spec!r} is reversed")
        return siblings[a : b + 1]

    def _expand(self, specs: list[str] | str) -> list[str]:
        """Expand ranges to paragraph ids (paragraphs inside tables included)."""
        if isinstance(specs, str):
            specs = [specs]
        out: list[str] = []
        for spec in specs:
            for node in self._nodes(spec):
                if isinstance(node, Para):
                    out.append(node.id)
                else:
                    out.extend(p.id for p in node.paras())
        return out

    def _read_grade_plan(self) -> dict[str, float]:
        plan: dict[str, float] = {}
        table_id = self.cmap.get("grade_plan_table")
        if not table_id:
            return plan
        table = self.tables[table_id]
        for row in table.rows[1:]:
            if len(row) < 2:
                continue
            name = row[0].text(self.view).strip()
            points = V.parse_points(row[1].text(self.view).strip())
            if name and points is not None and name != V.GRADE_PLAN_TOTAL:
                plan[name] = points
        return plan

    def _dispose(self, pid: str, disposition: str, note: str = "", carried_into: str = "") -> None:
        if pid in self.dispositions:
            raise MapError(
                f"Paragraph {pid} assigned twice: {self.dispositions[pid].disposition} and {disposition}"
            )
        self.dispositions[pid] = Disposition(pid, disposition, self.section, note, carried_into)

    def _tag(self, element: etree._Element, record: OutRecord) -> etree._Element:
        record.section = self.section
        self.records.append(record)
        element.set(REC_ATTR, str(len(self.records) - 1))
        return element

    # ------------------------------------------------------------ emit primitives
    def gen(self, text: str, role: str = "directive", *, note: str = "", style: str | None = None,
            bold: bool = False, fill: str | None = None, bold_prefix: str | None = None) -> etree._Element:
        """A generated structure paragraph (never authored content)."""
        element = make_para(text, style_id=style, bold=bold, fill=fill, bold_prefix=bold_prefix)
        self.generated.append({"text": text, "role": role, "note": note, "section": self.section})
        return self._tag(element, OutRecord("generated", role, text, note))

    def directive(self, keyword: str, value: str = "", note: str = "") -> etree._Element:
        text = f"{keyword}: {value}" if value or keyword not in V.BLOCK_END_MARKERS else keyword
        if keyword in V.BLOCK_END_MARKERS:
            text = keyword
        return self.gen(text, "directive", note=note, fill=STRUCTURE_FILL,
                        bold_prefix=(f"{keyword}:" if keyword not in V.BLOCK_END_MARKERS else keyword))

    def out_level(self, source_level: int) -> int:
        """A heading level stated in the source document's terms, as written in the normalized file."""
        return max(1, min(6, source_level - self.frame_shift))

    def heading(self, text: str, level: int, note: str = "") -> etree._Element:
        level = self.out_level(level)
        return self.gen(text, f"heading{level}", note=note, style=self.styles[f"heading {level}"])

    def edited_text(self, para: Para) -> str:
        """The paragraph's text after any authorized replacements."""
        text = para.text(self.view)
        for item in self.edit_replacements.get(para.id, []):
            if text.count(item["find"]) != 1:
                raise MapError(f"Edit on {para.id}: {item['find'][:50]!r} must occur exactly once (found {text.count(item['find'])})")
            text = text.replace(item["find"], item["with"], 1)
        return text

    def _apply_replacements(self, para: Para, element: etree._Element, record: OutRecord) -> None:
        items = self.edit_replacements.get(para.id)
        if not items:
            return
        before = para.text(self.view)
        for index, item in enumerate(items):
            if not replace_text(element, item["find"], item["with"]):
                raise MapError(f"Edit on {para.id}: {item['find'][:50]!r} must occur exactly once in the paragraph")
            self._replacements_applied.add((para.id, index))
            self.edits_written.append({"kind": "replace", "para": para.id, "find": item["find"], "with": item["with"],
                                       "authorized_by": item["entry"]["authorized_by"], "reason": item["entry"]["reason"],
                                       "section": self.section})
        record.text = self.edited_text(para)
        record.edited = True
        record.note = (record.note + "; " if record.note else "") + "text edited on the operator's authority"
        self.edits_written[-1]["before"] = before
        self.edits_written[-1]["after"] = record.text

    def keep(self, para: Para, role: str = "kept", note: str = "") -> etree._Element:
        """Copy an authored paragraph, applying mapped style operations and authorized edits only."""
        element = clone_clean(para.element, self.view)
        record = OutRecord(para.id, role, para.text(self.view), note, style_from=para.style)
        self._apply_replacements(para, element, record)
        target = self.restyle.get(para.id)
        if para.id in self.subheads:
            target = f"heading {self.subheads[para.id]}"
        shifted_by_rule = False
        if target is None and para.heading_level is not None and self.frame_shift:
            target = f"heading {para.heading_level}"
            shifted_by_rule = True
        if target is not None and target.lower().startswith("heading"):
            target = f"heading {self.out_level(int(target.split()[1]))}"
        if target is not None:
            if target.lower() == "normal":
                set_style(element, None)
                record.style_to = "Normal"
            else:
                set_style(element, self.styles[target.lower()])
                if target.lower().startswith("heading"):
                    remove_numbering(element) if self.cmap.get("policy", {}).get("headings_drop_list_numbering") else None
                record.style_to = target
        if para.id in self.unbold_ids:
            unbold(element)
            record.note = (record.note + "; " if record.note else "") + "accidental block bold removed"
        if para.id in self.bullet_like:
            like = self.by_id[self.bullet_like[para.id]]
            copy_numbering(element, like.element)
            record.note = (record.note + "; " if record.note else "") + f"made a list item like {like.id}"
            record.style_to = record.style_to or (para.style or "Normal")
            record.listed = True
        disposition = role
        if (record.style_to and record.style_to.lower() != (para.style or "normal").lower()) or record.listed:
            disposition = "kept_restyled"
            record.role = "kept_restyled"
            if shifted_by_rule:
                record.note = (record.note + "; " if record.note else "") + f"frame shift: every heading moves up {self.frame_shift} (one-to-one convention)"
        if para.id in self.unbold_ids:
            disposition = "kept_unbolded" if disposition == "kept" else disposition + "+unbolded"
        if record.edited:
            disposition = "kept_edited" if disposition == "kept" else disposition + "+edited"
        self._dispose(para.id, disposition, note=record.note or (f"{para.style or 'Normal'} → {record.style_to}" if record.style_to else ""))
        return self._tag(element, record)

    def keep_table(self, table: Table, note: str = "") -> etree._Element:
        """Copy a whole table verbatim (all of its paragraphs are kept in place)."""
        element = clone_clean(table.element, self.view)
        source_paras = list(table.paras())
        out_paras = list(element.iter(w("p")))
        if len(source_paras) != len(out_paras):
            raise MapError(f"Table {table.id}: paragraph count changed while copying")
        for para, out in zip(source_paras, out_paras):
            if para.fully_deleted:
                self._dispose(para.id, "kept_in_table_pending_deletion_text_removed", note="pending deletion inside copied table")
            elif not para.text(self.view).strip():
                self._dispose(para.id, "kept_empty_in_table")
            elif para.id in self.edit_replacements:
                self._dispose(para.id, "kept_edited", note="inside table copied whole; text edited on the operator's authority")
            else:
                self._dispose(para.id, "kept", note=note or "inside table copied whole")
            if para.id in self.edit_drops:
                raise MapError(f"Edit drops {para.id}, which sits inside a table that is copied whole")
            record = OutRecord(para.id, "kept_in_table", para.text(self.view), note, style_from=para.style)
            self._apply_replacements(para, out, record)
            self._tag(out, record)
        return element

    def carried(self, spec: dict[str, Any], keyword: str) -> str:
        """Value for a directive, carried from a source paragraph or stated in the map."""
        if "carry" in spec:
            para = self.by_id[spec["carry"]]
            text = self.edited_text(para).strip()
            if spec.get("strip_colon") and text.endswith(":"):
                text = text[:-1].rstrip()
            if spec["carry"] not in self.dispositions:
                edited = spec["carry"] in self.edit_replacements
                for index, item in enumerate(self.edit_replacements.get(spec["carry"], [])):
                    self._replacements_applied.add((spec["carry"], index))
                    self.edits_written.append({"kind": "replace", "para": spec["carry"], "find": item["find"], "with": item["with"],
                                               "authorized_by": item["entry"]["authorized_by"], "reason": item["entry"]["reason"],
                                               "section": self.section, "before": para.text(self.view), "after": self.edited_text(para)})
                self._dispose(spec["carry"], "carried_into_directive", carried_into=f"{keyword}: {text}",
                              note="title line carried into a directive" + ("; wizard-added trailing colon dropped" if spec.get("strip_colon") else "")
                                   + ("; text edited on the operator's authority" if edited else "; verbatim"))
            return self._with_prefix(text, spec)
        if "copy" in spec:
            # The paragraph stays where it is (an activity's own heading inside its
            # instructions); its words are repeated in a generated structure line.
            para = self.by_id[spec["copy"]]
            text = self.edited_text(para).strip()
            if spec.get("strip_colon") and text.endswith(":"):
                text = text[:-1].rstrip()
            if not text:
                raise MapError(f"Paragraph {spec['copy']} has no text to copy into '{keyword}'")
            return self._with_prefix(text, spec)
        if "text" in spec:
            return spec["text"]
        raise MapError(f"Directive value needs 'carry', 'copy', or 'text': {spec}")

    @staticmethod
    def _with_prefix(text: str, spec: dict[str, Any]) -> str:
        """A title inherits its week ("Week 4") when its own words do not already say it."""
        prefix = spec.get("prefix_if_missing")
        if prefix and not re.match(rf"^{re.escape(prefix)}\b", text, re.IGNORECASE):
            return f"{prefix} {text}"
        return text

    # ----------------------------------------------------------------- content
    def content(self, specs: list[str]) -> list[etree._Element]:
        """Emit a run of authored nodes, handling wizard markers and drops."""
        out: list[etree._Element] = []
        nodes: list[Para | Table] = []
        for spec in specs:
            nodes.extend(self._nodes(spec))
        ends_after: dict[str, list[str]] = {}
        open_blocks: list[tuple[str, str]] = []
        for node in nodes:
            if isinstance(node, Table):
                out.append(self.keep_table(node))
            else:
                emitted = self._content_para(node, ends_after)
                out.extend(emitted)
                if node.id in self.additions:
                    if not emitted:
                        raise MapError(f"Addition anchored after {node.id}, which is not kept in the output")
                    out.extend(self._emit_additions(node.id))
            for end_text in ends_after.pop(node.id, []):
                out.append(self.directive(end_text, note="block end made explicit"))
        if ends_after:
            raise MapError(f"Block end never reached inside its content range: {ends_after}")
        return out

    def _drop_authorized(self, para: Para) -> None:
        entry = self.edit_drops[para.id]
        self._dispose(para.id, "dropped_authorized", note=f"removed on the operator's authority: {entry['reason']}")
        text = para.text(self.view)
        if text.strip():
            self.edits_written.append({"kind": "drop", "para": para.id, "before": text, "after": "",
                                       "authorized_by": entry["authorized_by"], "reason": entry["reason"], "section": self.section})

    def _emit_additions(self, anchor: str) -> list[etree._Element]:
        """Paragraphs the operator authorized that are not in the source document."""
        return self._emit_addition_entries(self.additions.pop(anchor), anchor)

    def _emit_addition_entries(self, entries: list[dict[str, Any]], anchor: str) -> list[etree._Element]:
        out: list[etree._Element] = []
        for entry in entries:
            for key in ("authorized_by", "source", "paragraphs"):
                if not entry.get(key):
                    raise MapError(f"An addition needs '{key}': {entry}")
            for spec in entry["paragraphs"]:
                if spec.get("like"):
                    # borrow paragraph properties (style, list, spacing) from an authored neighbor
                    element = clone_clean(self.by_id[spec["like"]].element, self.view)
                    for child in list(element):
                        if child.tag != w("pPr"):
                            element.remove(child)
                else:
                    element = etree.Element(w("p"))
                text = ""
                for run in spec["runs"]:
                    if run.get("href"):
                        rel_id = f"rIdBpkAdd{len(self.extra_links) + 1}"
                        self.extra_links[rel_id] = run["href"]
                        element.append(make_link_run(run["text"], rel_id))
                    else:
                        element.append(_run(run["text"], bold=bool(run.get("bold")), italic=bool(run.get("italic"))))
                    text += run["text"]
                row = {"after": anchor, "text": text, "links": [r["href"] for r in spec["runs"] if r.get("href")],
                       "authorized_by": entry["authorized_by"], "source": entry["source"],
                       "reason": entry.get("reason", ""), "section": self.section}
                self.additions_written.append(row)
                out.append(self._tag(element, OutRecord("generated", "authorized_addition", text,
                                                        f"added on the operator's authority; {entry['source']}")))
        return out

    def _rubric_clone(self, block: dict[str, Any]) -> list[etree._Element]:
        """A rubric the operator asked for that differs from an authored one by named edits."""
        clone = block["clone"]
        for key in ("name", "table", "cell_edits", "authorized_by", "source"):
            if not clone.get(key):
                raise MapError(f"A rubric clone needs '{key}': {clone}")
        note = f"added on the operator's authority; {clone['source']}"
        row = {"authorized_by": clone["authorized_by"], "source": clone["source"], "reason": clone.get("reason", ""), "section": self.section}
        out: list[etree._Element] = []
        heading = make_para(clone["name"], style_id=self.styles[f"heading {self.out_level(self.source_frame_level + 1)}"])
        self.additions_written.append({**row, "after": f"rubric cloned from {clone['table']}", "text": clone["name"], "links": []})
        out.append(self._tag(heading, OutRecord("generated", "authorized_addition", clone["name"], note)))
        for user in block.get("used_by", []):
            if isinstance(user, dict):
                user = f"{user['activity']}: {self.carried(user, V.D_RUBRIC_USED_BY)}"
            out.append(self.directive(V.D_RUBRIC_USED_BY, user, note="join made explicit on the rubric side"))
        source_table = self.tables[clone["table"]]
        table = clone_clean(source_table.element, self.view)
        pending = [dict(edit) for edit in clone["cell_edits"]]
        for source_para, para in zip(source_table.paras(), table.iter(w("p"))):
            text = source_para.text(self.view)
            for edit in pending:
                if not edit.get("done") and edit["find"] in text:
                    if not replace_text(para, edit["find"], edit["with"]):
                        raise MapError(f"Rubric clone: {edit['find'][:40]!r} must occur exactly once in its cell paragraph")
                    self.edits_written.append({"kind": "rubric_clone_edit", "para": source_para.id, "find": edit["find"], "with": edit["with"],
                                               "before": text, "after": text.replace(edit["find"], edit["with"], 1),
                                               "authorized_by": clone["authorized_by"], "reason": clone.get("reason", ""),
                                               "section": self.section, "rubric": clone["name"]})
                    text = text.replace(edit["find"], edit["with"], 1)
                    edit["done"] = True
            self.additions_written.append({**row, "after": f"rubric cloned from {clone['table']}", "text": text,
                                           "links": [r.href for r in source_para.visible_runs(self.view) if r.href]})
            self._tag(para, OutRecord("generated", "authorized_addition", text, note))
        missed = [edit["find"] for edit in pending if not edit.get("done")]
        if missed:
            raise MapError(f"Rubric clone: text not found in {clone['table']}: {missed}")
        out.append(table)
        return out

    def _points(self, spec: dict[str, Any], grade_item: str) -> tuple[float, str]:
        """Points for an activity: its own body first, the points table when the body is silent."""
        table = self.grade_plan[grade_item]
        body = spec.get("body_points")
        if not body:
            return table, "from the points table; the activity body states no points"
        line = self.by_id[body["line"]]
        parsed = V.parse_directive(line.text(self.view))
        stated = V.parse_points(parsed[1]) if parsed else None
        decision = {"activity": grade_item, "body_line": body["line"], "body_text": line.text(self.view).strip(),
                    "body_points": stated, "points_table": table}
        if stated is None:
            decision.update(used="points_table", why="the body line gives no value")
            note = f"from the points table; the body line {body['line']} gives no value"
        elif abs(stated - table) < 1e-9:
            decision.update(used="body", why="the body and the points table agree")
            note = f"stated in the activity body ({body['line']}); the points table agrees"
        elif body.get("use") == "body":
            decision.update(used="body", why=body.get("reason", "the body is the authority for points"))
            note = f"stated in the activity body ({body['line']}); the points table row says {V.format_points(table)}"
            table = stated
        elif body.get("use") == "points_table":
            decision.update(used="points_table", why=body.get("reason", ""), conflict=True)
            note = (f"from the points table; the body line {body['line']} says {V.format_points(stated)} and was not used: "
                    f"{body.get('reason', 'no reason given')}")
        else:
            raise MapError(f"{grade_item!r}: the body says {stated:g} and the points table says {table:g}; "
                           f"the map must say which to use (body_points.use)")
        self.points_decisions.append(decision)
        return table, note

    def _content_para(self, para: Para, ends_after: dict[str, list[str]]) -> list[etree._Element]:
        pid = para.id
        if pid in self.dispositions:  # already carried into a directive
            return []
        if pid in self.edit_drops:
            self._drop_authorized(para)
            return []
        if pid in self.supersede:
            self._dispose(pid, "structure_superseded", note=self.supersede[pid])
            return []
        if para.fully_deleted:
            self._dispose(pid, "dropped_pending_deletion", note="suggested deletion in the Google Doc; proposed view")
            return []
        text = para.text(self.view).strip()
        if not text and not any(run.image for run in para.visible_runs(self.view)):
            self._dispose(pid, "dropped_empty")
            return []
        if BACK_TO_TOP_RE.match(text):
            self._dispose(pid, "structure_superseded", note="page chrome from the old template; the page template supplies its own")
            return []
        parsed = V.parse_directive(text)
        if parsed and parsed[0] == V.D_DROPDOWN:
            last = self.dropdown_last.get(pid, "?")
            if last == "?":
                raise MapError(f"Dropdown opener {pid} has no mapped panel end")
            if last is None:
                self._dispose(pid, "structure_superseded", note="dropdown opener with no panel content")
                return []
            ends_after.setdefault(last, []).append(V.D_DROPDOWN_END)
            self._dispose(pid, "structure_kept", note="wizard dropdown opener kept verbatim")
            el = clone_clean(para.element, self.view)
            return [self._tag(el, OutRecord(pid, "structure_kept", para.text(self.view)))]
        if parsed and parsed[0] == V.D_VISUAL:
            last = self.visual_last.get(pid, "?")
            if last == "?":
                raise MapError(f"Visual cue {pid} has no mapped extent")
            if last is None:
                self._dispose(pid, "structure_superseded", note="visual cue marker with no remaining content")
                return []
            ends_after.setdefault(last, []).insert(0, V.D_VISUAL_END)
            self._dispose(pid, "structure_kept", note="wizard visual cue kept verbatim")
            el = clone_clean(para.element, self.view)
            return [self._tag(el, OutRecord(pid, "structure_kept", para.text(self.view)))]
        if parsed and parsed[0] in (V.D_VIDEO, V.D_IMAGE):
            self._dispose(pid, "structure_kept", note=f"wizard {parsed[0].lower()} line kept verbatim")
            el = clone_clean(para.element, self.view)
            return [self._tag(el, OutRecord(pid, "structure_kept", para.text(self.view)))]
        return [self.keep(para)]

    # ------------------------------------------------------------------ objects
    def object_block(self, spec: dict[str, Any]) -> list[etree._Element]:
        """Directive header plus authored content for one page/link/module/activity."""
        out: list[etree._Element] = []
        for pid in self._expand(spec.get("supersede", [])):
            if pid not in self.dispositions:
                self._dispose(pid, "structure_superseded", note=spec.get("supersede_reason", "stale extraction line replaced by regenerated directives"))
        kind = spec["type"]
        opener = {
            "module": V.D_MODULE, "page": V.D_PAGE, "link": V.D_LINK, "assignment": V.D_ASSIGNMENT,
            "discussion": V.D_DISCUSSION, "quiz": V.D_QUIZ, "checklist": V.D_CHECKLIST,
        }[kind]
        if kind in ("assignment", "discussion", "quiz") and spec.get("grade_item"):
            grade_item = spec["grade_item"]
            if grade_item not in self.grade_plan:
                raise MapError(f"Grade item not found in the points table: {grade_item!r}")
            title = self.carried(spec["title"], opener) if spec.get("title") else grade_item
            out.append(self.directive(opener, title, note=spec.get("title_note", "title taken from the points table row")))
            points, points_note = self._points(spec, grade_item)
            out.append(self.directive(V.D_POINTS, V.format_points(points), note=points_note))
            out.append(self.directive(V.D_GRADE_ITEM, grade_item, note=spec.get("grade_note", "points table row text")))
        else:
            out.append(self.directive(opener, self.carried(spec["title"], opener), note=spec.get("title_note", "")))
        if spec.get("rubric"):
            out.append(self.directive(V.D_RUBRIC, spec["rubric"], note=spec.get("rubric_note", "rubric title as written in the Rubric Appendix")))
        for keyword, value_spec in spec.get("directives", []):
            note = value_spec.get("source", "") if isinstance(value_spec, dict) else ""
            out.append(self.directive(keyword, self.carried(value_spec, keyword), note=note))
        out.extend(self.content(spec.get("content", [])))
        if spec.get("append"):
            # authorized additions that belong at the end of this object (for example an extra checklist item)
            out.extend(self._emit_addition_entries(spec["append"], f"end of {kind}"))
        return out

    # --------------------------------------------------------------------- build
    def build(self) -> etree._Element:
        cmap = self.cmap
        source_body = self.doc.body_element
        root = copy.deepcopy(self.doc.tree.getroot())
        body = root.find(w("body"))
        sect_pr = body.find(w("sectPr"))
        for child in list(body):
            body.remove(child)
        add = body.append

        # 1. title lines and front-matter tables
        self.section = "front"
        for pid in cmap["title"]:
            add(self.keep(self.by_id[pid], role="kept"))
        for table_id in cmap["front_tables"]:
            add(make_para())
            self._tag(body[-1], OutRecord("generated", "spacer", ""))
            add(self.keep_table(self.tables[table_id], note="front-matter table copied whole"))

        # 2. course introduction
        intro = cmap["course_introduction"]
        self.section = "course_introduction"
        add(self._heading_from(intro["heading"], self.source_frame_level))
        for spec in intro["objects"]:
            for element in self.object_block(spec):
                add(element)

        # 3. before week 1
        pre = cmap["before_week_1"]
        self.section = "before_week_1"
        add(self._heading_from(pre["heading"], self.source_frame_level))
        rows: list[tuple[list[etree._Element], str | None]] = []
        for row in pre["rows"]:
            label_text = self.carried(row["label"], "row label")
            label = self.gen(label_text, "row_label", bold=True, note=row["label"].get("source", "item title"))
            rows.append(([label], LABEL_FILL))
            body_children: list[etree._Element] = []
            for spec in row["objects"]:
                body_children.extend(self.object_block(spec))
            rows.append((body_children, None))
            self._tag_closing(rows[-1][0])
        add(make_single_column_table(rows, self.tables[pre["template_table"]].element))
        self._record_cell_closers(body[-1])
        for pid in self._expand(pre.get("supersede", [])):
            if pid not in self.dispositions:
                self._dispose(pid, "structure_superseded", note=pre.get("supersede_reason", "wizard line replaced by explicit directives"))

        # 4. course content marker and weeks
        if cmap.get("course_content_line"):
            self.section = "weeks"
            add(self.keep(self.by_id[cmap["course_content_line"]], role="structure_kept"))
        label_templates = self._label_templates()
        for week in cmap["weeks"]:
            self.section = f"week_{week['number']}"
            add(self._week_heading(week))
            add(self._week_table(week, label_templates))
            self._record_cell_closers(body[-1])

        # 5. course-level activities
        acts = cmap["course_activities"]
        self.section = "course_activities"
        add(self._heading_from(acts["heading"], self.source_frame_level))
        for element in self.content(acts.get("intro", [])):
            add(element)
        for spec in acts["objects"]:
            for element in self.object_block(spec):
                add(element)

        # 6. rubrics
        rub = cmap["rubrics"]
        self.section = "rubrics"
        if rub.get("title"):
            add(self.keep(self.by_id[rub["title"]]))
        add(self._heading_from(rub["heading"], self.source_frame_level))
        for element in self.content(rub.get("intro", [])):
            add(element)
        for block in rub["blocks"]:
            if "notes" in block:
                for element in self.content(block["notes"]):
                    add(element)
                continue
            if "clone" in block:
                for element in self._rubric_clone(block):
                    add(element)
                continue
            name_para = self.by_id[block["name"]]
            self.restyle.setdefault(block["name"], f"heading {self.source_frame_level + 1}")
            add(self.keep(name_para))
            for user in block.get("used_by", []):
                if isinstance(user, dict):
                    # {"activity": "Discussion", "copy": "p00285"}: follow the activity's own heading
                    user = f"{user['activity']}: {self.carried(user, V.D_RUBRIC_USED_BY)}"
                add(self.directive(V.D_RUBRIC_USED_BY, user, note="join made explicit on the rubric side"))
            for element in self.content(block.get("content", [])):
                add(element)
            add(self.keep_table(self.tables[block["table"]], note="rubric grid copied whole"))
        if rub.get("retired"):
            self.section = "retired_rubrics"
            add(self.heading(V.H_RETIRED_RUBRICS, self.source_frame_level, note="boundary heading for rubrics the blueprint itself marks as old"))
            saved = (self.restyle, self.subheads)
            for element in self.content(rub["retired"]):
                add(element)

        # 7. extraction notes
        notes = cmap.get("notes")
        if notes:
            self.section = "notes"
            add(self._heading_from(notes["heading"], self.source_frame_level))
            for element in self.content(notes.get("content", [])):
                add(element)

        if sect_pr is not None:
            body.append(sect_pr)
        return root

    def _heading_from(self, pid: str, level: int) -> etree._Element:
        para = self.by_id[pid]
        self.restyle[pid] = f"heading {level}"
        return self.keep(para, role="structure_kept")

    def _week_heading(self, week: dict[str, Any]) -> etree._Element:
        spec = week["heading"]
        if "keep" in spec:
            return self._heading_from(spec["keep"], self.source_frame_level)
        parts = [self.by_id[pid] for pid in spec["merge"]]
        text = " ".join(p.text(self.view).strip() for p in parts if p.text(self.view).strip())
        for para in parts:
            self._dispose(para.id, "merged_into_heading", carried_into=text, note="split heading merged; words unchanged")
        for pid in spec.get("drop_empty", []):
            self._dispose(pid, "dropped_empty", note="empty heading paragraph")
        level = self.out_level(self.source_frame_level)
        return self.gen(text, f"heading{level}_merged", style=self.styles[f"heading {level}"], note="merged from " + "+".join(spec["merge"]))

    def _label_templates(self) -> dict[str, list[Para]]:
        """One clean set of wizard label paragraphs per section, reused for every week."""
        templates = self.cmap.get("label_templates", {})
        return {key: [self.by_id[pid] for pid in ids] for key, ids in templates.items()}

    def _label_row(self, key: str, templates: dict[str, list[Para]]) -> list[etree._Element]:
        out = []
        for para in templates[key]:
            element = clone_clean(para.element, self.view)
            set_style(element, None)
            out.append(self._tag(element, OutRecord("generated", "section_label", para.text(self.view),
                                                    note=f"wizard template label cloned from {para.id}")))
        return out

    def _week_table(self, week: dict[str, Any], templates: dict[str, list[Para]]) -> etree._Element:
        # source label paragraphs in this week are replaced by the uniform label set
        for pid in self._expand(week.get("labels", [])):
            if pid not in self.dispositions:
                para = self.by_id[pid]
                if not para.text(self.view).strip():
                    self._dispose(pid, "dropped_empty")
                else:
                    self._dispose(pid, "structure_superseded", note="section label re-emitted from the uniform wizard label set (same wording)")
        for pid in self._expand(week.get("supersede", [])):
            if pid not in self.dispositions:
                self._dispose(pid, "structure_superseded", note=week.get("supersede_reason", "stale extraction line"))
        rows: list[tuple[list[etree._Element], str | None]] = []
        for key in V.SECTION_KEYS:
            rows.append((self._label_row(key, templates), LABEL_FILL))
            children: list[etree._Element] = []
            section = week.get(key)
            saved = self.section
            self.section = f"{saved}.{key}"
            if key == "overview" and section:
                children.extend(self.object_block({"type": "page", **section["page"]}))
                children.extend(self.content(section.get("content", [])))
            elif key in ("objectives", "resources") and section:
                children.extend(self.content(section.get("content", [])))
            elif key in ("assignments", "discussions") and section:
                for spec in section:
                    children.extend(self.object_block(spec))
            elif key == "checklist" and section:
                children.extend(self.object_block({"type": "checklist", **section}))
            self.section = saved
            rows.append((children, None))
        return make_single_column_table(rows, self.tables[week["template_table"]].element)

    def _tag_closing(self, children: list[etree._Element]) -> None:
        return None

    def _record_cell_closers(self, table: etree._Element) -> None:
        """Record the empty closing paragraphs Word requires in generated cells."""
        for para in table.iter(w("p")):
            if para.get(REC_ATTR) is None:
                self._tag(para, OutRecord("generated", "spacer", "", note="required closing paragraph"))

    # ------------------------------------------------------------------ run
    def run(self, out_path: Path) -> dict[str, Any]:
        root = self.build()
        # every remaining source paragraph must be explicitly accounted for
        unassigned = [p for p in self.doc.paras() if p.id not in self.dispositions]
        leftovers = []
        for para in unassigned:
            if para.id in self.edit_drops:
                self._drop_authorized(para)
            elif para.id in self.supersede:
                self._dispose(para.id, "structure_superseded", note=self.supersede[para.id])
            elif para.fully_deleted:
                self._dispose(para.id, "dropped_pending_deletion", note="suggested deletion in the Google Doc; proposed view")
            elif not para.text(self.view).strip() and not any(r.image for r in para.runs):
                self._dispose(para.id, "dropped_empty")
            else:
                leftovers.append(para)
        if leftovers:
            preview = "; ".join(f"{p.id} {p.text(self.view)[:50]!r}" for p in leftovers[:25])
            raise MapError(f"{len(leftovers)} source paragraph(s) are not accounted for by the course map: {preview}")
        ordered: list[OutRecord] = []
        for para in root.iter(w("p")):
            index = para.get(REC_ATTR)
            if index is None:
                raise MapError("Output paragraph without a ledger record")
            ordered.append(self.records[int(index)])
            del para.attrib[REC_ATTR]
        for element in root.iter():
            if element.get(REC_ATTR) is not None:
                del element.attrib[REC_ATTR]
            for attr in list(element.attrib):
                # Word 2010 paragraph ids must be unique; cloned labels would repeat them
                if attr.endswith("}paraId") or attr.endswith("}textId"):
                    del element.attrib[attr]
        if self.additions:
            raise MapError(f"Additions never placed (anchor not inside any content range): {sorted(self.additions)}")
        not_dropped = [pid for pid in self.edit_drops if self.dispositions[pid].disposition != "dropped_authorized"]
        if not_dropped:
            raise MapError(f"Edits drop paragraphs that the map uses elsewhere: {not_dropped[:8]}")
        unused = [(pid, item["find"][:40]) for pid, items in self.edit_replacements.items()
                  for index, item in enumerate(items) if (pid, index) not in self._replacements_applied]
        if unused:
            raise MapError(f"Edits never applied (paragraph not kept or carried): {unused[:8]}")
        write_docx(self.doc.path, out_path, root, extra_links=self.extra_links)
        return {
            "records": ordered,
            "dispositions": self.dispositions,
            "generated": self.generated,
            "additions": self.additions_written,
            "edits": self.edits_written,
            "points_decisions": self.points_decisions,
            "heading_convention": {"source_frame_level": self.source_frame_level, "frame_level": self.frame_level,
                                   "frame_shift": self.frame_shift},
        }


def normalize(source_docx: Path, course_map: Path, out_docx: Path) -> dict[str, Any]:
    doc = read_docx(source_docx)
    cmap = json.loads(Path(course_map).read_text(encoding="utf-8"))
    expected = cmap.get("source", {}).get("sha256")
    if expected and expected != doc.sha256:
        raise MapError(f"Course map was written for source {expected[:12]}…, got {doc.sha256[:12]}…")
    normalizer = Normalizer(doc, cmap)
    result = normalizer.run(out_docx)
    result["doc"] = doc
    result["normalizer"] = normalizer
    return result
