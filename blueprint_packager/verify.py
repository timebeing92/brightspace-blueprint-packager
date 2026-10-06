"""Pre-import verification of a built package (evidence level L1).

Three independent readers look at the package:

1. the Workbench conformance gate (manifest shape D2L will accept);
2. the Workbench activity and structure extractors (every join traced);
3. Blueprint Wizard's own export-to-blueprint pipeline, run on the package as
   if it were a course export. Whatever the wizard reads back is compared with
   the course model the package was built from.

None of this is import evidence. It shows the package says what the model
says, in a shape the ecosystem's own readers understand.

The readers are run from a Workbench ``scripts`` folder: this repository's by
default, or another checkout named with ``--workbench-scripts`` for a second
opinion. Child processes are told not to write bytecode, so reading another
checkout leaves nothing behind in it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

from .build import _find_repo_root
from .joins import TYPE_LABEL
from .render_text import plain


def squash(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace(" ", " ")
    return re.sub(r"\s+", "", text)


def paragraphs(blocks: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for block in blocks:
        if block.get("runs"):
            text = plain(block["runs"])
            if text:
                out.append(text)
        if block["kind"] == "dropdown":
            out.append(block["title"])
        if block["kind"] in ("dropdown", "visual"):
            out.extend(paragraphs(block["blocks"]))
        if block["kind"] == "table":
            for row in block["rows"]:
                for cell in row:
                    out.extend(paragraphs(cell))
    return out


def _reader_identity(scripts: Path) -> dict[str, Any]:
    """Which reader code looked at the package: commit when known, file hashes always."""
    identity: dict[str, Any] = {"checkout": scripts.parent.name, "files": {}}
    for name in ("check_package_conformance.py", "build_blueprint_bundle.py", "reconstruct_course_structure.py",
                 "extract_course_activities.py", "extract_rubrics_to_workbook.py"):
        path = scripts / name
        if path.is_file():
            identity["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        commit = subprocess.run(["git", "-C", str(scripts.parent), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, check=False)
        if commit.returncode == 0:
            identity["commit"] = commit.stdout.strip()
    except OSError:
        pass
    return identity


def verify_build(build_dir: Path, model: dict[str, Any], workbench_scripts: Path | None = None,
                 label: str | None = None) -> int:
    build_dir = build_dir.resolve()
    if workbench_scripts is not None:
        scripts = Path(workbench_scripts).expanduser().resolve()
        if not (scripts / "build_blueprint_bundle.py").is_file():
            raise FileNotFoundError(f"No build_blueprint_bundle.py in {scripts}")
        label = label or "second_opinion"
    else:
        repo_root = _find_repo_root(build_dir) if (build_dir / "scripts").exists() else _find_repo_root(Path(__file__).resolve())
        scripts = repo_root / "scripts"
    suffix = f"__{re.sub(r'[^A-Za-z0-9_-]+', '_', label)}" if label else ""
    child_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    package_dir = build_dir / "package"
    object_map = json.loads((build_dir / "object_map.json").read_text(encoding="utf-8"))
    receipt = json.loads((build_dir / "component_package_receipt.json").read_text(encoding="utf-8"))
    zip_path = build_dir / receipt["zip"]["path"]
    settings_restorations = [n for n in object_map.get("notes", [])]
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    # 1. conformance gate
    result = subprocess.run([sys.executable, "-B", str(scripts / "check_package_conformance.py"), str(package_dir)],
                            capture_output=True, text=True, check=False, env=child_env)
    check("Workbench conformance gate", result.returncode == 0 and "RESULT: CONFORMANT" in result.stdout,
          " ".join(line.strip("- ") for line in result.stdout.splitlines() if "Errors" in line or "Warnings" in line or "RESULT" in line))

    # 2+3. wizard pipeline on the package
    readback_root = build_dir / f"verification{suffix}"
    if readback_root.exists():
        shutil.rmtree(readback_root)
    result = subprocess.run(
        [sys.executable, "-B", str(scripts / "build_blueprint_bundle.py"), str(zip_path), "--label", "readback",
         "--output-dir", str(readback_root), "--no-docx", "--no-syllabus-fetch", "--quiet"],
        capture_output=True, text=True, check=False, env=child_env)
    bundle = readback_root / "readback__blueprint_bundle"
    check("Blueprint Wizard pipeline reads the package", result.returncode == 0 and bundle.is_dir(),
          f"exit {result.returncode}" + (f"; {result.stderr.strip()[-200:]}" if result.returncode else ""))
    if not bundle.is_dir():
        return _finish(build_dir, checks, suffix, _reader_identity(scripts))
    activities = json.loads((bundle / "readback__course_activities.json").read_text(encoding="utf-8"))
    structure = json.loads((bundle / "readback__course_structure.json").read_text(encoding="utf-8"))
    rubrics_back = json.loads((bundle / "readback__rubrics.json").read_text(encoding="utf-8")) if (bundle / "readback__rubrics.json").exists() else {"rubrics": []}
    qa = json.loads((bundle / "readback__course_qa.json").read_text(encoding="utf-8")) if (bundle / "readback__course_qa.json").exists() else {}

    # joins traced by the extractor
    states = [str(j.get("resolved", "")).lower() for j in activities.get("joins", [])]
    unresolved = [state for state in states if state not in ("yes", "true", "none")]
    unlinked = states.count("none")  # an activity with no module link, e.g. a course-wide forum topic
    check("every join in the package resolves", not unresolved and not activities.get("diagnostics"),
          f"{len(states)} join edges traced, {len(unresolved)} unresolved, {unlinked} activities with no module link by design, "
          f"{len(activities.get('diagnostics', []))} extractor diagnostics")

    # module tree
    planned = [(m["module"], m["hidden"], [(i["title"], i["hidden"]) for i in m["items"]]) for m in object_map["structure"]]
    hidden = lambda node: str(node.get("is_hidden", "")).lower() in ("true", "1", "yes")
    read = [(n["title"], hidden(n), [(c["title"], hidden(c)) for c in n.get("children", [])]) for n in structure["tree"]]
    check("module tree read back equals the planned tree", planned == read,
          f"{len(planned)} modules and {sum(len(m[2]) for m in planned)} topics planned; {len(read)} modules and {sum(len(m[2]) for m in read)} topics read back")

    # activities and their joins
    back: dict[tuple[str, str], dict[str, Any]] = {}
    for row in activities.get("dropbox_folders", []):
        back[("assignment", row["name"])] = row
    for row in activities.get("discussions", []):
        if row.get("kind") == "topic":
            back[("discussion", row["title"])] = row
    for row in activities.get("quizzes", []):
        back[("quiz", row["title"])] = row
    # points-table row -> the name the build gave its grade item
    built_name = {o["points_table_row"]: o["title"] for o in object_map["objects"] if o["kind"] == "grade_item" and o.get("points_table_row")}
    planned_points = {(o["kind"], o["title"]): o["points"] for o in object_map["objects"]
                      if o["kind"] in ("assignment", "discussion", "quiz") and o.get("points") is not None}
    model_activities = [a for w in model["weeks"] for k in ("assignments", "discussions", "quizzes") for a in w[k]]
    model_activities += [a for a in model["course_activities"] if a["type"] in TYPE_LABEL]
    problems: list[str] = []
    for activity in model_activities:
        row = back.get((activity["type"], activity["title"]))
        label = f"{activity['type']} '{activity['title']}'"
        if row is None:
            problems.append(f"{label} not found")
            continue
        expected_grade = built_name.get(activity.get("grade_item") or "", activity.get("grade_item") or "")
        if expected_grade != (row.get("grade_item_name") or ""):
            problems.append(f"{label}: grade item '{row.get('grade_item_name')}' != '{expected_grade}'")
        points = row.get("out_of") if activity["type"] == "assignment" else row.get("score_out_of") if activity["type"] == "discussion" else row.get("grade_item_out_of")
        expected_points = planned_points.get((activity["type"], activity["title"]), activity.get("points"))
        if expected_points is not None and (points in (None, "") or abs(float(points) - float(expected_points)) > 1e-9):
            problems.append(f"{label}: points {points} != {expected_points}")
        resolved = str(row.get("rubrics_resolved") or "")
        if activity.get("rubric") and activity["rubric"] not in resolved:
            problems.append(f"{label}: rubric '{activity['rubric']}' not attached (read back: '{resolved}')")
        if not activity.get("rubric") and resolved:
            problems.append(f"{label}: unexpected rubric '{resolved}'")
    extra = set(back) - {(a["type"], a["title"]) for a in model_activities}
    if extra:
        problems.append(f"unexpected activities in package: {sorted(extra)}")
    check("every activity reads back with its grade item, points, and rubric", not problems,
          f"{len(model_activities)} activities compared; {len(problems)} problems {problems[:4]}")

    # gradebook
    built_points = {o["points_table_row"]: float(o["points"]) for o in object_map["objects"] if o["kind"] == "grade_item" and o.get("points_table_row")}
    plan = [(built_name.get(i["name"], i["name"]), built_points.get(i["name"], float(i["points"]))) for i in model["grade_plan"]["items"]]
    grades = [(g["name"], float(g["out_of"])) for g in activities.get("grade_items", [])]
    orphans = [g["name"] for g in activities.get("grade_items", []) if not g.get("linked_activities")]
    table_total = sum(float(i["points"]) for i in model["grade_plan"]["items"])
    check("gradebook equals the grading plan", plan == grades and not orphans,
          f"{len(grades)} grade items totalling {sum(p for _, p in grades):g} (points table totals {table_total:g}); "
          f"{len(orphans)} without a linked activity")

    # rubrics
    rubric_problems: list[str] = []
    by_name = {r["name"]: r for r in rubrics_back.get("rubrics", [])}
    built = [r for r in model["rubrics"] if r.get("grid")]
    for rubric in built:
        other = by_name.get(rubric["name"])
        if other is None:
            rubric_problems.append(f"'{rubric['name']}' missing")
            continue
        grid = rubric["grid"]
        if [l["name"] for l in grid["levels"]] != [l["name"] for l in other["levels"]]:
            rubric_problems.append(f"'{rubric['name']}': level names differ")
        if [c["name"] for c in grid["criteria"]] != [c["name"] for c in other["criteria"]]:
            rubric_problems.append(f"'{rubric['name']}': criterion names differ")
            continue
        for criterion, back_criterion in zip(grid["criteria"], other["criteria"]):
            for level, cell, back_cell in zip(grid["levels"], criterion["cells"], back_criterion["cells"]):
                expected = criterion["weight"] * level["percent"] / 100.0
                if abs(float(back_cell["points"]) - expected) > 1e-6:
                    rubric_problems.append(f"'{rubric['name']}' / '{criterion['name']}' / {level['name']}: {back_cell['points']} != {expected:g}")
                if squash(" ".join(paragraphs(cell))) != squash(back_cell.get("description") or ""):
                    rubric_problems.append(f"'{rubric['name']}' / '{criterion['name']}' / {level['name']}: cell text differs")
    check("every rubric reads back with its levels, weights, and cell text", not rubric_problems and len(by_name) == len(built),
          f"{len(built)} rubrics, {sum(len(r['grid']['criteria']) * len(r['grid']['levels']) for r in built)} cells compared; {len(rubric_problems)} problems {rubric_problems[:3]}")

    # authored text survives into the package
    def topic_haystack(topic: dict[str, Any]) -> str:
        # body_text omits a heading when the heading is itself a link, so headings are read from the segments too
        parts = [topic.get("body_text") or ""]
        for segment in topic.get("body_segments") or []:
            parts.append(segment.get("heading") or "")
        return squash(" ".join(parts))

    topic_text = {t["manifest_title"]: topic_haystack(t) for t in structure.get("html_topics", [])}
    removed = [squash(n) for n in _removed_texts(build_dir)]
    missing: list[str] = []
    compared = 0

    def compare(expected: list[str], haystack: str, where: str) -> None:
        nonlocal compared
        for text in expected:
            needle = squash(text)
            for cut in removed:
                needle = needle.replace(cut, "")
            compared += 1
            if needle and needle not in haystack:
                missing.append(f"{where}: {text[:70]}")

    for page in model["pages"]:
        compare(paragraphs(page["blocks"]), topic_text.get(page["title"], ""), page["title"])
    for week in model["weeks"]:
        page = week["overview_page"]
        compare(paragraphs(page["blocks"]) + paragraphs(week["objectives"]) + paragraphs(week["resources"]), topic_text.get(page["title"], ""), page["title"])
    for activity in model_activities:
        row = back.get((activity["type"], activity["title"]), {})
        text = squash(row.get("instructions_text") or row.get("description_text") or "")
        if activity["type"] != "quiz":
            compare(paragraphs(activity["blocks"]), text, f"{activity['type']} {activity['title']}")
    check("every authored paragraph is present in the package as read back", not missing,
          f"{compared} paragraphs compared; {len(missing)} not found {missing[:4]}")

    # checklists
    checklist_back = {c["name"]: [plain(b["runs"]) for b in c.get("blocks", []) if b.get("kind") == "li"] for c in activities.get("checklists", [])}
    checklist_problems = []
    planned_checklists = {o["title"]: o for o in object_map["objects"] if o["kind"] == "checklist"}
    for week in model["weeks"]:
        checklist = week["checklist"]
        if not checklist:
            continue
        planned = planned_checklists.get(checklist["title"])
        # items the build planned: listed in the blueprint, built from the week's activities, or both
        items = planned.get("item_names", []) if planned else [plain(i["runs"]) for i in checklist.get("items", []) if plain(i["runs"])]
        if not items:
            continue
        if [squash(i) for i in items] != [squash(i) for i in checklist_back.get(checklist["title"], [])]:
            checklist_problems.append(checklist["title"])
    check("every checklist reads back with its items", not checklist_problems, f"{len(checklist_back)} checklists; problems {checklist_problems}")

    # dates, read straight from the payload files
    planned_dates = object_map.get("dates") or []
    if planned_dates:
        import xml.etree.ElementTree as ET

        def local(tag: str) -> str:
            return tag.rsplit("}", 1)[-1]

        found: set[tuple[str, str]] = set()
        for row in activities.get("dropbox_folders", []):
            if row.get("date_due"):
                found.add((f"Assignment: {row['name']}", row["date_due"]))
        checklist_file = package_dir / "checklist_d2l.xml"
        if checklist_file.is_file():
            for item in ET.parse(checklist_file).getroot().iter():
                if local(item.tag) == "item":
                    name = next((c.text or "" for c in item if local(c.tag) == "name"), "")
                    end = next((c.text or "" for c in item if local(c.tag) == "date_end"), "")
                    if end:
                        found.add((name, end))
        for quiz_file in sorted(package_dir.glob("quiz_d2l_*.xml")):
            text = quiz_file.read_text(encoding="utf-8-sig")
            stamp = re.search(r"<d2l_2p0:date_due><d2l_2p0:timestamp>(.*?)</d2l_2p0:timestamp></d2l_2p0:date_due>", text, flags=re.S)
            title = re.search(r'<assessment\b[^>]*?\btitle="([^"]*)"', text)
            if stamp and title:
                n = {k: int(v) for k, v in re.findall(r"<d2l_2p0:(\w+)>(\d+)</d2l_2p0:\1>", stamp.group(1))}
                found.add((f"Quiz: {title.group(1)}", f"{n['year']:04d}-{n['month']:02d}-{n['day']:02d}T{n['hour']:02d}:{n['minutes']:02d}:{n['seconds']:02d}.000Z"))
        date_problems = []
        for d in planned_dates:
            if d["kind"].startswith("checklist item"):
                name = d["kind"].split("(", 1)[1].rstrip(")") if "(" in d["kind"] else d["object"].split(": ", 1)[1]
                key = (name, d["utc"])
            else:
                key = (d["object"], d["utc"])
            if key not in found:
                date_problems.append(f"{d['object']} {d['kind']}")
        check("every planned date is in the package", not date_problems,
              f"{len(planned_dates)} dates planned, {len(planned_dates) - len(date_problems)} found; missing {date_problems[:4]}")

    # page gate borrowed from the Workbench page compiler (Page Kit): one h1, alt text, iframe titles,
    # no scripts or inline handlers, matched details/summary. It reads compiled HTML, so it applies as is.
    gate_script = scripts / "check_page_conformance.py"
    pages_dir = package_dir / (json.loads((build_dir / "build_settings.json").read_text(encoding="utf-8")).get("pages_dir", "course_pages"))
    if gate_script.is_file() and pages_dir.is_dir():
        gate_out = readback_root / "page_gate.json"
        result = subprocess.run([sys.executable, "-B", str(gate_script), str(pages_dir), "--mode", "learner", "--json-output", str(gate_out)],
                                capture_output=True, text=True, check=False, env=child_env)
        gate = json.loads(gate_out.read_text(encoding="utf-8")) if gate_out.is_file() else {"diagnostics": [], "files": [], "status": "not written"}
        gate_errors = [d for d in gate["diagnostics"] if d.get("severity") == "error"]
        gate_warnings = [d for d in gate["diagnostics"] if d.get("severity") == "warning"]
        check("Page Kit page gate finds no errors in the pages", result.returncode == 0 and not gate_errors,
              f"{len(gate.get('files', []))} pages; {len(gate_errors)} errors; {len(gate_warnings)} warnings"
              + (": " + "; ".join(f"{d['code']} in {d.get('page_id', '')}" for d in (gate_errors + gate_warnings)[:4]) if gate_errors or gate_warnings else ""))
    else:
        check("Page Kit page gate finds no errors in the pages", True, "not run: this Workbench checkout has no page gate script, or the package has no pages")

    # wizard QA
    summary = qa.get("summary", qa)
    breaks = summary.get("breaks", summary.get("break_count"))
    check("Blueprint Wizard QA finds no breaks", breaks in (0, [], None) or breaks == 0,
          f"breaks: {breaks if not isinstance(breaks, list) else len(breaks)}; broken relative references: "
          f"{sum(len(t.get('missing_refs') or []) for t in structure.get('html_topics', []))}")
    return _finish(build_dir, checks, suffix, _reader_identity(scripts))


def _removed_texts(build_dir: Path) -> list[str]:
    """Wizard link targets that link restoration deliberately removes from visible text."""
    settings_copy = build_dir / "build_settings.json"
    if not settings_copy.exists():
        return []
    settings = json.loads(settings_copy.read_text(encoding="utf-8"))
    return [item["remove_text"] for item in settings.get("link_restorations", []) if item.get("remove_text")]


def _finish(build_dir: Path, checks: list[dict[str, Any]], suffix: str = "", readers: dict[str, Any] | None = None) -> int:
    passed = all(c["passed"] for c in checks)
    report = {
        "schema": "blueprint_packager.verification/0.1",
        "evidence_level": "L1: local build read back by the Workbench extractors and Blueprint Wizard. Nothing was imported.",
        "readers": readers or {},
        "passed": passed,
        "checks": checks,
    }
    (build_dir / f"verification_report{suffix}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    reader_line = ""
    if readers:
        reader_line = f"Readers: Workbench checkout `{readers.get('checkout', '')}`" + (f" at commit `{readers['commit']}`" if readers.get("commit") else "") + "."
    lines = ["# Pre-import verification", "", report["evidence_level"], "", reader_line, "", "| Check | Result | Detail |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['check']} | {'pass' if c['passed'] else 'FAIL'} | {c['detail'].replace('|', '/')} |")
    (build_dir / f"verification_report{suffix}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for c in checks:
        print(f"  [{'pass' if c['passed'] else 'FAIL'}] {c['check']}: {c['detail']}")
    return 0 if passed else 1
