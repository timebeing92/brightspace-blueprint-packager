"""Synthetic authoring workflows in the guided runner."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from docx import Document

from blueprint_packager import workbench as WB
from blueprint_packager.blank import write_blank
from blueprint_packager.reader import read_model
import synth

sys.path.insert(0, str(WB.REPO_DIR / "scripts"))
import packager_tui as tui


@pytest.fixture(autouse=True)
def isolated_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(tui, "STATE_PATH", tmp_path / "runner-state.json")
    monkeypatch.setattr(tui, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(tui, "CACHE_PATH", tmp_path / "updates.json")
    monkeypatch.setattr(tui, "TERM", tui.ui.Term(plain=True))


def _args(*args):
    return ["--plain", "--yes", "--no-update-check", *map(str, args)]


def test_title_peek_prefers_course_subtitle_and_counts_activities(tmp_path):
    path = tmp_path / "blank.docx"
    write_blank(path, course_number="SYN 202", course_title="Synthetic Authoring", term="Test Term", weeks=2,
                assignments_per_week=2, discussions_per_week=3, week_counts={2: {"assignments": 0, "discussions": 1}})
    peek = tui.peek_blueprint(path)
    assert not peek["error"]
    assert "SYN 202" in peek["title"] and "Synthetic Authoring" in peek["title"]
    assert peek["title"] != "Blueprint"
    assert peek["week_numbers"] == [1, 2]
    assert (peek["assignments"], peek["discussions"]) == (2, 4)


@pytest.mark.parametrize("raw", [r"C:\Users\Synthetic\My Documents\course.docx", r"\\server\courses\My Course\blueprint.docx"])
def test_windows_paths_preserve_separators(raw):
    for value in (raw, '"' + raw + '"'):
        parsed = tui.parse_path(value)
        assert str(parsed) == raw if os.name != "nt" else parsed.is_absolute()


def test_posix_dragged_and_quoted_paths(tmp_path):
    path = tmp_path / "some course.docx"
    assert tui.parse_path('"' + str(path) + '"') == path.resolve()
    if os.name != "nt":  # a backslash-escaped space is a POSIX shell convention; Windows drags a quoted path
        assert tui.parse_path(str(path).replace(" ", r"\ ")) == path.resolve()


def test_calendar_file_preserves_breaks_and_does_not_invent_due_rules(tmp_path):
    path = tmp_path / "weeks.json"
    weeks = {"1": ["2027-01-06", "2027-01-10"], "2": ["2027-01-18", "2027-01-22"]}
    path.write_text(json.dumps(weeks), encoding="utf-8")
    calendar = tui.calendar_from_file(path, timezone="UTC")
    assert calendar["weeks"] == weeks and calendar["timezone"] == "UTC"
    assert "rules" not in calendar
    original = {"timezone": "America/New_York", "weeks": {}, "rules": {"assignment": {"day": "last_day"}}}
    assert tui.calendar_from_file(path, original)["rules"] == original["rules"]
    path.write_text(json.dumps({"timezone": "UTC", "weeks": weeks, "rules": {"assignment": {"day": "last_day"}}}), encoding="utf-8")
    assert tui.calendar_from_file(path)["rules"]["assignment"]["day"] == "last_day"


def test_calendar_review_edits_only_named_week(tmp_path, monkeypatch, capsys):
    original = {"timezone": "UTC", "weeks": {"1": ["2027-01-06", "2027-01-12"], "2": ["2027-01-13", "2027-01-19"]}}
    answers = iter(["1", "2027-01-06", "2027-01-10", ""])
    monkeypatch.setattr(tui.ui, "prompt_text", lambda *a, **kw: next(answers))
    reviewed = tui.review_calendar(original, interactive=True, week_numbers=[1, 2])
    assert reviewed["weeks"]["1"] == ["2027-01-06", "2027-01-10"]
    assert reviewed["weeks"]["2"] == original["weeks"]["2"]
    assert original["weeks"]["1"][1] == "2027-01-12"
    assert "5 days" in capsys.readouterr().out


def test_calendar_rejects_overlap_and_missing_weeks():
    with pytest.raises(ValueError, match="overlaps"):
        tui.validate_calendar({"timezone": "UTC", "weeks": {"1": ["2027-01-01", "2027-01-07"], "2": ["2027-01-07", "2027-01-14"]}})
    with pytest.raises(ValueError, match="missing blueprint"):
        tui.validate_calendar({"timezone": "UTC", "weeks": {"1": ["2027-01-01", "2027-01-07"]}}, [1, 2])


def test_calendar_settings_copy_preserves_source_paths(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "settings.json"
    settings = {"package": {"title": "Synthetic"}, "workbench_scripts": "engine/scripts",
                "carried_quizzes": [{"title": "Synthetic Quiz", "source_dir": "quiz_source", "payload": "quiz.xml"}]}
    path.write_text(json.dumps(settings), encoding="utf-8")
    dates = tmp_path / "dates.json"
    dates.write_text(json.dumps({"1": ["2027-01-01", "2027-01-07"]}), encoding="utf-8")
    args = tui.parse_args(_args("--calendar-file", dates, "--timezone", "UTC"))
    result = tui.prepare_calendar_settings(path, args, tmp_path / "out", {"week_numbers": [1]})
    assert result != path and json.loads(path.read_text(encoding="utf-8")) == settings
    copied = json.loads(result.read_text(encoding="utf-8"))
    assert copied["carried_quizzes"][0]["source_dir"] == str(source / "quiz_source")
    assert copied["workbench_scripts"] == str(source / "engine" / "scripts")


def test_status_summary_does_not_count_skips_as_passes(tmp_path):
    (tmp_path / "component_package_receipt.json").write_text(json.dumps({"zip": {}, "extensions": {"build_mode": "preview", "authoring_state": "draft"}}), encoding="utf-8")
    summary = {"passed": 3, "failed": 1, "not_run": 2, "not_applicable": 4}
    (tmp_path / "verification_report.json").write_text(json.dumps({"passed": False, "summary": summary}), encoding="utf-8")
    peek = tui.peek_build(tmp_path)
    assert peek["verified"] == "3 passed; 1 failed; 2 not run; 4 not applicable"
    assert not peek["verification_passed"] and peek["preview"]
    assert all("Import the ZIP" not in step for step in tui.build_next_steps(tmp_path))


def test_first_task_supports_counts_and_never_silently_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(tui.ui, "prompt_text", lambda *a, **kw: pytest.fail("--yes must not prompt"))
    args = _args("--task", "first", "--course-number", "SYN 202", "--course-title", "Synthetic Authoring",
                 "--term", "Test Term", "--weeks", 2, "--assignments-per-week", 2, "--discussions-per-week", 0,
                 "--week-count", "2:1:3", "--output-dir", tmp_path)
    assert tui.main(args) == 0
    first = Path(tui.load_state()["blueprint"])
    doc = Document(first)
    doc.add_paragraph("Synthetic authored marker.")
    doc.save(first)
    original = first.read_bytes()
    assert tui.main(args) == 0
    second = Path(tui.load_state()["blueprint"])
    assert second != first and first.read_bytes() == original
    assert tui.main([*args, "--force"]) == 0
    backups = list(tmp_path.glob("*.backup-*.docx"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    model = read_model(second)
    assert [(len(w["assignments"]), len(w["discussions"])) for w in model["weeks"]] == [(2, 0), (1, 3)]


def test_draft_requires_explicit_preview_and_never_gets_import_advice(tmp_path, capsys):
    source = tmp_path / "draft.docx"
    write_blank(source, course_number="SYN 202", course_title="Synthetic Draft", term="Test Term", weeks=1)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(tui.make_settings({"package_title": "Synthetic draft"})))
    out = tmp_path / "out"
    common = _args("--task", "build", "--blueprint", source, "--settings", settings, "--output-dir", out)
    assert tui.main(common) == 1
    assert not (out / "build").exists()
    first = capsys.readouterr().out
    assert "Authoring readiness" in first and "explicitly rerun with --preview" in first
    assert tui.main([*common, "--preview"]) == 0
    output = capsys.readouterr().out
    assert "The draft preview is built" in output
    assert "import this" not in output and "Import the ZIP" not in output
    assert tui.peek_build(out / "build")["preview"]


def test_dry_run_reports_draft_readiness(tmp_path, capsys):
    source = tmp_path / "draft.docx"
    write_blank(source, course_number="SYN 202", course_title="Synthetic Draft", term="Test Term", weeks=1)
    assert tui.main(_args("--dry-run", "--blueprint", source, "--output-dir", tmp_path / "read")) == 0
    output = capsys.readouterr().out
    assert "The blueprint is a draft" in output and "Authoring readiness" in output
    assert not (tmp_path / "read" / "build").exists()


def test_calendar_file_build_uses_explicit_boundaries_without_prompts(tmp_path, monkeypatch, capsys):
    source = synth.canonical(tmp_path / "course.docx")
    settings = tmp_path / "settings.json"
    original = tui.make_settings({"package_title": "Synthetic calendar"})
    settings.write_text(json.dumps(original), encoding="utf-8")
    calendar = tmp_path / "calendar.json"
    calendar.write_text(json.dumps({"timezone": "UTC", "weeks": {"1": ["2027-01-06", "2027-01-08"]},
                                    "rules": {"assignment": {"day": "last_day"}}}), encoding="utf-8")
    monkeypatch.setattr(tui.ui, "prompt_text", lambda *a, **kw: pytest.fail("--yes must not prompt"))
    out = tmp_path / "out"
    assert tui.main(_args("--task", "build", "--blueprint", source, "--settings", settings,
                         "--calendar-file", calendar, "--output-dir", out)) == 0
    output = capsys.readouterr().out
    assert "2027-01-06 (Wed) to 2027-01-08 (Fri); 3 days" in output
    assert json.loads(settings.read_text(encoding="utf-8")) == original
    object_map = json.loads((out / "build" / "object_map.json").read_text(encoding="utf-8"))
    assert [row["utc"] for row in object_map["dates"]] == ["2027-01-08T23:59:00.000Z"]


def test_yes_without_a_blueprint_refuses_instead_of_prompting(monkeypatch):
    monkeypatch.setattr(tui.ui, "prompt_text", lambda *a, **kw: pytest.fail("--yes must not prompt"))
    with pytest.raises(SystemExit, match="No blueprint"):
        tui.main(_args("--task", "build"))


def test_failed_preview_verification_keeps_results_reviewable(tmp_path, capsys):
    source = synth.canonical(tmp_path / "pending.docx", assignment_body=["TODO: finish this synthetic instruction."])
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(tui.make_settings({"package_title": "Synthetic pending content"})))
    out = tmp_path / "out"
    assert tui.main(_args("--task", "build", "--blueprint", source, "--settings", settings,
                         "--output-dir", out, "--preview")) == 1
    output = capsys.readouterr().out
    assert "Draft preview built; checks need attention" in output
    assert "import this" not in output and "Import the ZIP" not in output
    assert (out / "build" / "verification_report.json").is_file()
    assert not tui.peek_build(out / "build")["verification_passed"]
