"""The guided runner, the update check, the release bundle, and the installer: non-interactive tests."""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import synth
from blueprint_packager import __version__
from blueprint_packager import workbench as WB

REPO = WB.REPO_DIR
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "launcher"))

import art  # noqa: E402
import packager_tui as tui  # noqa: E402
import update_check  # noqa: E402
import make_release_bundle  # noqa: E402
import install_release  # noqa: E402

try:
    WB.scripts_dir()
    HAS_WORKBENCH = True
except Exception:
    HAS_WORKBENCH = False


# --------------------------------------------------------------------------- the workshop
def test_python_version_rule():
    assert tui.python_version_ok((3, 11, 0))
    assert tui.python_version_ok((3, 14, 5))
    assert not tui.python_version_ok((3, 10, 9))


def test_vendored_engine_integrity_on_the_real_manifest():
    report = tui.vendor_integrity()
    assert report["ok"], report
    assert report["files"] >= 30 and report["commit"]


def test_a_tampered_vendored_copy_is_reported(tmp_path):
    vendor = tmp_path / "vendor"
    shutil.copytree(REPO / "vendor" / "coursecraft_workbench", vendor)
    manifest = json.loads((vendor / "MANIFEST.json").read_text(encoding="utf-8"))
    first = vendor / manifest["files"][0]["path"]
    first.write_bytes(first.read_bytes() + b"\n# edited\n")
    second = vendor / manifest["files"][1]["path"]
    second.unlink()
    report = tui.vendor_integrity(vendor / "MANIFEST.json")
    assert not report["ok"]
    assert manifest["files"][0]["path"] in report["changed"]
    assert manifest["files"][1]["path"] in report["missing"]


def test_the_splash_grid_renders_and_the_package_slides():
    grid = art.load_grid()
    frames = art.package_frames(grid)
    assert len(frames) == 10 and frames[-1] == grid
    cells = art.package_cells(grid)
    r, c = cells[0]
    assert frames[0][r][c - 9] == grid[r][c]

    class Truecolor:
        truecolor = True

    rendered = art.render(grid, Truecolor())
    assert rendered.count("\n") + 1 == len(grid) // 2
    assert "\x1b[38;2;" in rendered


# --------------------------------------------------------------------------- settings
def test_week_table_is_consecutive_seven_day_weeks():
    weeks = tui.derive_weeks("2026-10-28", 3)
    assert weeks == {"1": ["2026-10-28", "2026-11-03"], "2": ["2026-11-04", "2026-11-10"], "3": ["2026-11-11", "2026-11-17"]}


def test_course_label_guess():
    assert tui.guess_course_label("MBA 620 Marketing - Fall B 2026 Major Edit Blueprint") == "MBA 620 · Marketing"
    assert tui.guess_course_label("NEW 101 Course Title – Spring A 2027 Blueprint") == "NEW 101 · Course Title"
    assert tui.guess_course_label("Untitled document") == ""


def test_generated_settings_load_and_build(tmp_path):
    settings = tui.make_settings({"package_title": "SYN 101 test", "course_label": "SYN 101 · Synthetic", "template": "composite-navy",
                                  "week1_start": "2026-10-28", "weeks": 2})
    assert settings["package"]["manifest_identifier"] == "D2L_SYN_101"
    assert settings["calendar"]["weeks"]["2"] == ["2026-11-04", "2026-11-10"]
    assert settings["calendar"]["rules"]["discussion_initial"]["day"] == "Friday"
    path = tmp_path / "build_settings.json"
    path.write_text(json.dumps(settings), encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8")) == settings
    if not HAS_WORKBENCH:
        pytest.skip("Workbench building blocks not present")
    from blueprint_packager.build import Builder
    from blueprint_packager.joins import resolve
    from blueprint_packager.reader import read_model

    model = read_model(synth.canonical(tmp_path / "canonical.docx"))
    model["joins"] = resolve(model)["joins"] if "joins" not in model else model["joins"]
    result = Builder(model, settings, tmp_path).run(tmp_path / "out", force=True)
    assert result["errors"] == []
    assert (tmp_path / "out" / "SYN_101__package.zip").is_file()


# --------------------------------------------------------------------------- the update check
def _payload(tag: str, assets: bool = True) -> dict:
    payload = {"tag_name": tag, "name": f"Blueprint Packager {tag}",
               "html_url": f"https://github.com/timebeing92/brightspace-blueprint-packager/releases/tag/{tag}"}
    if assets:
        payload["assets"] = [{"name": f"brightspace-blueprint-packager-{tag}.zip", "url": "https://api.github.com/repos/x/releases/assets/1"}]
    return payload


def test_update_check_parses_a_release_and_caches_it(tmp_path):
    cache = tmp_path / ".update_check.json"
    calls = []

    def fetcher(etag):
        calls.append(etag)
        return _payload("v9.9.9"), "etag-1", False

    now = dt.datetime(2026, 10, 8, 12, 0, tzinfo=dt.timezone.utc)
    status = update_check.check_latest_release(current_version="0.2.0", cache_path=cache, now=now, fetcher=fetcher)
    assert status.update_available and status.latest_version == "9.9.9" and status.asset_name.endswith("v9.9.9.zip")
    assert status.release_url.startswith("https://github.com/timebeing92/brightspace-blueprint-packager/releases/")
    again = update_check.check_latest_release(current_version="0.2.0", cache_path=cache, now=now + dt.timedelta(hours=1), fetcher=fetcher)
    assert again.from_cache and calls == ["" ]  # a fresh cache is not refetched
    later = update_check.check_latest_release(current_version="0.2.0", cache_path=cache, now=now + dt.timedelta(days=2), fetcher=fetcher)
    assert not later.from_cache and calls == ["", "etag-1"]
    current = update_check.check_latest_release(current_version="9.9.9", cache_path=cache, now=now, fetcher=fetcher, force=True)
    assert current.state == "current"
    assert update_check.notice_is_due(cache, latest_version="9.9.9")
    update_check.mark_notified(cache, latest_version="9.9.9", now=now)
    assert not update_check.notice_is_due(cache, latest_version="9.9.9", now=now + dt.timedelta(hours=2))


def test_update_check_reports_no_access_and_bad_responses(tmp_path):
    def denied(etag):
        raise PermissionError("no GitHub access")

    def broken(etag):
        return {"tag_name": "not-a-version"}, "", False

    assert update_check.check_latest_release(current_version="0.2.0", cache_path=tmp_path / "a.json", fetcher=denied).state == "no_access"
    assert update_check.check_latest_release(current_version="0.2.0", cache_path=tmp_path / "b.json", fetcher=broken).state == "unavailable"
    assert update_check.safe_release_url("https://evil.example/x") == update_check.RELEASES_URL


# --------------------------------------------------------------------------- releases and installs
def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org"})


def _tiny_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "blueprint_packager").mkdir(parents=True)
    (repo / "blueprint_packager" / "__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    (repo / "bpk.py").write_text("print('hi')\n", encoding="utf-8")
    (repo / "blueprint_packager.sh").write_text("#!/usr/bin/env bash\necho launched\n", encoding="utf-8")
    (repo / "vendor" / "coursecraft_workbench").mkdir(parents=True)
    (repo / "vendor" / "coursecraft_workbench" / "MANIFEST.json").write_text(json.dumps({"commit": "abc1234def", "commit_short": "abc1234", "files": []}), encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "start")
    return repo


def test_release_bundle_manifest_is_complete_and_verifies(tmp_path):
    repo = _tiny_repo(tmp_path)
    out_zip, sidecar = make_release_bundle.build(tmp_path / "dist", root=repo, now=dt.datetime(2026, 10, 8, tzinfo=dt.timezone.utc))
    assert out_zip.name == "brightspace-blueprint-packager-v1.2.3.zip"
    assert sidecar.read_text(encoding="utf-8").split()[1] == out_zip.name
    with zipfile.ZipFile(out_zip) as archive:
        names = archive.namelist()
        tops = {name.split("/")[0] for name in names}
        assert tops == {"brightspace-blueprint-packager-v1.2.3"}
        manifest = json.loads(archive.read("brightspace-blueprint-packager-v1.2.3/release_manifest.json"))
    assert manifest["version"] == "1.2.3" and manifest["tag"] == "v1.2.3" and len(manifest["commit"]) == 40
    assert manifest["vendored_workbench"]["commit_short"] == "abc1234"
    listed = {entry["path"] for entry in manifest["files"]}
    archived = {name.split("/", 1)[1] for name in names if "/" in name} - {"release_manifest.json"}
    assert listed == archived  # every archived file is in the manifest, and nothing else
    (repo / "bpk.py").write_text("print('dirty')\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="uncommitted"):
        make_release_bundle.build(tmp_path / "dist2", root=repo)


def test_install_release_verifies_installs_beside_and_points(tmp_path):
    repo = _tiny_repo(tmp_path)
    out_zip, _ = make_release_bundle.build(tmp_path / "dist", root=repo)
    root = tmp_path / "installs"
    old = root / "old-version"
    old.mkdir(parents=True)
    (old / ".last_run.json").write_text('{"blueprint": "x.docx"}', encoding="utf-8")
    result = install_release.install_archive(out_zip, root, expected_version="v1.2.3", carry_from=old)
    assert result["status"] == "installed"
    folder = Path(result["folder"])
    assert folder == root / "brightspace-blueprint-packager-v1.2.3"
    assert (folder / "INSTALL_RECEIPT.json").is_file() and (folder / ".last_run.json").is_file()
    assert install_release.current_folder(root) == folder
    again = install_release.install_archive(out_zip, root, expected_version="1.2.3")
    assert again["status"] == "already_installed"
    with pytest.raises(install_release.ReleaseInstallError, match="expected"):
        install_release.install_archive(out_zip, tmp_path / "other", expected_version="9.9.9")
    # a tampered archive is refused before anything is installed
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(out_zip) as src, zipfile.ZipFile(tampered, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename.endswith("/bpk.py"):
                data = b"print('changed')\n"
            dst.writestr(info, data)
    with pytest.raises(install_release.ReleaseInstallError, match="hash mismatch"):
        install_release.install_archive(tampered, tmp_path / "other2")
    assert not (tmp_path / "other2" / "brightspace-blueprint-packager-v1.2.3").exists()


# --------------------------------------------------------------------------- the runner, end to end
@pytest.mark.skipif(not HAS_WORKBENCH, reason="Workbench building blocks not present")
def test_the_runner_builds_a_package_from_scripted_answers(tmp_path):
    blueprint = synth.canonical(tmp_path / "SYN_101__blueprint.docx")
    out_dir = tmp_path / "out"
    answers = "\n".join([
        str(out_dir),              # output folder (the blueprint came from the command line, so no peek to confirm)
        "",                        # settings: make one for me (default)
        "",                        # package title (suggestion)
        "SYN 101 · Synthetic",     # course label
        "",                        # manifest identifier
        "",                        # template (default)
        "y",                       # add a term calendar
        "",                        # time zone
        "2026-10-28",              # first day of week 1
        "1",                       # weeks
        "",                        # assignment due day (Sunday)
        "",                        # discussion initial day (Friday)
        "",                        # discussion response day (Sunday)
        "",                        # Return to run
        "",                        # accept the displayed calendar boundaries
    ]) + "\n"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(tmp_path)}
    state = REPO / ".last_run.json"
    saved = state.read_text(encoding="utf-8") if state.is_file() else None
    try:
        proc = subprocess.run([sys.executable, "-B", str(SCRIPTS / "packager_tui.py"), "--plain", "--no-splash", "--no-update-check",
                               "--task", "build", "--blueprint", str(blueprint)], input=answers, capture_output=True, text=True, env=env, check=False)
    finally:
        if saved is None:
            state.unlink(missing_ok=True)
        else:
            state.write_text(saved, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    assert "[ ok ] Read the blueprint" in proc.stdout
    assert "[ ok ] Build the package" in proc.stdout
    assert "[ ok ] Verify the package" in proc.stdout
    assert "every planned date is in the package" in proc.stdout  # the calendar made dates
    assert "The package is built" in proc.stdout and "What to do next" in proc.stdout
    settings = json.loads((out_dir / "build_settings.json").read_text(encoding="utf-8"))
    assert settings["package"]["course_label"] == "SYN 101 · Synthetic"
    assert (out_dir / "build" / "course_pages_refresh.zip").is_file()
    receipt = json.loads((out_dir / "build" / "component_package_receipt.json").read_text(encoding="utf-8"))
    assert receipt["zip"]["sha256"] in proc.stdout


@pytest.mark.skipif(not HAS_WORKBENCH, reason="Workbench building blocks not present")
def test_the_runner_dry_run_and_doctor(tmp_path):
    blueprint = synth.canonical(tmp_path / "dry.docx")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(tmp_path)}
    state = REPO / ".last_run.json"
    saved = state.read_text(encoding="utf-8") if state.is_file() else None
    try:
        proc = subprocess.run([sys.executable, "-B", str(SCRIPTS / "packager_tui.py"), "--plain", "--no-splash", "--no-update-check", "--yes",
                               "--task", "dry", "--blueprint", str(blueprint), "--output-dir", str(tmp_path / "dry")], capture_output=True, text=True, env=env, check=False)
    finally:
        if saved is None:
            state.unlink(missing_ok=True)
        else:
            state.write_text(saved, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "The blueprint reads clean" in proc.stdout and (tmp_path / "dry" / "model" / "dry__course_model.json").is_file()
    doctor = subprocess.run([sys.executable, "-B", str(SCRIPTS / "packager_tui.py"), "--doctor", "--plain"], capture_output=True, text=True, env=env, check=False)
    assert doctor.returncode == 0 and "Vendored engine" in doctor.stdout
