"""Synthetic checks for verification failures that must not become green reports."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import synth
from blueprint_packager import verify as V
from blueprint_packager import workbench as WB
from blueprint_packager.build import Builder
from blueprint_packager.joins import resolve
from blueprint_packager.reader import read_model

SETTINGS = {
    "schema": "blueprint_packager.build_settings/0.1",
    "package": {"title": "Synthetic verification", "manifest_identifier": "D2L_VERIFY",
                "base_resource_code": "00000000-0000-4000-8000-000000000111"},
    "template": "bumk515-classic",
    "forum_order": ["Community Forum", "Discussions"],
}
CHROME = "Page chrome: 1 element(s) with a skip-link or course-label class left out of the blueprint"


def _read(path):
    model = read_model(path)
    joined = resolve(model)
    model["joins"] = joined["joins"]
    model["diagnostics"].extend(joined["diagnostics"])
    return model


def _report(path):
    return json.loads((path / "verification_report.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("qa", [{}, {"summary": {"breaks": []}}, {"summary": {"break_count": 0}}, None])
def test_missing_top_level_qa_breaks_is_not_a_pass(qa):
    check, notes = V._wizard_qa_check(qa, 0)
    assert check["status"] == "not_run" and check["passed"] is False
    assert not notes


def test_only_exact_generated_page_chrome_findings_are_classified():
    check, notes = V._wizard_qa_check({"summary": {"breaks": []}, "breaks": [CHROME]}, 0)
    assert check["passed"] and len(notes) == 1
    check, _ = V._wizard_qa_check({"summary": {"breaks": []}, "breaks": [CHROME, "Authored paragraph lost"]}, 0)
    assert not check["passed"] and "Authored paragraph lost" in check["detail"]
    check, _ = V._wizard_qa_check({"breaks": [CHROME + "; also authored content"]}, 0)
    assert not check["passed"]
    check, _ = V._wizard_qa_check({"breaks": []}, 1)
    assert not check["passed"]


@pytest.mark.parametrize("value", [None, 0, {}, [None]])
def test_malformed_qa_breaks_fail(value):
    check, _ = V._wizard_qa_check({"breaks": value}, 0)
    assert check["status"] == "failed" and not check["passed"]


def test_not_run_is_fatal_but_not_applicable_is_explicit(tmp_path):
    assert V._finish(tmp_path, [V._check_record("No links", False, "none authored", status="not_applicable")]) == 0
    report = _report(tmp_path)
    assert report["passed"] is True
    assert report["checks"][0]["passed"] is False
    assert V._finish(tmp_path, [V._check_record("Missing gate", False, "not available", status="not_run")]) == 1
    assert _report(tmp_path)["passed"] is False
    assert "not_run" in (tmp_path / "verification_report.md").read_text()


def test_vendored_pin_is_not_the_containing_repositories_head(tmp_path):
    scripts = tmp_path / "vendor" / "synthetic_workbench" / "scripts"
    scripts.mkdir(parents=True)
    pin = "abcdef0123456789abcdef0123456789abcdef01"
    (scripts.parent / "MANIFEST.json").write_text(json.dumps({"commit": pin}))
    identity = V._reader_identity(scripts)
    assert identity["commit"] == identity["pinned_commit"] == pin
    assert identity["source"] == "vendored"
    V._finish(tmp_path, [V._check_record("test", True, "synthetic")], readers=identity)
    text = (tmp_path / "verification_report.md").read_text()
    assert "vendored Workbench" in text and pin in text


def test_internal_link_text_is_compared_as_the_rendered_label():
    assert V.visible_text("Read [link to assignment: Essay | the first task].") == "Read the first task."
    assert V.visible_text("Read [link to page: Resources].") == "Read Resources."
    blocks = [{"kind": "p", "runs": [{"text": "Read [link to assignment: Essay | the first task]."}]}]
    assert V.paragraphs(blocks) == ["Read the first task."]


@pytest.mark.parametrize("kind,link_type", [("assignment", "dropbox"), ("discussion", "discuss"),
                                             ("quiz", "quiz"), ("checklist", "checklist")])
def test_internal_link_destination_and_label_are_both_required(kind, link_type):
    blocks = [{"kind": "p", "runs": [{"text": f"[link to {kind}: Target | open target]"}]}]
    objects = [{"kind": kind, "title": "Target", "resource_code": "test-code"}]
    href = f"/d2l/common/dialogs/quickLink/quickLink.d2l?ou={{orgUnitId}}&amp;type={link_type}&amp;rCode=test-code"
    markup = f'<a href="{href}"><b>open</b> target</a>'
    count, problems = V._internal_link_check(blocks, markup, objects, "page", "Overview")
    assert count == 1 and not problems
    assert V._internal_link_check(blocks, markup.replace("test-code", "wrong-code"), objects, "page", "Overview")[1]
    assert V._internal_link_check(blocks, markup.replace("open", "other"), objects, "page", "Overview")[1]
    assert V._internal_link_check(blocks * 2, markup, objects, "page", "Overview")[1]


def test_page_link_and_nested_marker_destinations():
    blocks = [{"kind": "table", "rows": [[[{
        "kind": "dropdown", "title": "[link to page: Guide]", "blocks": []}]]]}]
    objects = [{"kind": "page", "title": "Guide", "file": "course_pages/guide.html"}]
    assert V._internal_link_check(blocks, '<a href="guide.html">Guide</a>', objects, "page", "Overview") == (1, [])
    assert V._internal_link_check(blocks, '<a href="guide.html">Guide</a>', objects, "fragment", "Assignment")[1]


@pytest.fixture
def built(tmp_path):
    source = synth.canonical(tmp_path / "source.docx", overview=[
        "Page: Week 1 Overview", "Page heading: Week 1 – Sample Topic",
        "Read [link to assignment: Week 1 Assignment: Report | the report] and [link to page: Welcome to SYN 101]."])
    model = _read(source)
    out = tmp_path / "build"
    Builder(model, SETTINGS, WB.REPO_DIR).run(out, force=False)
    return model, out


def test_internal_link_blueprint_verifies_and_tampered_destination_fails(built):
    model, out = built
    assert V.verify_build(out, model) == 0
    page = out / "package" / "course_pages" / "week-1-overview.html"
    text = page.read_text()
    assert "rCode=" in text
    page.write_text(text.replace("rCode=", "rCode=incorrect-"))
    assert V.verify_build(out, model) == 1
    check = next(c for c in _report(out)["checks"] if "internal link" in c["check"])
    assert check["status"] == "failed"


def test_model_errors_and_missing_accounting_cannot_verify_green(built):
    model, out = built
    broken = copy.deepcopy(model)
    broken["diagnostics"].append({"severity": "error", "code": "SYNTHETIC_SOURCE_LOSS"})
    assert V.verify_build(out, broken) == 1
    assert any(c["status"] == "not_run" for c in _report(out)["checks"])
    legacy = copy.deepcopy(model)
    legacy.pop("source_accounting", None)
    assert V.verify_build(out, legacy) == 1
    assert "re-read the DOCX" in json.dumps(_report(out))


@pytest.mark.parametrize("missing", ["course_qa", "page_gate"])
def test_missing_required_readback_evidence_is_not_a_pass(built, monkeypatch, missing):
    model, out = built
    original_run = V.subprocess.run

    def run(command, **kwargs):
        result = original_run(command, **kwargs)
        if missing == "course_qa" and any(str(arg).endswith("build_blueprint_bundle.py") for arg in command):
            (out / "verification" / "readback__blueprint_bundle" / "readback__course_qa.json").unlink()
        if missing == "page_gate" and any(str(arg).endswith("check_page_conformance.py") for arg in command):
            (out / "verification" / "page_gate.json").unlink()
        return result

    monkeypatch.setattr(V.subprocess, "run", run)
    assert V.verify_build(out, model) == 1
    name = "required course_qa" if missing == "course_qa" else "Page Kit page gate"
    check = next(c for c in _report(out)["checks"] if name in c["check"])
    assert check["status"] == "not_run" and not check["passed"]


def test_unclassified_top_level_wizard_break_fails_integration(built, monkeypatch):
    model, out = built
    original_run = V.subprocess.run

    def run(command, **kwargs):
        result = original_run(command, **kwargs)
        if any(str(arg).endswith("build_blueprint_bundle.py") for arg in command):
            path = out / "verification" / "readback__blueprint_bundle" / "readback__course_qa.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["summary"]["breaks"] = []  # this must not conceal the actual top-level findings
            data["breaks"].append("Synthetic authored content loss")
            path.write_text(json.dumps(data))
        return result

    monkeypatch.setattr(V.subprocess, "run", run)
    assert V.verify_build(out, model) == 1
    check = next(c for c in _report(out)["checks"] if "Wizard QA" in c["check"])
    assert check["status"] == "failed"
    assert check["unclassified_findings"] == ["Synthetic authored content loss"]
