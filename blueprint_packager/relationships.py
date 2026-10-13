"""Relationship reports and explicitly requested, previewable activity renames."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

from .docx_ingest import read_docx
from .joins import all_activities, resolve
from .reader import read_model

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def relationship_report(model: dict[str, Any]) -> dict[str, Any]:
    entries = model.get("source_accounting", {}).get("entries", [])
    result = []
    for activity in all_activities(model):
        kind, title = activity["type"], activity["title"]
        label = f"{kind.title()}: {title}"
        refs = []
        for entry in entries:
            text = entry["text"].strip()
            role = None
            if entry["id"] == activity.get("src"):
                role = "activity declaration"
            elif (text == f"Gradebook item: {activity.get('grade_item', '')}"
                  and entry.get("disposition") == "structure" and entry.get("where") == f"object {activity.get('src')}"):
                role = "gradebook declaration"
            elif text == activity.get("grade_item") and entry.get("where") == "grading plan":
                role = "grading-plan row"
            elif (text == f"Used by: {label}" and entry.get("disposition") == "structure"
                  and entry.get("where", "").endswith(" relationship")):
                role = "rubric relationship"
            elif re.search(r"\[\s*(?i:link to " + re.escape(kind) + r")\s*:\s*" + re.escape(title) + r"\s*(?:\||\])", text):
                role = "internal link"
            if role:
                refs.append({"paragraph_id": entry["id"], "role": role, "text": entry["text"]})
        result.append({"kind": kind, "title": title, "week": activity.get("week"),
                       "grade_item": activity.get("grade_item"), "rubric": activity.get("rubric"), "references": refs})
    return {"schema": "blueprint_packager.relationship_report/1", "source": model.get("source"), "activities": result}


def _replace_span(element, start: int, end: int, new: str) -> None:
    cursor = 0
    touched = []
    for node in element.iter():
        value = (node.text or "") if node.tag == W + "t" else "\t" if node.tag == W + "tab" else "\n" if node.tag in (W + "br", W + "cr") else ""
        stop = cursor + len(value)
        if stop > start and cursor < end:
            if node.tag != W + "t":
                raise ValueError("Rename target crosses a line break or tab; edit that exact title in Word first.")
            touched.append((node, cursor, stop, value))
        cursor = stop
    if not touched:
        raise ValueError("Rename target has no editable text run.")
    for index, (node, a, b, value) in enumerate(touched):
        prefix = value[:max(0, start - a)] if index == 0 else ""
        suffix = value[max(0, end - a):] if index == len(touched) - 1 else ""
        node.text = prefix + (new if index == 0 else "") + suffix
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def rename_activity(source: Path, output: Path, *, kind: str, old: str, new: str,
                    apply: bool = False, authorized_by: str = "", reason: str = "") -> dict[str, Any]:
    if kind not in ("assignment", "discussion", "quiz") or not new.strip() or any(c in new for c in "\r\n[]|"):
        raise ValueError("Use an activity kind and a nonempty, single-line title without bracket delimiters.")
    if old == new:
        raise ValueError("The old and new titles are identical.")
    model = read_model(source)
    activities = all_activities(model)
    targets = [a for a in activities if a["type"] == kind and a["title"] == old]
    if len(targets) != 1:
        raise ValueError(f"Expected one exact {kind} title '{old}', found {len(targets)}.")
    if any(a["type"] == kind and a["title"] == new for a in activities):
        raise ValueError(f"An activity already has the title '{new}'.")
    if source.resolve() == output.resolve():
        raise ValueError("Rename writes a new authoring copy; choose a different output path.")
    if output.exists():
        raise FileExistsError(f"Output exists: {output}")
    if apply and (not authorized_by.strip() or not reason.strip()):
        raise ValueError("Applying a rename requires --authorized-by and --reason.")
    doc = read_docx(source)
    rename_grade = targets[0].get("grade_item") == old
    references = next(a["references"] for a in relationship_report(model)["activities"] if a["kind"] == kind and a["title"] == old)
    structural_ids = {r["paragraph_id"] for r in references if r["role"] in ("activity declaration", "rubric relationship")
                      or (rename_grade and r["role"] in ("gradebook declaration", "grading-plan row"))}
    link = re.compile(r"(\[\s*(?i:link to " + re.escape(kind) + r")\s*:\s*)(" + re.escape(old) + r")(?=\s*(?:\||\]))")
    changes = []
    for para in doc.paras():
        text = para.text()
        stripped = text.strip()
        after = text
        spans = []
        if para.id in structural_ids:
            a = text.index(stripped) + len(stripped) - len(old)
            spans.append((a, a + len(old), new))
        else:
            spans.extend((m.start(2), m.end(2), new) for m in link.finditer(text))
        if not spans:
            continue
        if para.has_change:
            raise ValueError(f"Rename target {para.id} contains tracked changes; resolve its title edits before applying the rename.")
        for a, b, replacement in reversed(spans):
            after = after[:a] + replacement + after[b:]
            if apply:
                _replace_span(para.element, a, b, replacement)
        changes.append({"paragraph_id": para.id, "before": text, "after": after,
                        "authorized_by": authorized_by, "reason": reason})
    report = {"schema": "blueprint_packager.rename/1", "status": "applied" if apply else "preview",
              "source": {"path": str(source), "sha256": doc.sha256}, "output": str(output),
              "kind": kind, "old": old, "new": new, "changes": changes,
              "note": "Narrative wording and body headings are unchanged; only exact structural references and internal-link targets are renamed."}
    output.parent.mkdir(parents=True, exist_ok=True)
    if apply:
        root = next(doc.paras()).element.getroottree()
        xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        created = False
        try:
            with zipfile.ZipFile(source) as original, zipfile.ZipFile(output, "x") as changed:
                created = True
                for entry in original.infolist():
                    changed.writestr(entry, xml if entry.filename == "word/document.xml" else original.read(entry.filename))
            after_model = read_model(output)
            after_diags = after_model["diagnostics"] + resolve(after_model)["diagnostics"]
            report["diagnostics"] = after_diags
            report["output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
        except Exception:
            if created:
                output.unlink(missing_ok=True)
            raise
    ledger = output.with_suffix(".rename.json")
    ledger.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["ledger"] = str(ledger)
    return report
