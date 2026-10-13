#!/usr/bin/env python3
"""Blueprint Packager command line (working title).

    bpk.py ingest     SOURCE.docx --out stream.json
    bpk.py normalize  SOURCE.docx --map course_map.json --output-dir DIR [--label STEM]
    bpk.py read       NORMALIZED.docx --output-dir DIR [--label STEM]
    bpk.py build      MODEL.json --settings build_settings.json --output-dir DIR [--force]
    bpk.py rebase-map OLD.docx NEW.docx --map MAP.json --output NEW_MAP.json
    bpk.py verify     BUILD_DIR --model MODEL.json [--workbench-scripts DIR --label NAME]

Exit codes: 0 success; 1 the step ran and found errors or a failed check;
2 usage, environment, or course-map refusal; 130 interrupted.

Nothing here imports into Brightspace. A built package is a local artifact
until an operator imports it and records the result.

Run with the repo's virtual environment, from the repo root.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blueprint_packager import __version__  # noqa: E402
from blueprint_packager.docx_ingest import read_docx  # noqa: E402


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_ingest(args: argparse.Namespace) -> int:
    doc = read_docx(args.source)
    _write_json(Path(args.out), doc.to_dict(args.view))
    print(f"stream: {args.out}")
    return 0


def cmd_blank(args: argparse.Namespace) -> int:
    from blueprint_packager.blank import write_blank

    out = write_blank(Path(args.output), course_number=args.course_number, course_title=args.course_title, term=args.term,
                      weeks=args.weeks, topics=args.topic, assignments_per_week=args.assignments_per_week,
                      discussions_per_week=args.discussions_per_week, week_counts=_week_counts(args.week_count),
                      worked_example=args.worked_example, force=args.force)
    print(f"blank blueprint: {out} ({args.weeks} weeks)")
    return 0


def _week_counts(values: list[str]) -> dict[int, dict[str, int]]:
    result = {}
    for value in values:
        try:
            week, assignments, discussions = map(int, value.split(":"))
        except ValueError as exc:
            raise ValueError("Use --week-count WEEK:ASSIGNMENTS:DISCUSSIONS, for example 2:2:3") from exc
        if week in result:
            raise ValueError(f"Week {week} has two count overrides.")
        result[week] = {"assignments": assignments, "discussions": discussions}
    return result


def cmd_from_wizard(args: argparse.Namespace) -> int:
    from blueprint_packager.wizard_authoring import convert_bundle

    result = convert_bundle(Path(args.bundle), Path(args.output), force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["status"] == "converted" else 1


def cmd_rename(args: argparse.Namespace) -> int:
    from blueprint_packager.relationships import rename_activity
    result = rename_activity(Path(args.source), Path(args.output), kind=args.kind, old=args.old, new=args.new,
                             apply=args.apply, authorized_by=args.authorized_by or "", reason=args.reason or "")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if any(d.get("severity") == "error" for d in result.get("diagnostics", [])) else 0


REMEDIATION = {
    "TITLE_DIFFERS_FROM_BODY_HEADING": "Decide which wording is the activity's name and make the points table and the activity heading agree.",
    "RUBRIC_UNATTACHED": "Attach the rubric to an activity with a 'Used by:' line and a matching 'Rubric:' line, or move it under Retired Rubrics.",
    "CHECKLIST_ITEM_STALE": "Update or remove the checklist item in the blueprint.",
    "CHECKLIST_EMPTY": "Add checklist items in the blueprint, or accept that no checklist is built for this week.",
    "GRADED_WITHOUT_RUBRIC": "Name a rubric for the activity or confirm it is graded without one.",
}
STATUS_QUALITY = {"resolved": "resolved_endpoints", "none": "evidence_only", "unattached": "evidence_only"}


def _read_and_resolve(docx: Path, out_dir: Path, stem: str) -> tuple[dict, dict]:
    from blueprint_packager import identity as I
    from blueprint_packager.joins import resolve
    from blueprint_packager.reader import read_model
    from blueprint_packager.render_text import model_markdown

    model = read_model(docx)
    resolved = resolve(model)
    model["joins"] = [
        {**join, "relationship_key": I.scoped_key("relationship", join["from"], join["kind"], join["to"]),
         "identity": {"quality": STATUS_QUALITY.get(join["status"], "partial_endpoints"), "basis": "title"}}
        for join in resolved["joins"]
    ]
    raw = model["diagnostics"] + resolved["diagnostics"]
    model["diagnostics"] = [
        I.diagnostic(index, d["code"], d["severity"], d["message"], d.get("where", ""), REMEDIATION.get(d["code"], ""))
        for index, d in enumerate(raw, start=1)
    ]
    model["provenance"] = "authored"
    from blueprint_packager.authoring import readiness
    from blueprint_packager.relationships import relationship_report
    model["readiness"] = readiness(model)
    _write_json(out_dir / f"{stem}__course_model.json", model)
    _write_json(out_dir / f"{stem}__readiness.json", model["readiness"])
    _write_json(out_dir / f"{stem}__source_accounting.json", model["source_accounting"])
    _write_json(out_dir / f"{stem}__relationships.json", relationship_report(model))
    (out_dir / f"{stem}__normalized.md").write_text(model_markdown(model), encoding="utf-8")
    return model, resolved


def _summarize(model: dict) -> int:
    errors = [d for d in model["diagnostics"] if d["severity"] == "error"]
    warnings = [d for d in model["diagnostics"] if d["severity"] == "warning"]
    infos = [d for d in model["diagnostics"] if d["severity"] == "info"]
    print(f"model: {len(model['weeks'])} weeks, {len(model['pages'])} course pages, {len(model['rubrics'])} rubrics, "
          f"{len(model['joins'])} joins; {len(errors)} errors, {len(warnings)} warnings, {len(infos)} notes")
    for d in errors:
        print(f"  ERROR {d['code']}: {d['message']} [{d['location']}]")
    ready = model.get("readiness", {})
    print(f"authoring: {ready.get('state', 'not checked')}; {sum(f.get('status') == 'unresolved' for f in ready.get('findings', []))} unresolved authoring items")
    return 1 if errors else 0


def _receipt(out_dir: Path, stem: str, source_path: Path, started: str, steps: list, parameters: dict, contracts: dict, diagnostics: list, lineage: tuple[str, str]) -> None:
    from blueprint_packager import identity as I

    name = f"{stem}__run_identity.json"
    receipt = I.run_receipt(
        run_id=I.new_run_id(), source=I.document_source(source_path, *lineage), bundle_dir=out_dir, receipt_name=name,
        started_at=started, steps=steps, parameters=parameters, contract_by_name=contracts, diagnostics=diagnostics,
        repo_root=Path(__file__).resolve().parent, version=__version__)
    _write_json(out_dir / name, receipt)


def cmd_normalize(args: argparse.Namespace) -> int:
    from blueprint_packager import identity as I
    from blueprint_packager.fidelity import prove, write_generated, write_ledger, write_ledger_json
    from blueprint_packager.normalize import MapError, normalize

    started = I.utc_now()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or Path(args.source).stem
    out_docx = out_dir / f"{stem}__normalized.docx"
    try:
        result = normalize(Path(args.source), Path(args.map), out_docx)
    except MapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = prove(result, out_docx)
    _write_json(out_dir / f"{stem}__fidelity_report.json", report)
    write_ledger(result, out_dir / f"{stem}__normalization_ledger.csv")
    write_ledger_json(result, out_dir / f"{stem}__paragraph_ledger.json")
    write_generated(result, out_dir / f"{stem}__generated_structure_lines.csv")
    print(f"normalized: {out_docx}")
    for check in report["checks"]:
        print(f"  [{'pass' if check['passed'] else 'FAIL'}] {check['check']}: {check['detail']}")
    model, _ = _read_and_resolve(out_docx, out_dir, stem)
    status = _summarize(model)
    steps = [{"name": "normalize", "status": "completed"},
             {"name": "fidelity proof", "status": "completed" if report["passed"] else "failed"},
             {"name": "read normalized blueprint", "status": "completed" if status == 0 else "unresolved"}]
    _receipt(out_dir, stem, Path(args.source), started, steps,
             {"course_map": Path(args.map).name, "course_map_sha256": I.sha256_file(Path(args.map)), "suggestion_view": report["source"]["view"]},
             {f"{stem}__course_model.json": "blueprint_packager.course_model/0.1", f"{stem}__fidelity_report.json": "blueprint_packager.fidelity/1",
              f"{stem}__paragraph_ledger.json": "blueprint_packager.paragraph_ledger/0.1"},
             [d for d in model["diagnostics"] if d["severity"] != "info"], ("document", Path(args.source).name))
    return status if report["passed"] else 1


def cmd_read(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    stem = args.name or Path(args.source).stem
    model, _ = _read_and_resolve(Path(args.source), out_dir, stem)
    return _summarize(model)


def cmd_build(args: argparse.Namespace) -> int:
    from blueprint_packager.build import build_package

    from blueprint_packager import identity as I

    started = I.utc_now()
    model = json.loads(Path(args.model).read_text(encoding="utf-8"))
    settings = json.loads(Path(args.settings).read_text(encoding="utf-8"))
    if args.preview:
        settings["build_mode"] = "preview"
    if args.retain_video_placeholder:
        settings["retain_video_placeholders"] = args.retain_video_placeholder
    if args.video_link_fallback:
        settings["video_link_fallbacks"] = args.video_link_fallback
    status = build_package(model, settings, Path(args.out_dir), settings_dir=Path(args.settings).resolve().parent, force=args.force)
    if status in (0, 1):
        lineage = settings.get("lineage", {})
        _receipt(Path(args.out_dir), "build", Path(args.model), started,
                 [{"name": "plan", "status": "completed"}, {"name": "render pages", "status": "completed"},
                  {"name": "write package", "status": "completed" if status == 0 else "unresolved"}],
                 {"settings": Path(args.settings).name, "settings_sha256": I.sha256_file(Path(args.settings)),
                  "template": settings.get("template"), "base_resource_code": settings["package"]["base_resource_code"]},
                 {"component_package_receipt.json": "coursecraft.component_package_receipt/1",
                  "object_map.json": "blueprint_packager.object_map/0.1"},
                 [], (lineage.get("basis", "course"), lineage.get("value", settings["package"]["title"])))
    return status


def cmd_rebase_map(args: argparse.Namespace) -> int:
    from blueprint_packager import rebase
    from blueprint_packager.docx_ingest import read_docx

    old, new = read_docx(args.old_source), read_docx(args.new_source)
    course_map = json.loads(Path(args.map).read_text(encoding="utf-8"))
    bound = course_map.get("source", {}).get("sha256")
    if bound and bound != old.sha256:
        print(f"error: the map is bound to {bound[:12]}, not to {Path(args.old_source).name} ({old.sha256[:12]})", file=sys.stderr)
        return 2
    alignment = rebase.align(old, new)
    rebased, problems = rebase.rebase_map(course_map, alignment, new, old)
    rep = rebase.report(alignment, problems, old, new)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rebased, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path = Path(args.report) if args.report else out.with_name(out.stem + "__rebase_report.json")
    report_path.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.with_suffix(".md").write_text(rebase.report_markdown(rep), encoding="utf-8")
    c = rep["counts"]
    print(f"rebased map: {out}")
    print(f"  {c['carried']} paragraphs carried, {c['edited_in_place']} edited in place, {c['added']} added, {c['removed']} removed, "
          f"{c['suggestions_resolved']} suggestions resolved; ids {'unchanged' if rep['ids_unchanged'] else 'translated'}")
    blocking = [p for p in problems if p.get("severity") != "note"]
    for problem in problems:
        print(f"  [{'note' if problem.get('severity') == 'note' else 'look'}] {problem['where']}: {problem['id']} {problem['problem']}")
    return 1 if blocking else 0


def cmd_verify(args: argparse.Namespace) -> int:
    from blueprint_packager.verify import verify_build

    model = json.loads(Path(args.model).read_text(encoding="utf-8"))
    scripts = Path(args.workbench_scripts) if args.workbench_scripts else None
    return verify_build(Path(args.build_dir), model, workbench_scripts=scripts, label=args.label)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"blueprint-packager {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="dump a DOCX as a paragraph stream")
    p.add_argument("source")
    p.add_argument("--out", required=True)
    p.add_argument("--view", default="proposed", choices=["proposed", "base", "raw"])
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("blank", help="write a blank blueprint in the current convention, ready to fill in")
    p.add_argument("output")
    p.add_argument("--course-number", required=True)
    p.add_argument("--course-title", required=True)
    p.add_argument("--term", required=True)
    p.add_argument("--weeks", type=int, default=8)
    p.add_argument("--topic", action="append", default=[], help="a week's topic, in order; repeatable")
    p.add_argument("--assignments-per-week", type=int, default=1)
    p.add_argument("--discussions-per-week", type=int, default=1)
    p.add_argument("--week-count", action="append", default=[], help="override one week: WEEK:ASSIGNMENTS:DISCUSSIONS")
    p.add_argument("--worked-example", action="store_true", help="include sample panels and sample rubrics")
    p.add_argument("--force", action="store_true", help="back up an existing DOCX before replacing it")
    p.set_defaults(func=cmd_blank)

    p = sub.add_parser("from-wizard", help="convert an immutable Wizard extraction bundle into an authoring DOCX")
    p.add_argument("bundle")
    p.add_argument("--output", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_from_wizard)

    p = sub.add_parser("rename", help="preview an exact activity rename and its structural references; --apply writes an authorized copy")
    p.add_argument("source")
    p.add_argument("--output", required=True)
    p.add_argument("--kind", required=True, choices=["assignment", "discussion", "quiz"])
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--authorized-by")
    p.add_argument("--reason")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("normalize", help="apply a course map and write the normalized blueprint")
    p.add_argument("source")
    p.add_argument("--map", required=True)
    p.add_argument("--output-dir", "--out-dir", dest="out_dir", required=True)
    p.add_argument("--label", "--name", dest="name")
    p.set_defaults(func=cmd_normalize)

    p = sub.add_parser("read", help="read a normalized blueprint into a course model")
    p.add_argument("source")
    p.add_argument("--output-dir", "--out-dir", dest="out_dir", required=True)
    p.add_argument("--label", "--name", dest="name")
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("build", help="build a Brightspace package from a course model")
    p.add_argument("model")
    p.add_argument("--settings", required=True)
    p.add_argument("--output-dir", "--out-dir", dest="out_dir", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--preview", action="store_true", help="explicitly build a draft preview with unresolved authoring fields")
    p.add_argument("--retain-video-placeholder", action="append", default=[], metavar="TITLE")
    p.add_argument("--video-link-fallback", action="append", default=[], metavar="TITLE")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("rebase-map", help="carry a course map from one export of a blueprint to a later export")
    p.add_argument("old_source")
    p.add_argument("new_source")
    p.add_argument("--map", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report")
    p.set_defaults(func=cmd_rebase_map)

    p = sub.add_parser("verify", help="read a built package back and compare it with the course model")
    p.add_argument("build_dir")
    p.add_argument("--model", required=True)
    p.add_argument("--workbench-scripts", help="read the package with another Workbench checkout's scripts (second opinion)")
    p.add_argument("--label", help="suffix for the second-opinion report and read-back folder")
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
