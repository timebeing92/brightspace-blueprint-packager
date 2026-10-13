"""Release readiness: the builder's provenance, the installer's reinstall check and repair, and the update from v0.2.2.

The update case is real rather than a fixture: the released tag is archived by
the builder, installed by the installer, run once so it remembers answers, and
the working tree is then installed beside it the way an update is."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from blueprint_packager import __version__
from blueprint_packager import workbench as WB

REPO = WB.REPO_DIR
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "launcher"))

import install_release  # noqa: E402
import make_release_bundle  # noqa: E402

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org"}
PREVIOUS_RELEASE = "v0.2.2"
SETTINGS = {
    "schema": "blueprint_packager.build_settings/0.1",
    "package": {"title": "SYN 101 update test", "manifest_identifier": "D2L_SYN101",
                "base_resource_code": "00000000-0000-4000-8000-000000000101"},
    "template": "bumk515-classic",
    "forum_order": ["Community Forum", "Discussions"],
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=GIT_ENV).stdout.strip()


def tiny_repo(tmp_path: Path, version: str = "1.2.3") -> Path:
    repo = tmp_path / "repo"
    (repo / "blueprint_packager").mkdir(parents=True)
    (repo / "blueprint_packager" / "__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    (repo / "bpk.py").write_text("print('hi')\n", encoding="utf-8")
    (repo / "blueprint_packager.sh").write_text("#!/usr/bin/env bash\necho launched\n", encoding="utf-8")
    (repo / "vendor" / "coursecraft_workbench").mkdir(parents=True)
    (repo / "vendor" / "coursecraft_workbench" / "MANIFEST.json").write_text(
        json.dumps({"commit": "abc1234def", "commit_short": "abc1234", "files": []}), encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "start")
    return repo


def manifest_of(out_zip: Path) -> dict:
    return make_release_bundle.read_manifest(out_zip)


# --------------------------------------------------------------------------- the builder
def test_the_manifest_comes_from_the_archived_commit_not_the_worktree(tmp_path):
    repo = tiny_repo(tmp_path)
    (repo / "blueprint_packager" / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")  # not committed
    with pytest.raises(SystemExit, match="uncommitted"):
        make_release_bundle.build(tmp_path / "d0", root=repo)
    out_zip, sidecar = make_release_bundle.build(tmp_path / "d1", root=repo, allow_dirty=True)
    manifest = manifest_of(out_zip)
    assert out_zip.name == "brightspace-blueprint-packager-v1.2.3.zip" and manifest["version"] == "1.2.3"  # the committed version
    assert manifest["tag"] is None
    assert manifest["build"] == {"ref": "HEAD", "tag_verified": False, "dirty_worktree": True}
    assert manifest["commit"] == git(repo, "rev-parse", "HEAD") and manifest["vendored_workbench"]["commit_short"] == "abc1234"
    assert sidecar.read_text(encoding="utf-8").split() == [make_release_bundle.sha256_file(out_zip), out_zip.name]
    with zipfile.ZipFile(out_zip) as archive:
        assert b'"1.2.3"' in archive.read("brightspace-blueprint-packager-v1.2.3/blueprint_packager/__init__.py")


def test_a_tagged_build_checks_the_tag_against_the_commit_and_the_version(tmp_path):
    repo = tiny_repo(tmp_path)
    first = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "v1.2.3")
    (repo / "blueprint_packager" / "__init__.py").write_text('__version__ = "1.2.4"\n', encoding="utf-8")
    git(repo, "commit", "-q", "-am", "bump")
    second = git(repo, "rev-parse", "HEAD")
    with pytest.raises(SystemExit, match="does not exist"):
        make_release_bundle.build(tmp_path / "d0", root=repo, tag="v1.2.4")
    git(repo, "tag", "v1.2.4")
    git(repo, "tag", "wrong-name")
    out_zip, _ = make_release_bundle.build(tmp_path / "d1", root=repo, ref="v1.2.4", tag="v1.2.4")
    manifest = manifest_of(out_zip)
    assert manifest["tag"] == "v1.2.4" and manifest["commit"] == second
    assert manifest["build"] == {"ref": "v1.2.4", "tag_verified": True, "dirty_worktree": False}
    out_zip, _ = make_release_bundle.build(tmp_path / "d2", root=repo)  # the tag at HEAD is found without being named
    assert manifest_of(out_zip)["tag"] == "v1.2.4"
    out_zip, _ = make_release_bundle.build(tmp_path / "d3", root=repo, ref=first)  # an earlier commit, by sha, with its own version and tag
    assert out_zip.name.endswith("v1.2.3.zip") and manifest_of(out_zip)["tag"] == "v1.2.3" and manifest_of(out_zip)["commit"] == first
    with pytest.raises(SystemExit, match="points at"):
        make_release_bundle.build(tmp_path / "d4", root=repo, ref=first, tag="v1.2.4")
    with pytest.raises(SystemExit, match="must be v1.2.4"):
        make_release_bundle.build(tmp_path / "d5", root=repo, tag="wrong-name")
    with pytest.raises(SystemExit, match="not a commit"):
        make_release_bundle.build(tmp_path / "d6", root=repo, ref="no-such-ref")
    (repo / "bpk.py").write_text("print('dirty')\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="clean worktree"):
        make_release_bundle.build(tmp_path / "d7", root=repo, tag="v1.2.4", allow_dirty=True)


# --------------------------------------------------------------------------- the installer
def test_reinstall_checks_the_installed_files_and_repairs_only_when_asked(tmp_path):
    repo = tiny_repo(tmp_path)
    out_zip, _ = make_release_bundle.build(tmp_path / "dist", root=repo)
    root = tmp_path / "installs"
    folder = Path(install_release.install_archive(out_zip, root)["folder"])
    # runtime state an install legitimately accumulates
    (folder / ".venv" / "bin").mkdir(parents=True)
    (folder / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    (folder / ".last_run.json").write_text('{"blueprint": "x.docx"}', encoding="utf-8")
    (folder / "logs").mkdir()
    (folder / "logs" / "run.log").write_text("ran\n", encoding="utf-8")
    again = install_release.install_archive(out_zip, root)
    assert again["status"] == "already_installed" and again["checked_files"] == 5  # four release files and the manifest
    # a changed and a missing release file: refused, nothing touched, unless repair is asked for
    (folder / "bpk.py").write_text("print('edited')\n", encoding="utf-8")
    (folder / "blueprint_packager.sh").unlink()
    with pytest.raises(install_release.ReleaseInstallError, match=r"1 release file\(s\) are missing and 1 changed .*--repair") as refused:
        install_release.install_archive(out_zip, root)
    assert "blueprint_packager.sh" in str(refused.value) and "bpk.py" in str(refused.value)
    assert (folder / "bpk.py").read_text(encoding="utf-8") == "print('edited')\n"
    repaired = install_release.install_archive(out_zip, root, repair=True)
    assert repaired["status"] == "repaired" and sorted(repaired["repaired"]) == ["blueprint_packager.sh", "bpk.py"]
    assert (folder / "bpk.py").read_text(encoding="utf-8") == "print('hi')\n" and (folder / "blueprint_packager.sh").is_file()
    assert (folder / ".last_run.json").read_text(encoding="utf-8") == '{"blueprint": "x.docx"}'
    assert (folder / ".venv" / "bin" / "python").is_file() and (folder / "logs" / "run.log").is_file()
    receipt = json.loads((folder / "INSTALL_RECEIPT.json").read_text(encoding="utf-8"))
    assert receipt["repaired_files"] == repaired["repaired"] and receipt["repaired_at_utc"].endswith("Z")
    assert install_release.install_archive(out_zip, root)["status"] == "already_installed"
    assert install_release.current_folder(root) == folder
    # the manifest itself is release-owned
    (folder / "release_manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(install_release.ReleaseInstallError, match="release_manifest.json"):
        install_release.install_archive(out_zip, root)
    assert install_release.install_archive(out_zip, root, repair=True)["repaired"] == ["release_manifest.json"]
    # a folder with a different receipt is still left alone
    (folder / "INSTALL_RECEIPT.json").write_text('{"archive_sha256": "other"}', encoding="utf-8")
    with pytest.raises(install_release.ReleaseInstallError, match="move it aside"):
        install_release.install_archive(out_zip, root, repair=True)


# --------------------------------------------------------------------------- the update from the released version
def previous_release_available() -> bool:
    try:
        git(REPO, "rev-parse", "--verify", "--quiet", f"{PREVIOUS_RELEASE}^{{commit}}")
    except subprocess.CalledProcessError:
        return False
    return True


def require_previous_release() -> None:
    if previous_release_available():
        return
    reason = f"tag {PREVIOUS_RELEASE} is not in this checkout (a shallow clone or an unpacked release); fetch tags to run the update test"
    if os.environ.get("BPK_REQUIRE_RELEASE_TAGS") == "1":
        pytest.fail(reason + " (BPK_REQUIRE_RELEASE_TAGS=1 forbids skipping)")
    pytest.skip(reason)


def worktree_release(tmp_path: Path) -> Path:
    """A release ZIP of the working tree as it is, uncommitted edits included, built the real way."""
    repo = tmp_path / "worktree-copy"
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"], check=True, capture_output=True).stdout.decode("utf-8")
    for rel in filter(None, listed.split("\0")):
        source = REPO / rel
        if source.is_file():  # a file deleted in the worktree is not part of it
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "worktree")
    out_zip, _ = make_release_bundle.build(tmp_path / "dist-candidate", root=repo)
    return out_zip


def run_tui(folder: Path, *args: str, home: Path, released: bool = False) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(home), "USERPROFILE": str(home), "BPK_NO_UPDATE_CHECK": "1"}
    if released:  # the released runner writes its glyphs strictly; a Windows pipe in cp1252 would stop it
        env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, "-B", str(folder / "scripts" / "packager_tui.py"), "--plain", "--no-splash",
                           "--no-update-check", *args], capture_output=True, text=True, env=env, check=False)


def test_updating_from_the_released_version_keeps_answers_and_re_reads_the_blueprint(tmp_path):
    require_previous_release()
    root, home = tmp_path / "installs", tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    # 1. the released version, archived from its tag by the builder and installed by the installer
    old_zip, _ = make_release_bundle.build(tmp_path / "dist-old", root=REPO, ref=PREVIOUS_RELEASE, allow_dirty=True)
    assert manifest_of(old_zip)["tag"] == PREVIOUS_RELEASE
    old = Path(install_release.install_archive(old_zip, root, expected_version=PREVIOUS_RELEASE)["folder"])

    # 2. a blueprint in that version's own layout, read once by that version so it remembers its answers
    blueprint = tmp_path / "course.docx"
    subprocess.run([sys.executable, "-B", "-c",
                    "import sys; sys.path[:0] = [sys.argv[1], sys.argv[2]]; import synth; from pathlib import Path; synth.canonical(Path(sys.argv[3]))",
                    str(old / "tests"), str(old), str(blueprint)], check=True, env=env)
    first = run_tui(old, "--yes", "--task", "dry", "--blueprint", str(blueprint), "--output-dir", str(tmp_path / "old-run"), home=home, released=True)
    assert first.returncode == 0, first.stdout[-2000:] + first.stderr[-2000:]
    remembered = json.loads((old / ".last_run.json").read_text(encoding="utf-8"))
    assert remembered["blueprint"] == str(blueprint)
    old_model = tmp_path / "old-run" / "model" / "course__course_model.json"
    assert old_model.is_file()

    # 3. the working tree, installed beside it the way an update is
    new_zip = worktree_release(tmp_path)
    assert manifest_of(new_zip)["version"] == __version__ and __version__ != PREVIOUS_RELEASE.lstrip("v")
    result = install_release.install_archive(new_zip, root, carry_from=old)
    new = Path(result["folder"])
    assert result["status"] == "installed" and new != old and install_release.current_folder(root) == new
    assert json.loads((new / ".last_run.json").read_text(encoding="utf-8")) == remembered

    # 4. the new version runs from the remembered answers alone and re-reads the blueprint
    second = run_tui(new, "--yes", "--task", "dry", "--output-dir", str(tmp_path / "new-run"), home=home)
    assert second.returncode == 0, second.stdout[-2000:] + second.stderr[-2000:]
    assert "course.docx" in second.stdout and "The blueprint reads clean" in second.stdout
    new_model = tmp_path / "new-run" / "model" / "course__course_model.json"
    assert json.loads(new_model.read_text(encoding="utf-8"))["source_accounting"]["complete"]

    # 5. the old version's cached model is refused with the re-read instruction; the re-read model builds
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(SETTINGS), encoding="utf-8")
    refused = subprocess.run([sys.executable, "-B", str(new / "bpk.py"), "build", str(old_model), "--settings", str(settings),
                              "--output-dir", str(tmp_path / "build-old")], capture_output=True, text=True, env=env)
    assert refused.returncode != 0 and "Re-read the DOCX" in refused.stdout + refused.stderr
    built = subprocess.run([sys.executable, "-B", str(new / "bpk.py"), "build", str(new_model), "--settings", str(settings),
                            "--output-dir", str(tmp_path / "build-new")], capture_output=True, text=True, env=env)
    assert built.returncode == 0, built.stdout[-2000:] + built.stderr[-2000:]
    assert list((tmp_path / "build-new").glob("*.zip")) and (tmp_path / "build-new" / "component_package_receipt.json").is_file()
