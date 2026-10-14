"""The public repository: release access without credentials, and a producer identity that is its own.

Nothing here touches the network; urllib is replaced with a recorder."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from blueprint_packager import identity as I
from blueprint_packager import workbench as WB

REPO = WB.REPO_DIR
sys.path.insert(0, str(REPO / "launcher"))
sys.path.insert(0, str(REPO / "scripts"))
import install_release  # noqa: E402
import update_check  # noqa: E402


class _Response(io.BytesIO):
    def __init__(self, body: bytes, headers: dict[str, str] | None = None):
        super().__init__(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _no_credentials(monkeypatch):
    monkeypatch.setattr(update_check, "gh_available", lambda **kwargs: False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)


def _record(monkeypatch, body: bytes, headers: dict[str, str] | None = None):
    seen: list[urllib.request.Request] = []

    def urlopen(request, timeout=None):
        seen.append(request)
        return _Response(body, headers)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return seen


def test_the_check_asks_github_anonymously_when_nothing_is_signed_in(monkeypatch, tmp_path):
    _no_credentials(monkeypatch)
    payload = {"tag_name": "v9.9.9", "name": "v9.9.9", "html_url": update_check.RELEASES_URL + "/tag/v9.9.9",
               "assets": [{"name": "brightspace-blueprint-packager-v9.9.9.zip", "url": "https://api.github.com/repos/x/releases/assets/1"}]}
    seen = _record(monkeypatch, json.dumps(payload).encode("utf-8"), {"ETag": "etag-9"})
    assert update_check.access_mode() == "anonymous"
    status = update_check.check_latest_release(current_version="0.3.0", cache_path=tmp_path / "c.json", force=True)
    assert status.state == "update_available" and status.latest_tag == "v9.9.9" and status.asset_name.endswith("v9.9.9.zip")
    assert len(seen) == 1 and seen[0].full_url == update_check.API_URL
    assert not seen[0].has_header("Authorization") and seen[0].get_header("Accept") == "application/vnd.github+json"
    assert json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))["etag"] == "etag-9"


def test_a_token_is_sent_when_present_and_a_rate_limit_is_reported_not_raised(monkeypatch, tmp_path):
    monkeypatch.setattr(update_check, "gh_available", lambda **kwargs: False)
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    seen = _record(monkeypatch, json.dumps({"tag_name": "v0.3.0", "assets": []}).encode("utf-8"))
    assert update_check.access_mode() == "token"
    status = update_check.check_latest_release(current_version="0.3.0", cache_path=tmp_path / "t.json", force=True)
    assert status.state == "current" and seen[0].get_header("Authorization") == "Bearer t0ken"

    def limited(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 403, "rate limited", {}, io.BytesIO(b""))

    monkeypatch.setattr(urllib.request, "urlopen", limited)
    status = update_check.check_latest_release(current_version="0.3.0", cache_path=tmp_path / "r.json", force=True)
    assert status.state == "unavailable" and "rate-limiting" in status.error


def test_the_installer_downloads_the_asset_anonymously(monkeypatch, tmp_path):
    _no_credentials(monkeypatch)
    seen = _record(monkeypatch, b"PK\x03\x04 not really a zip")
    status = update_check.UpdateStatus(state="update_available", current_version="0.0.0", latest_version="9.9.9",
                                       latest_tag="v9.9.9", asset_name="brightspace-blueprint-packager-v9.9.9.zip",
                                       asset_url="https://api.github.com/repos/x/releases/assets/1")
    target, tag = install_release.download_latest(tmp_path / "dl", status=status)
    assert tag == "v9.9.9" and target.name == status.asset_name and target.read_bytes().startswith(b"PK")
    assert seen[0].full_url == status.asset_url and seen[0].get_header("Accept") == "application/octet-stream"
    assert not seen[0].has_header("Authorization")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org"}).stdout.strip()


def test_the_producer_identity_comes_from_the_release_manifest_when_installed(tmp_path):
    folder = tmp_path / "brightspace-blueprint-packager-v9.9.9"
    folder.mkdir()
    (folder / "release_manifest.json").write_text(json.dumps({
        "version": "9.9.9", "tag": "v9.9.9", "commit": "c" * 40, "build": {"tag_verified": True, "dirty_worktree": False}}),
        encoding="utf-8")
    producer = I.producer(folder, "9.9.9")
    assert producer["identity_state"] == "release" and producer["commit"] == "c" * 40 and producer["ref"] == "v9.9.9"
    assert producer["dirty"] is False and producer["extensions"]["tag_verified"] is True
    assert producer["extensions"]["identity_source"] == "release_manifest.json"


def test_a_copy_inside_another_repository_does_not_borrow_its_commit(tmp_path):
    host = tmp_path / "course-build"
    (host / "tools" / "packager").mkdir(parents=True)
    (host / "README.md").write_text("a course build\n", encoding="utf-8")
    _git(host, "init", "-q")
    _git(host, "add", "-A")
    _git(host, "commit", "-q", "-m", "course")
    producer = I.producer(host / "tools" / "packager", "9.9.9")
    assert producer["identity_state"] == "unknown" and producer["commit"] is None and producer["ref"] is None
    assert producer["extensions"]["identity_source"] == "a repository that is not this tool's"
    own = I.producer(host, "9.9.9")  # the repository's own root is a git identity
    assert own["identity_state"] == "git" and own["commit"] == _git(host, "rev-parse", "HEAD")


def test_this_checkout_reports_its_own_state():
    producer = I.producer(REPO, "0.0.0")
    if (REPO / "release_manifest.json").is_file():  # the suite shipped inside an installed release
        manifest = json.loads((REPO / "release_manifest.json").read_text(encoding="utf-8"))
        assert producer["identity_state"] == "release" and producer["commit"] == manifest["commit"]
    elif (REPO / ".git").exists():
        assert producer["identity_state"] == "git" and producer["commit"]
    else:
        assert producer["identity_state"] == "unknown"
