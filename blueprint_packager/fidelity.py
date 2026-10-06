"""Fidelity proof for a normalization run.

The proof is computed from the file actually written to disk: the normalized
DOCX is read back and compared, paragraph by paragraph, with the source in the
chosen suggestion view.
"""
from __future__ import annotations

import collections
import csv
import json
import re
from pathlib import Path
from typing import Any

from .docx_ingest import Document, Para, read_docx

KEPT_ROLES = {"kept", "kept_restyled", "kept_in_table", "structure_kept"}
WORD_RE = re.compile(r"\S+")


def _fmt_runs(para: Para, view: str, ignore_bold: bool = False) -> list[tuple]:
    out: list[tuple] = []
    for run in para.visible_runs(view):
        if not run.text:
            continue
        key = (False if ignore_bold else run.bold, run.italic, run.underline, run.href)
        if out and out[-1][1:] == key:
            out[-1] = (out[-1][0] + run.text, *key)
        else:
            out.append((run.text, *key))
    return out


def prove(result: dict[str, Any], out_docx: Path) -> dict[str, Any]:
    source: Document = result["doc"]
    normalizer = result["normalizer"]
    view = normalizer.view
    records = result["records"]
    dispositions = result["dispositions"]
    by_id = source.by_id()
    written = read_docx(out_docx)
    out_paras = list(written.paras())

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    # A. every source paragraph has exactly one disposition
    source_ids = [p.id for p in source.paras()]
    missing = [pid for pid in source_ids if pid not in dispositions]
    check("every source paragraph is accounted for", not missing,
          f"{len(source_ids)} source paragraphs, {len(dispositions)} dispositions, {len(missing)} missing")

    # B. the written file matches the plan, paragraph by paragraph
    same_length = len(out_paras) == len(records)
    check("written file has the planned paragraph count", same_length, f"{len(out_paras)} written, {len(records)} planned")
    text_mismatch = []
    format_mismatch = []
    kept_source_words: collections.Counter[str] = collections.Counter()
    kept_output_words: collections.Counter[str] = collections.Counter()
    kept_count = 0
    edited_count = 0
    for record, out in zip(records, out_paras):
        if out.text() != record.text:
            text_mismatch.append((record.origin, record.text[:60], out.text()[:60]))
        if record.origin == "generated" or record.role not in KEPT_ROLES:
            continue
        if record.edited:
            edited_count += 1  # compared with its planned text above; listed under authorized edits
            continue
        src = by_id[record.origin]
        kept_count += 1
        if out.text() != src.text(view):
            text_mismatch.append((record.origin, src.text(view)[:60], out.text()[:60]))
        kept_source_words.update(WORD_RE.findall(src.text(view)))
        kept_output_words.update(WORD_RE.findall(out.text()))
        ignore_bold = record.origin in normalizer.unbold_ids
        if _fmt_runs(src, view, ignore_bold) != _fmt_runs(out, "proposed", ignore_bold):
            format_mismatch.append(record.origin)
    check("every kept paragraph is text-identical to its source", not text_mismatch,
          f"{kept_count} kept paragraphs compared; {len(text_mismatch)} mismatches {text_mismatch[:3]}")
    check("kept paragraphs keep their inline formatting and links", not format_mismatch,
          f"{len(format_mismatch)} paragraphs differ in bold/italic/underline/link runs {format_mismatch[:8]}"
          + (f"; block bold intentionally removed from {len(normalizer.unbold_ids)} mapped paragraphs" if normalizer.unbold_ids else ""))
    check("word-for-word equality of kept content", kept_source_words == kept_output_words,
          f"{sum(kept_source_words.values())} words in kept source paragraphs; {sum(kept_output_words.values())} in the written file")

    # C. no pending suggestions or comment anchors remain
    check("no pending suggestions remain in the written file", not any(p.has_change for p in out_paras),
          f"{sum(1 for p in out_paras if p.has_change)} paragraphs with tracked changes")

    # D. carried titles appear verbatim in a directive or label
    out_texts = [p.text() for p in out_paras]
    carried_missing = []
    for disposition in dispositions.values():
        if disposition.disposition != "carried_into_directive":
            continue
        value = disposition.carried_into.split(": ", 1)[1] if ": " in disposition.carried_into else disposition.carried_into
        if not any(value in text for text in out_texts):
            carried_missing.append(disposition.id)
    check("carried title lines appear verbatim in structure lines", not carried_missing, f"{len(carried_missing)} missing {carried_missing[:5]}")

    # E. words that are not in the source are exactly the authorized additions
    additions = result.get("additions", [])
    added_records = [(record, out) for record, out in zip(records, out_paras) if record.role == "authorized_addition"]
    addition_problems = []
    if len(added_records) != len(additions):
        addition_problems.append(f"{len(added_records)} written, {len(additions)} authorized")
    for (record, out), planned in zip(added_records, additions):
        if out.text() != planned["text"]:
            addition_problems.append(f"text differs: {out.text()[:60]!r}")
        if [run.href for run in out.runs if run.href] != planned["links"]:
            addition_problems.append(f"links differ in {planned['text'][:40]!r}")
    added_words = sum(len(WORD_RE.findall(a["text"])) for a in additions)
    check("words not in the source are only the authorized additions", not addition_problems,
          f"{len(additions)} paragraphs, {added_words} words added on the operator's authority" + (f"; {addition_problems[:3]}" if addition_problems else ""))

    # F. authored wording differs only where the map carries an authorized edit
    edits = result.get("edits", [])
    replaced = {e["para"] for e in edits if e["kind"] == "replace"}
    dropped = [e for e in edits if e["kind"] == "drop"]
    dropped_ids = {pid for pid, d in dispositions.items() if d.disposition == "dropped_authorized"}
    edited_dispositions = {pid for pid, d in dispositions.items() if "edited" in d.disposition or
                           (d.disposition == "carried_into_directive" and "edited" in d.note)}
    edit_problems = []
    if edited_dispositions != replaced:
        edit_problems.append(f"edited paragraphs {sorted(edited_dispositions ^ replaced)[:6]} do not match the map")
    if {e["para"] for e in dropped} - dropped_ids:
        edit_problems.append("a dropped paragraph is not recorded as dropped")
    removed_words = sum(len(WORD_RE.findall(e["before"])) for e in dropped)
    check("authored wording changed only by authorized edits", not edit_problems,
          f"{len(replaced)} paragraphs edited, {len(dropped_ids)} paragraphs removed ({removed_words} words), "
          f"{sum(1 for e in edits if e['kind'] == 'rubric_clone_edit')} edits inside a cloned rubric"
          + (f"; {edit_problems}" if edit_problems else ""))

    counts = collections.Counter(d.disposition for d in dispositions.values())
    nonempty_removed = [d for d in dispositions.values() if d.disposition in ("structure_superseded", "dropped_pending_deletion", "dropped_authorized")]
    return {
        "schema": "blueprint_packager.fidelity/1",
        "source": {"name": source.path.name, "sha256": source.sha256, "view": view},
        "output": {"name": out_docx.name, "sha256": written.sha256},
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "disposition_counts": dict(sorted(counts.items())),
        "generated_structure_lines": len(result["generated"]),
        "authorized_additions": additions,
        "authorized_edits": edits,
        "points_decisions": result.get("points_decisions", []),
        "authored_lines_not_carried_forward": len(nonempty_removed),
        "note": "Lines not carried forward are wizard-generated structure lines that were superseded, text under a pending deletion suggestion, or paragraphs removed on the operator's authority. Each is listed with its full text in the ledger.",
    }


def write_ledger(result: dict[str, Any], path: Path) -> None:
    source: Document = result["doc"]
    view = result["normalizer"].view
    dispositions = result["dispositions"]
    style_changes = {r.origin: r for r in result["records"] if r.origin != "generated"}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_id", "disposition", "section", "style_from", "style_to", "note", "carried_into", "pending_suggestion", "source_text"])
        for para in source.paras():
            d = dispositions[para.id]
            record = style_changes.get(para.id)
            suggestion = "deletion" if para.fully_deleted else "insertion" if para.fully_inserted else "mixed" if para.has_change else ""
            text = para.text("raw" if para.fully_deleted else view)
            writer.writerow([
                para.id, d.disposition, d.section, para.style or "Normal",
                (record.style_to if record and record.style_to else ""), d.note, d.carried_into, suggestion, text,
            ])


def write_generated(result: dict[str, Any], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "role", "text", "value_source_or_note"])
        for item in result["generated"]:
            writer.writerow([item["section"], item["role"], item["text"], item["note"]])


def write_ledger_json(result: dict[str, Any], path: Path) -> None:
    """The ledger as a versioned sidecar, so a consumer can ingest it without parsing CSV."""
    source: Document = result["doc"]
    view = result["normalizer"].view
    rows = []
    for para in source.paras():
        d = result["dispositions"][para.id]
        rows.append({"source_id": para.id, "disposition": d.disposition, "section": d.section, "note": d.note,
                     "carried_into": d.carried_into, "source_style": para.style or "Normal",
                     "text_sha256": __import__("hashlib").sha256(para.text(view).encode("utf-8")).hexdigest()})
    payload = {
        "schema": "blueprint_packager.paragraph_ledger/0.1",
        "source": {"source_name": source.path.name,
                   "transport_fingerprint": {"algorithm": "sha256", "digest": source.sha256, "scope": "transport_file", "bytes": source.path.stat().st_size}},
        "suggestion_view": view,
        "rows": rows,
        "generated_structure_lines": result["generated"],
        "authorized_additions": result.get("additions", []),
        "authorized_edits": result.get("edits", []),
    }
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
