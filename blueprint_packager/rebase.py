"""Carry a course map from one export of a blueprint to a later export.

A course map names paragraphs by position (``p00412``). When the author edits
the live document those positions shift, and a map written for the earlier
export no longer fits. This module lines the two exports up paragraph by
paragraph, translates every id the map uses, and reports what changed so a
person can see which decisions need a second look.

It decides nothing about content. A paragraph that is new in the later export
and sits inside a mapped stretch comes along with it. One that sits between
stretches joins the content stretch that ends just before it in the same cell
or body, and that placement is reported as an inference for a person to confirm
or move (the owner's rule of 2026-10-07; before that, such a paragraph stopped
the run). Only a paragraph with no mapped content neighbour on either side in
its container is left unplaced, and the normalizer still refuses it.
"""
from __future__ import annotations

import copy
import difflib
import re
from typing import Any

from .docx_ingest import Document, Para

PARA_ID = re.compile(r"^p\d{5}$")
RANGE_ID = re.compile(r"^(p\d{5}):(p\d{5})$")
CELL_REF = re.compile(r"^@(c\d{4})$")
TABLE_ID = re.compile(r"^t\d{3}$")
ID_TOKEN = re.compile(r"\bp\d{5}\b")
SIMILAR = 0.55  # two paragraphs this alike, in the same changed stretch, are one edited paragraph
# Lists under these keys are stretches of authored content; a new paragraph may join one.
# Lists under other keys (drop, unbold, ids, title, labels …) name paragraphs to act on and never grow.
CONTENT_KEYS = {"content", "intro", "notes", "retired"}


def _state(para: Para) -> str:
    if para.fully_deleted:
        return "pending deletion"
    if para.fully_inserted:
        return "pending insertion"
    if para.has_change:
        return "pending change"
    return ""


def _pair_changed(old: list[Para], new: list[Para]) -> list[tuple[Para | None, Para | None]]:
    """Pair paragraphs inside one changed stretch, keeping document order."""
    if len(old) == len(new):
        return list(zip(old, new))
    pairs: list[tuple[Para | None, Para | None]] = []
    j = 0
    for para in old:
        best, best_ratio = None, SIMILAR
        for k in range(j, len(new)):
            ratio = difflib.SequenceMatcher(None, para.text("raw"), new[k].text("raw"), autojunk=False).ratio()
            if ratio > best_ratio:
                best, best_ratio = k, ratio
        if best is None:
            pairs.append((para, None))
            continue
        pairs.extend((None, added) for added in new[j:best])
        pairs.append((para, new[best]))
        j = best + 1
    pairs.extend((None, added) for added in new[j:])
    return pairs


def align(old: Document, new: Document) -> dict[str, Any]:
    """Line up two exports. Returns id translations and a list of what changed."""
    old_paras, new_paras = list(old.paras()), list(new.paras())
    matcher = difflib.SequenceMatcher(None, [p.text("raw") for p in old_paras], [p.text("raw") for p in new_paras], autojunk=False)
    para_map: dict[str, str] = {}
    removed: list[dict[str, str]] = []
    added: list[dict[str, str]] = []
    edited: list[dict[str, str]] = []
    resolved: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            pairs: list[tuple[Para | None, Para | None]] = list(zip(old_paras[i1:i2], new_paras[j1:j2]))
        else:
            pairs = _pair_changed(old_paras[i1:i2], new_paras[j1:j2])
        for before, after in pairs:
            if before is not None and after is not None:
                para_map[before.id] = after.id
                if before.text("raw") != after.text("raw"):
                    edited.append({"old": before.id, "new": after.id, "old_text": before.text("raw"), "new_text": after.text("raw")})
                elif _state(before) != _state(after):
                    resolved.append({"old": before.id, "new": after.id, "was": _state(before), "now": _state(after) or "accepted into the text",
                                     "text": after.text("raw")[:120]})
            elif before is not None:
                removed.append({"old": before.id, "was": _state(before), "text": before.text("raw")})
            elif after is not None:
                added.append({"new": after.id, "text": after.text("raw"), "state": _state(after)})

    def containers(doc: Document) -> tuple[dict[str, str], dict[str, str]]:
        table_of, cell_of = {}, {}
        for table in doc.tables():
            for row in table.rows:
                for cell in row:
                    for para in cell.paras(recursive=False):
                        cell_of[para.id] = cell.id
                    for para in cell.paras():
                        table_of.setdefault(para.id, table.id)
        return table_of, cell_of

    def innermost_tables(doc: Document) -> dict[str, str]:
        owner: dict[str, str] = {}
        for table in doc.tables():  # outer tables first; inner tables overwrite
            for para in table.paras():
                owner[para.id] = table.id
        return owner

    _, old_cell_of = containers(old)
    _, new_cell_of = containers(new)
    old_table_of, new_table_of = innermost_tables(old), innermost_tables(new)
    cell_map: dict[str, str] = {}
    table_map: dict[str, str] = {}
    for old_id, new_id in para_map.items():
        if old_id in old_cell_of and new_id in new_cell_of:
            cell_map.setdefault(old_cell_of[old_id], new_cell_of[new_id])
        if old_id in old_table_of and new_id in new_table_of:
            table_map.setdefault(old_table_of[old_id], new_table_of[new_id])
    # cells and tables that hold no paragraphs of their own keep their position among their kind
    old_tables, new_tables = [t.id for t in old.tables()], [t.id for t in new.tables()]
    if len(old_tables) == len(new_tables):
        for a, b in zip(old_tables, new_tables):
            table_map.setdefault(a, b)
    old_cells = [c.id for t in old.tables() for row in t.rows for c in row]
    new_cells = [c.id for t in new.tables() for row in t.rows for c in row]
    if len(old_cells) == len(new_cells):
        for a, b in zip(old_cells, new_cells):
            cell_map.setdefault(a, b)

    order = {p.id: n for n, p in enumerate(old_paras)}
    return {
        "paragraphs": para_map, "cells": cell_map, "tables": table_map,
        "removed": removed, "added": added, "edited": edited, "suggestions_resolved": resolved,
        "identity": all(k == v for k, v in para_map.items()) and not removed and not added
                    and all(k == v for k, v in cell_map.items()) and all(k == v for k, v in table_map.items()),
        "_old_order": order, "_old_ids": [p.id for p in old_paras],
        "counts": {"old_paragraphs": len(old_paras), "new_paragraphs": len(new_paras), "carried": len(para_map),
                   "edited_in_place": len(edited), "removed": len(removed), "added": len(added),
                   "suggestions_resolved": len(resolved)},
    }


def rebase_map(course_map: dict[str, Any], alignment: dict[str, Any], new: Document, old: Document) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Translate every id in a course map. Returns the new map and the entries that could not be carried."""
    paragraphs, cells, tables = alignment["paragraphs"], alignment["cells"], alignment["tables"]
    old_ids, order = alignment["_old_ids"], alignment["_old_order"]
    problems: list[dict[str, str]] = []

    def para(pid: str, where: str, in_list: bool = False) -> str | None:
        if pid in paragraphs:
            return paragraphs[pid]
        if in_list:
            # a list names paragraphs to act on; one that is gone simply needs no action
            problems.append({"where": where, "id": pid, "problem": "paragraph is gone; dropped from this list", "severity": "note"})
        else:
            problems.append({"where": where, "id": pid, "problem": "paragraph is not in the later export"})
        return None

    def span(first: str, last: str, where: str) -> str | None:
        # A range survives as long as any paragraph inside it survives: pull the ends inward.
        if first not in order or last not in order:
            problems.append({"where": where, "id": f"{first}:{last}", "problem": "range end is not a paragraph of the earlier export"})
            return None
        inside = [pid for pid in old_ids[order[first]: order[last] + 1] if pid in paragraphs]
        if not inside:
            problems.append({"where": where, "id": f"{first}:{last}", "problem": "every paragraph of this range is gone"})
            return None
        if inside[0] != first or inside[-1] != last:
            problems.append({"where": where, "id": f"{first}:{last}", "problem": f"range end removed; range now runs {paragraphs[inside[0]]}:{paragraphs[inside[-1]]}", "severity": "note"})
        a, b = paragraphs[inside[0]], paragraphs[inside[-1]]
        return a if a == b and first == last else f"{a}:{b}"

    def value(item: Any, where: str, in_list: bool = False) -> Any:
        if isinstance(item, str):
            if PARA_ID.match(item):
                return para(item, where, in_list)
            match = RANGE_ID.match(item)
            if match:
                return span(match.group(1), match.group(2), where)
            match = CELL_REF.match(item)
            if match:
                if match.group(1) in cells:
                    return "@" + cells[match.group(1)]
                problems.append({"where": where, "id": item, "problem": "cell is not in the later export"})
                return None
            if TABLE_ID.match(item):
                if item in tables:
                    return tables[item]
                problems.append({"where": where, "id": item, "problem": "table is not in the later export"})
                return None
            # ids quoted inside notes follow the paragraphs they name
            return ID_TOKEN.sub(lambda m: paragraphs.get(m.group(0), m.group(0)), item)
        if isinstance(item, list):
            out = [value(x, f"{where}[{n}]", in_list=True) for n, x in enumerate(item)]
            return [x for x, raw in zip(out, item) if x is not None or raw is None]
        if isinstance(item, dict):
            out_dict: dict[str, Any] = {}
            for key, val in item.items():
                new_key = key
                if PARA_ID.match(key):
                    new_key = para(key, f"{where}.{key} (key)")
                    if new_key is None:
                        continue
                out_dict[new_key] = value(val, f"{where}.{key}")
            return out_dict
        return item

    rebased = copy.deepcopy(course_map)
    source = rebased.pop("source", {})
    rebased = value(rebased, "map")
    alignment["inferred_placements"] = _place_added(rebased, alignment, new, problems)
    rebased = {"schema": rebased.pop("schema", course_map.get("schema")), "course": rebased.pop("course", course_map.get("course")),
               "source": {"name": new.path.name, "sha256": new.sha256,
                          "rebased_from": {"name": source.get("name", old.path.name), "sha256": source.get("sha256", old.sha256)},
                          "retrieved": source.get("retrieved", "")},
               **rebased}
    return rebased, problems


def _place_added(rebased: dict[str, Any], alignment: dict[str, Any], new: Document, problems: list[dict[str, str]]) -> list[dict[str, str]]:
    """Attach each new paragraph outside every mapped stretch to the content stretch before it.

    Works in the later export's paragraph order, inside one container (a table cell or the body).
    A stretch grows only across paragraphs nothing else in the map names, so a new paragraph
    never crosses a mapped heading, label, or title line. With no content stretch before it,
    the one after it grows backwards instead. With neither, the paragraph is left unplaced and
    named in `problems`; the normalizer refuses it as before.
    """
    new_paras = list(new.paras())
    index = {para.id: n for n, para in enumerate(new_paras)}
    container = {para.id: para.container for para in new_paras}
    cell_paras: dict[str, list[int]] = {}
    table_paras: dict[str, list[int]] = {}
    for table in new.tables():
        table_paras.setdefault(table.id, [index[p.id] for p in table.paras()])
        for row in table.rows:
            for cell in row:
                cell_paras[cell.id] = [index[p.id] for p in cell.paras()]

    stretches: list[dict[str, Any]] = []  # content stretches that may grow
    mapped: set[int] = set()  # every paragraph position the map names, any key

    def note_string(item: str, holder: list | None, position: int | None, key: str, where: str) -> None:
        match = RANGE_ID.match(item)
        if match and match.group(1) in index and match.group(2) in index:
            a, b = index[match.group(1)], index[match.group(2)]
            mapped.update(range(a, b + 1))
            if holder is not None and key in CONTENT_KEYS:
                stretches.append({"start": a, "end": b, "holder": holder, "position": position, "where": where})
        elif PARA_ID.match(item) and item in index:
            mapped.add(index[item])
            if holder is not None and key in CONTENT_KEYS:
                stretches.append({"start": index[item], "end": index[item], "holder": holder, "position": position, "where": where})
        else:
            cell = CELL_REF.match(item)
            if cell and cell.group(1) in cell_paras:
                mapped.update(cell_paras[cell.group(1)])
            elif TABLE_ID.match(item) and item in table_paras:
                mapped.update(table_paras[item])

    def walk(node: Any, key: str, where: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if PARA_ID.match(k) and k in index:
                    mapped.add(index[k])
                walk(v, k, f"{where}.{k}")
        elif isinstance(node, list):
            for n, item in enumerate(node):
                if isinstance(item, str):
                    note_string(item, node, n, key, f"{where}[{n}]")
                else:
                    walk(item, key, f"{where}[{n}]")
        elif isinstance(node, str):
            note_string(node, None, None, key, where)

    walk(rebased, "", "map")
    placements: list[dict[str, str]] = []
    added = sorted((a for a in alignment["added"] if a["new"] in index), key=lambda a: index[a["new"]])
    for item in added:
        pid = item["new"]
        at = index[pid]
        if at in mapped:
            continue  # inside a mapped stretch: comes along
        here = container[pid]
        same = [s for s in stretches if container[new_paras[s["end"]].id] == here]
        before = max((s for s in same if s["end"] < at and not any(n in mapped for n in range(s["end"] + 1, at))),
                     key=lambda s: s["end"], default=None)
        after = min((s for s in same if s["start"] > at and not any(n in mapped for n in range(at + 1, s["start"]))),
                    key=lambda s: s["start"], default=None)
        text = item["text"][:120]
        if before is not None:
            first = new_paras[before["start"]].id
            before["holder"][before["position"]] = f"{first}:{pid}"
            before["end"] = at
            placements.append({"new": pid, "text": text, "joined": f"{first}:{pid}", "after": new_paras[at - 1].id if at else "",
                               "where": before["where"], "how": "joined the content stretch that ends just before it"})
        elif after is not None:
            last = new_paras[after["end"]].id
            after["holder"][after["position"]] = f"{pid}:{last}"
            after["start"] = at
            placements.append({"new": pid, "text": text, "joined": f"{pid}:{last}", "before": new_paras[after["start"] + 1].id if after["start"] + 1 < len(new_paras) else "",
                               "where": after["where"], "how": "nothing mapped before it in its container; joined the content stretch after it"})
        else:
            problems.append({"where": "later export", "id": pid,
                             "problem": f"new paragraph has no mapped content neighbour in its container; place it by hand: {text!r}"})
            continue
        mapped.add(at)
    return placements


def report(alignment: dict[str, Any], problems: list[dict[str, str]], old: Document, new: Document) -> dict[str, Any]:
    return {
        "schema": "blueprint_packager.map_rebase/0.1",
        "from": {"name": old.path.name, "sha256": old.sha256},
        "to": {"name": new.path.name, "sha256": new.sha256},
        "ids_unchanged": alignment["identity"],
        "counts": alignment["counts"],
        "edited_in_place": alignment["edited"],
        "added": alignment["added"],
        "removed": alignment["removed"],
        "suggestions_resolved": alignment["suggestions_resolved"],
        "placed_by_inference": alignment.get("inferred_placements", []),
        "map_entries_needing_a_look": problems,
    }


def report_markdown(rep: dict[str, Any]) -> str:
    c = rep["counts"]
    lines = ["# Course map carried to a later export", "",
             f"From `{rep['from']['name']}` (`{rep['from']['sha256'][:12]}`) to `{rep['to']['name']}` (`{rep['to']['sha256'][:12]}`).", "",
             "| Measure | Count |", "|---|---|",
             f"| Paragraphs in the earlier export | {c['old_paragraphs']} |", f"| Paragraphs in the later export | {c['new_paragraphs']} |",
             f"| Carried across | {c['carried']} |", f"| Edited in place | {c['edited_in_place']} |",
             f"| Added | {c['added']} |", f"| Removed | {c['removed']} |",
             f"| Suggestions resolved with no change of text | {c['suggestions_resolved']} |",
             f"| New paragraphs placed by inference | {len(rep.get('placed_by_inference', []))} |", "",
             "Paragraph ids are unchanged." if rep["ids_unchanged"] else "Paragraph ids shifted; every id in the map was translated.", ""]

    def block(title: str, rows: list[str]) -> None:
        if rows:
            lines.extend([f"## {title}", "", *rows, ""])

    block("Edited in place", [f"- `{e['new']}`: was {e['old_text'][:160]!r}; now {e['new_text'][:160]!r}" for e in rep["edited_in_place"]])
    block("Added", [f"- `{a['new']}` {('(' + a['state'] + ') ') if a['state'] else ''}{a['text'][:200]!r}" for a in rep["added"] if a["text"].strip()])
    block("Removed", [f"- `{r['old']}` {('(' + r['was'] + ') ') if r['was'] else ''}{r['text'][:200]!r}" for r in rep["removed"] if r["text"].strip()])
    grouped: dict[tuple[str, str], int] = {}
    for item in rep["suggestions_resolved"]:
        grouped[(item["was"], item["now"])] = grouped.get((item["was"], item["now"]), 0) + 1
    block("Suggestions resolved", [f"- {n} paragraphs: {was} became {now}" for (was, now), n in grouped.items()])
    block("Placed by inference, confirm",
          [f"- `{p['new']}` {p['text']!r} now in `{p['joined']}` ({p['where']}): {p['how']}" for p in rep.get("placed_by_inference", [])])
    block("Map entries needing a look", [f"- {p['where']}: `{p['id']}` {p['problem']}" for p in rep["map_entries_needing_a_look"]])
    return "\n".join(lines) + "\n"
