"""Synthetic closed-cycle and failure cases for the explicit Wizard adapter."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import synth

from blueprint_packager.build import Builder
from blueprint_packager.joins import resolve
from blueprint_packager.reader import read_model
from blueprint_packager import workbench as WB
from blueprint_packager.wizard_authoring import convert_bundle

SETTINGS = {
    "schema": "blueprint_packager.build_settings/0.1",
    "package": {"title": "SYN 101 conversion test", "manifest_identifier": "D2L_SYN101",
                "base_resource_code": "00000000-0000-4000-8000-000000000101"},
    "template": "bumk515-classic",
    "forum_order": ["Community Forum", "Discussions"],
}


def joined(path):
    model = read_model(path)
    result = resolve(model)
    model["joins"] = result["joins"]
    model["diagnostics"].extend(result["diagnostics"])
    return model


def extract(package, directory):
    command = [sys.executable, "-B", str(WB.scripts_dir() / "build_blueprint_bundle.py"), str(package),
               "--label", "synthetic", "--output-dir", str(directory), "--no-docx", "--no-syllabus-fetch", "--quiet"]
    process = subprocess.run(command, capture_output=True, text=True,
                             env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert process.returncode == 0, process.stdout + process.stderr
    return directory / "synthetic__blueprint_bundle"


@pytest.fixture(scope="module")
def cycle(tmp_path_factory):
    root = tmp_path_factory.mktemp("wizard-cycle")
    model = joined(synth.canonical(root / "source.docx"))
    week = model["weeks"][0]
    for key, kind in (("assignments", "Assignment"), ("discussions", "Discussion")):
        activity = copy.deepcopy(week[key][0])
        activity["title"] = activity["grade_item"] = f"Week 1 {kind}: Second task"
        activity["points"] = 20.
        activity["blocks"] = [{"kind": "p", "runs": [{"text": f"Complete the second synthetic {kind.lower()}."}]}]
        week[key].append(activity)
        model["grade_plan"]["items"].append({"name": activity["title"], "points": 20.})
        rubric = next(r for r in model["rubrics"] if r["name"] == activity["rubric"])
        rubric["used_by"].append(f"{kind}: {activity['title']}")
    model["grade_plan"].update(total_stated=140., total_computed=140.)
    week["overview_page"]["blocks"].extend([
        {"kind": "video", "title": "Synthetic overview video", "href": "https://www.youtube.com/embed/synthetic01"},
        {"kind": "p", "runs": [{"text": "A bold phrase", "b": True}, {"text": " and "},
                                 {"text": "an italic phrase", "i": True},
                                 {"text": " with a reference.", "href": "https://example.org/reference"}]},
        {"kind": "p", "runs": [{"text": "Read [link to assignment: Week 1 Assignment: Report | the report task]."}]},
        {"kind": "p", "runs": [{"text": "Return to [link to page: Welcome to SYN 101 | the welcome page]."}]},
    ])
    joins = resolve(model)
    model["joins"] = joins["joins"]
    model["diagnostics"] = joins["diagnostics"]
    assert not [d for d in model["diagnostics"] if d["severity"] == "error"]
    built = Builder(model, SETTINGS, WB.REPO_DIR).run(root / "first-build", force=False)
    assert not built["errors"]
    bundle = extract(built["zip"], root / "first-extraction")
    return root, model, bundle


def semantic(blocks):
    """Compare authored text/structure, excluding extraction-only style evidence."""
    result = []
    for block in blocks:
        kind = block["kind"]
        entry = {"kind": kind}
        for key in ("title", "cue", "href", "level", "ordered"):
            if key in block:
                entry[key] = block[key]
        if "runs" in block:
            entry["runs"] = [{k: v for k, v in r.items() if k != "b" or kind != "heading"} for r in block["runs"]]
        if "blocks" in block:
            entry["blocks"] = semantic(block["blocks"])
        result.append(entry)
    return result


def test_closed_cycle_preserves_multiple_activities_media_and_joins(cycle):
    root, source, bundle = cycle
    before_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.glob("*.json")}
    output = root / "returned.docx"
    report = convert_bundle(bundle, output)
    assert report["status"] == "converted", report["diagnostics"]
    returned = joined(output)
    assert not [d for d in returned["diagnostics"] if d["severity"] == "error"]
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.glob("*.json")} == before_hashes
    assert len(report["sources"]) == 4
    assert all(len(s["sha256"]) == 64 for s in report["sources"])
    assert returned["grade_plan"]["items"] == source["grade_plan"]["items"]
    assert returned["grade_plan"]["total_computed"] == 140
    for key in ("pages", "modules", "links", "course_activities"):
        assert [(o["type"], o["title"], o.get("placement"), o.get("visibility")) for o in returned[key]] == [
            (o["type"], o["title"], o.get("placement"), o.get("visibility")) for o in source[key]]
    a, b = source["weeks"][0], returned["weeks"][0]
    assert (a["title"], a["overview_page"]["title"], a["overview_page"]["page_heading"]) == (
        b["title"], b["overview_page"]["title"], b["overview_page"]["page_heading"])
    assert semantic(a["overview_page"]["blocks"]) == semantic(b["overview_page"]["blocks"])
    assert semantic(a["objectives"]) == semantic(b["objectives"])
    assert semantic(a["resources"]) == semantic(b["resources"])
    for key in ("assignments", "discussions"):
        assert len(b[key]) == 2
        for left, right in zip(a[key], b[key]):
            for attr in ("title", "points", "grade_item", "rubric", "forum"):
                assert left.get(attr) == right.get(attr)
            assert semantic(left["blocks"]) == semantic(right["blocks"])
    assert [[r["text"] for r in item["runs"]] for item in a["checklist"]["items"]] == [
        [r["text"] for r in item["runs"]] for item in b["checklist"]["items"]]
    for left, right in zip(source["rubrics"], returned["rubrics"]):
        assert left["name"] == right["name"]
        assert left["used_by"] == right["used_by"]
        assert [(c["name"], c["weight"], semantic(c["cells"][0])) for c in left["grid"]["criteria"]] == [
            (c["name"], c["weight"], semantic(c["cells"][0])) for c in right["grid"]["criteria"]]
    rebuilt = Builder(returned, SETTINGS, WB.REPO_DIR).run(root / "second-build", force=False)
    assert not rebuilt["errors"]
    second_bundle = extract(rebuilt["zip"], root / "second-extraction")
    # Extracted HTML content and object payloads should be stable through the
    # second generation even though source-file provenance comments differ.
    for suffix in ("__blueprint.json", "__rubrics.json"):
        first = json.loads(next(bundle.glob("*" + suffix)).read_text())
        second = json.loads(next(second_bundle.glob("*" + suffix)).read_text())
        if suffix == "__blueprint.json":
            for key in ("front_matter", "before_week_1", "weeks", "unplaced_activities"):
                assert first[key] == second[key]
        else:
            assert first["rubrics"] == second["rubrics"]


def mutate_bundle(cycle, tmp_path, role, change):
    import shutil
    source = cycle[2]
    copied = tmp_path / "bundle"
    shutil.copytree(source, copied)
    suffix = {"blueprint": "__blueprint.json", "activities": "__course_activities.json",
              "structure": "__course_structure.json", "rubrics": "__rubrics.json"}[role]
    path = next(copied.glob("*" + suffix))
    payload = json.loads(path.read_text())
    change(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return copied


@pytest.mark.parametrize(("role", "change", "code"), [
    ("activities", lambda x: x["dropbox_folders"][0].update(date_due="2026-10-09T23:59:00Z"), "ACTIVITY_SETTINGS_UNSUPPORTED"),
    ("activities", lambda x: x["dropbox_folders"][0].update(grade_item_code="missing"), "GRADE_JOIN_UNRESOLVED"),
    ("activities", lambda x: x["dropbox_folders"][0]["instructions_blocks"].append({"kind": "practice", "runs": [{"text": "Practice"}]}), "BLOCK_UNSUPPORTED"),
    ("structure", lambda x: x.update(run_id="different-extraction"), "BUNDLE_RUN_MISMATCH"),
    ("structure", lambda x: x["tree"][-1].update(is_hidden=True), "WEEK_VISIBILITY_UNSUPPORTED"),
    ("structure", lambda x: x["tree"][-1]["children"][-1].update(title="Different manifest title"), "MANIFEST_TITLE_DIFFERS"),
    ("rubrics", lambda x: x["rubrics"][0]["criteria"][0]["cells"][0].update(points=99), "RUBRIC_SCORE_UNREPRESENTABLE"),
    ("blueprint", lambda x: x["front_matter"]["course_introduction"].append({"kind": "p", "runs": [{"text": "Unaccounted authored passage."}]}), "BLUEPRINT_CONTENT_UNACCOUNTED"),
])
def test_unsupported_or_inconsistent_evidence_blocks_conversion(cycle, tmp_path, role, change, code):
    bundle = mutate_bundle(cycle, tmp_path, role, change)
    output = tmp_path / "blocked.docx"
    result = convert_bundle(bundle, output)
    assert result["status"] == "blocked"
    assert code in {d["code"] for d in result["diagnostics"]}
    assert not output.exists()
    assert output.with_suffix(".conversion.json").is_file()


def test_refuses_overwrite_and_writes_outside_evidence(cycle, tmp_path):
    output = tmp_path / "authored.docx"
    output.write_bytes(b"Existing authored document")
    with pytest.raises(FileExistsError):
        convert_bundle(cycle[2], output)
    assert output.read_bytes() == b"Existing authored document"
    with pytest.raises(ValueError, match="immutable"):
        convert_bundle(cycle[2], cycle[2] / "output.docx")


def test_missing_or_unknown_contracts_produce_reviewable_diagnostics(cycle, tmp_path):
    bundle = mutate_bundle(cycle, tmp_path, "blueprint", lambda x: x.update(schema="coursecraft.blueprint/999"))
    result = convert_bundle(bundle, tmp_path / "unknown.docx")
    assert result["status"] == "blocked"
    assert result["diagnostics"][0]["code"] == "BUNDLE_SCHEMA"
    missing = tmp_path / "empty"; missing.mkdir()
    result = convert_bundle(missing, tmp_path / "missing.docx")
    assert len(result["diagnostics"]) == 4


def test_extracted_explicit_callout_tone_is_carried_into_authoring(cycle, tmp_path):
    def add_tone(payload):
        block = next(b for b in payload["weeks"][0]["overview"] if b["kind"] == "visual")
        block["meta"]["tone"] = "gold"
    bundle = mutate_bundle(cycle, tmp_path, "blueprint", add_tone)
    output = tmp_path / "tone.docx"
    result = convert_bundle(bundle, output)
    assert result["status"] == "converted", result["diagnostics"]
    blocks = read_model(output)["weeks"][0]["overview_page"]["blocks"]
    assert next(b for b in blocks if b["kind"] == "visual")["attrs"] == {"tone": "gold"}


def test_no_rubric_package_converts_using_explicit_inventory_evidence(cycle, tmp_path):
    model = copy.deepcopy(cycle[1])
    model["rubrics"] = []
    for week in model["weeks"]:
        for key in ("assignments", "discussions"):
            for activity in week[key]:
                activity.pop("rubric", None)
    resolved = resolve(model)
    model["joins"], model["diagnostics"] = resolved["joins"], resolved["diagnostics"]
    first = Builder(model, SETTINGS, WB.REPO_DIR).run(tmp_path / "without-rubric", force=False)
    bundle = extract(first["zip"], tmp_path / "extraction")
    assert not list(bundle.glob("*__rubrics.json"))
    output = tmp_path / "no-rubric.docx"
    result = convert_bundle(bundle, output)
    assert result["status"] == "converted", result["diagnostics"]
    assert any(s["role"] == "inventory" and s["sha256"] for s in result["sources"])
    assert any(e["source"] == "rubrics" and e["disposition"] == "not_applicable" for e in result["ledger"])
    returned = joined(output)
    assert returned["rubrics"] == []
    rebuilt = Builder(returned, SETTINGS, WB.REPO_DIR).run(tmp_path / "rebuilt", force=False)
    assert not rebuilt["errors"]
    second = extract(rebuilt["zip"], tmp_path / "second-extraction")
    assert not list(second.glob("*__rubrics.json"))
    assert json.loads(next(bundle.glob("*__blueprint.json")).read_text())["weeks"] == json.loads(
        next(second.glob("*__blueprint.json")).read_text())["weeks"]


def test_absent_rubric_contract_with_existing_payload_is_an_error(cycle, tmp_path):
    import shutil
    bundle = tmp_path / "bundle"
    shutil.copytree(cycle[2], bundle)
    next(bundle.glob("*__rubrics.json")).unlink()
    result = convert_bundle(bundle, tmp_path / "missing-rubric.docx")
    assert result["status"] == "blocked"
    assert "RUBRIC_CONTRACT_MISSING" in {d["code"] for d in result["diagnostics"]}


@pytest.mark.parametrize("conflict", ["document", "ledger"])
def test_exclusive_publication_preserves_a_concurrent_file(cycle, tmp_path, monkeypatch, conflict):
    from blueprint_packager import wizard_authoring as adapter
    output = tmp_path / "concurrent.docx"
    ledger = output.with_suffix(".conversion.json")
    target = output if conflict == "document" else ledger
    real_link = adapter.os.link
    def concurrent_link(source, destination):
        if Path(destination) == target:
            target.write_bytes(b"Another writer's completed artifact")
        return real_link(source, destination)
    monkeypatch.setattr(adapter.os, "link", concurrent_link)
    with pytest.raises(FileExistsError):
        convert_bundle(cycle[2], output)
    assert target.read_bytes() == b"Another writer's completed artifact"
    assert not (ledger if conflict == "document" else output).exists()
    assert not list(tmp_path.glob(".wizard-*"))
