#!/usr/bin/env python3
"""Smoke-test a published Blueprint Packager release from the asset people download.

    python3 scripts/smoke_test_release.py --tag v0.3.0 --report docs/evidence/RELEASE_SMOKE_v0.3.0.json
    python3 scripts/smoke_test_release.py --archive dist/brightspace-blueprint-packager-v0.3.0.zip

Every step runs against the downloaded ZIP, installed into an empty folder,
with the Python environment the launcher creates there, never against this
checkout. The steps, each recorded with its command and outcome:

1. the release has exactly one ZIP asset and its sidecar (what the installers expect);
2. the sidecar's hash matches the ZIP;
3. the installer verifies and installs it; the shipped installer, run from the
   installed folder, recognises it as already installed;
4. the manifest names the tag, a verified tag, the commit the tag points at
   (when this checkout has the tag) and the vendored Workbench pin;
5. the launcher starts, creates the venv, installs the packages and passes the doctor;
6. a blank blueprint is written and read back;
7. a ready synthetic course (the shipped tests' fixture) is read, built and verified;
8. the built package goes through the vendored Blueprint Wizard, back through
   `from-wizard`, and is read, built and verified again;
9. the shipped suite passes in the installed copy (``--skip-suite`` leaves it out).

The report (JSON, with a Markdown twin beside it) is the evidence record for
the release; commit it under docs/evidence/ after publishing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "launcher"))
sys.path.insert(0, str(ROOT / "scripts"))

import install_release  # noqa: E402

REPO = "timebeing92/brightspace-blueprint-packager"
SETTINGS = {
    "schema": "blueprint_packager.build_settings/0.1",
    "package": {"title": "SMK 101 smoke test", "manifest_identifier": "D2L_SMK101",
                "base_resource_code": "00000000-0000-4000-8000-000000000201"},
    "template": "composite-navy",
    "forum_order": ["Community Forum", "Discussions"],
}


class Smoke:
    def __init__(self, work: Path) -> None:
        self.work = work
        self.steps: list[dict[str, Any]] = []
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "BPK_NO_UPDATE_CHECK": "1"}

    def run(self, name: str, command: list[str], *, cwd: Path | None = None, ok_codes: tuple[int, ...] = (0,),
            timeout: int = 1800) -> subprocess.CompletedProcess:
        started = time.monotonic()
        process = subprocess.run(command, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                                 env=self.env, check=False, timeout=timeout)
        recorded = ["python" if part == sys.executable else part for part in command]  # the driver, not its path
        self.steps.append({"step": name, "ok": process.returncode in ok_codes, "command": recorded,
                           "returncode": process.returncode, "seconds": round(time.monotonic() - started, 1),
                           "stdout_tail": process.stdout[-1500:], "stderr_tail": process.stderr[-1500:]})
        if process.returncode not in ok_codes:
            raise SystemExit(f"step {name!r} failed (exit {process.returncode}):\n{process.stdout[-2000:]}\n{process.stderr[-2000:]}")
        return process

    def check(self, name: str, ok: bool, detail: Any) -> None:
        self.steps.append({"step": name, "ok": bool(ok), "detail": detail})
        if not ok:
            raise SystemExit(f"check {name!r} failed: {detail}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def venv_python(folder: Path) -> Path:
    return folder / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")


def launcher(folder: Path, *args: str) -> list[str]:
    if os.name == "nt":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(folder / "blueprint_packager.ps1"), *args]
    return ["bash", str(folder / "blueprint_packager.sh"), *args]


def fetch(smoke: Smoke, tag: str, download: Path) -> tuple[Path, Path, dict[str, Any]]:
    view = smoke.run("release view", ["gh", "release", "view", tag, "--repo", REPO, "--json", "tagName,assets,publishedAt,targetCommitish"])
    release = json.loads(view.stdout)
    zips = [a["name"] for a in release["assets"] if a["name"].endswith(".zip")]
    sidecars = [a["name"] for a in release["assets"] if a["name"].endswith(".zip.sha256")]
    smoke.check("exactly one ZIP asset and its sidecar", len(zips) == 1 and sidecars == [zips[0] + ".sha256"],
                {"assets": [a["name"] for a in release["assets"]]})
    download.mkdir(parents=True, exist_ok=True)
    for name in (zips[0], sidecars[0]):
        smoke.run(f"download {name}", ["gh", "release", "download", tag, "--repo", REPO, "--pattern", name, "--dir", str(download), "--clobber"])
    return download / zips[0], download / sidecars[0], release


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tag", help="the published release to test, through gh")
    source.add_argument("--archive", type=Path, help="a release ZIP on disk (its .sha256 sidecar beside it, if any)")
    parser.add_argument("--work-dir", type=Path, help="an empty folder for the download, the install and the runs (default: a temporary one outside this checkout)")
    parser.add_argument("--report", type=Path, help="where to write the JSON report (a .md twin is written beside it)")
    parser.add_argument("--skip-suite", action="store_true", help="do not run the shipped test suite in the installed copy")
    parser.add_argument("--keep", action="store_true", help="keep the work folder afterwards")
    args = parser.parse_args(argv)

    # a temporary folder outside this checkout: inside it, the shipped suite would see this repository's tags
    work = args.work_dir.resolve() if args.work_dir else Path(tempfile.mkdtemp(prefix="bpk-smoke-"))
    if work.exists() and any(work.iterdir()):
        raise SystemExit(f"the work folder must be empty: {work}")
    work.mkdir(parents=True, exist_ok=True)
    smoke = Smoke(work)
    started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    report: dict[str, Any] = {"schema": "blueprint_packager.release_smoke/1", "started_at_utc": started.isoformat().replace("+00:00", "Z"),
                              "host": {"platform": platform.platform(), "python": sys.version.split()[0]},
                              "work_dir": str(work) if args.work_dir else "a temporary folder"}
    try:
        # 1-2. the asset and its sidecar
        if args.tag:
            archive, sidecar, release = fetch(smoke, args.tag, work / "download")
            report["release"] = {"tag": release["tagName"], "published_at": release.get("publishedAt"), "assets": [a["name"] for a in release["assets"]]}
        else:
            archive = args.archive.resolve()
            sidecar = archive.with_suffix(".zip.sha256")
            report["release"] = {"tag": None, "archive": str(archive)}
        digest = sha256_file(archive)
        report["asset"] = {"name": archive.name, "bytes": archive.stat().st_size, "sha256": digest}
        if sidecar.is_file():
            recorded = sidecar.read_text(encoding="utf-8").split()
            smoke.check("sidecar matches the ZIP", recorded == [digest, archive.name], {"sidecar": recorded, "sha256": digest})
        else:
            smoke.check("sidecar present", False, f"no sidecar beside {archive.name}")

        # 3. install with the installer; the shipped installer agrees
        installs = work / "installs"
        result = install_release.install_archive(archive, installs, expected_version=args.tag)
        smoke.check("installer verified and installed", result["status"] == "installed", result)
        folder = Path(result["folder"])
        report["install"] = {"folder": folder.name, "version": result["version"]}
        again = smoke.run("shipped installer sees it installed",
                          [sys.executable, "-B", str(folder / "launcher" / "install_release.py"), "--archive", str(archive), "--install-root", str(installs)])
        smoke.check("shipped installer reports already_installed", '"already_installed"' in again.stdout, again.stdout[-300:])

        # 4. the manifest
        manifest = json.loads((folder / "release_manifest.json").read_text(encoding="utf-8"))
        receipt = json.loads((folder / "INSTALL_RECEIPT.json").read_text(encoding="utf-8"))
        provenance = {"tag": manifest.get("tag"), "version": manifest["version"], "build": manifest.get("build")}
        if args.tag:
            smoke.check("manifest names the verified tag for this version",
                        manifest.get("tag") == args.tag == f"v{manifest['version']}" and manifest.get("build", {}).get("tag_verified") is True, provenance)
        else:  # a ZIP on disk may be an unreleased build; say so rather than pretend
            smoke.check("manifest provenance recorded" + ("" if manifest.get("tag") else " (unreleased build, no tag)"), True, provenance)
        tagged_commit = None
        if args.tag:
            probe = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", f"{args.tag}^{{commit}}"], capture_output=True, text=True)
            tagged_commit = probe.stdout.strip() or None
        if tagged_commit:
            smoke.check("manifest commit is the tag's commit", manifest["commit"] == tagged_commit, {"manifest": manifest["commit"], "tag": tagged_commit})
        vendored = manifest.get("vendored_workbench") or {}
        smoke.check("vendored Workbench pin recorded", bool(vendored.get("commit")) and receipt.get("vendored_workbench") == vendored, vendored)
        report["manifest"] = {"version": manifest["version"], "tag": manifest["tag"], "commit": manifest["commit"], "file_count": manifest["file_count"],
                              "vendored_workbench": vendored, "build": manifest.get("build")}

        # 5. the launcher
        doctor = smoke.run("launcher --yes --doctor", launcher(folder, "--yes", "--doctor"))
        smoke.check("doctor reports the engine and the version", "Vendored engine" in doctor.stdout and f"v{manifest['version']}" in doctor.stdout, doctor.stdout[-600:])
        py = venv_python(folder)
        smoke.check("launcher created the venv", py.is_file(), str(py))
        version = smoke.run("bpk.py --version", [str(py), "-B", str(folder / "bpk.py"), "--version"])
        smoke.check("bpk.py reports the version", manifest["version"] in version.stdout, version.stdout.strip())
        report["venv_python"] = smoke.run("venv python version", [str(py), "-c", "import sys; print(sys.version.split()[0])"]).stdout.strip()
        bpk = [str(py), "-B", str(folder / "bpk.py")]

        # 6. a blank, written and read
        blank_dir = work / "blank"
        blank_dir.mkdir()
        blank = blank_dir / "SMK_101__blueprint.docx"
        smoke.run("blank", [*bpk, "blank", str(blank), "--course-number", "SMK 101", "--course-title", "Smoke test course", "--term", "Fall 2026", "--weeks", "2"])
        read_blank = smoke.run("read the blank", [*bpk, "read", str(blank), "--output-dir", str(blank_dir / "read")], ok_codes=(0, 1))
        readiness = json.loads((blank_dir / "read" / "SMK_101__blueprint__readiness.json").read_text(encoding="utf-8"))
        smoke.check("blank read writes a model and a readiness report", (blank_dir / "read" / "SMK_101__blueprint__course_model.json").is_file(),
                    {"readiness": readiness.get("state"), "summary": read_blank.stdout.strip().splitlines()[-2:]})

        # 7. a ready synthetic course: read, build, verify
        ready_dir = work / "ready"
        ready_dir.mkdir()
        course = ready_dir / "SMK_101__course.docx"
        smoke.run("synthetic ready course", [str(py), "-B", "-c",
                  "import sys; sys.path[:0] = [sys.argv[1], sys.argv[2]]; import synth; from pathlib import Path; synth.canonical(Path(sys.argv[3]))",
                  str(folder / "tests"), str(folder), str(course)])
        read_ready = smoke.run("read the ready course", [*bpk, "read", str(course), "--output-dir", str(ready_dir / "read")])
        model = ready_dir / "read" / "SMK_101__course__course_model.json"
        settings = ready_dir / "build_settings.json"
        settings.write_text(json.dumps(SETTINGS, indent=2) + "\n", encoding="utf-8")
        smoke.run("build the ready course", [*bpk, "build", str(model), "--settings", str(settings), "--output-dir", str(ready_dir / "build")])
        packages = list((ready_dir / "build").glob("*.zip"))
        smoke.check("build wrote a package and its receipt", len(packages) >= 1 and (ready_dir / "build" / "component_package_receipt.json").is_file(),
                    [p.name for p in packages])
        package = next(p for p in packages if "pages_refresh" not in p.name)
        verify = smoke.run("verify the ready course", [*bpk, "verify", str(ready_dir / "build"), "--model", str(model)])
        report["ready_course"] = {"read": read_ready.stdout.strip().splitlines()[:1], "package": package.name, "package_sha256": sha256_file(package),
                                  "verify": verify.stdout.strip().splitlines()[-1:]}

        # 8. the Wizard conversion cycle from the installed copy
        wizard_dir = work / "wizard"
        wizard_dir.mkdir()
        wizard = folder / "vendor" / "coursecraft_workbench" / "scripts" / "build_blueprint_bundle.py"
        smoke.run("vendored Wizard extracts the package", [str(py), "-B", str(wizard), str(package), "--label", "smoke", "--output-dir", str(wizard_dir),
                                                           "--no-docx", "--no-syllabus-fetch", "--quiet"])
        bundle = wizard_dir / "smoke__blueprint_bundle"
        authoring = wizard_dir / "smoke__authoring.docx"
        converted = smoke.run("from-wizard", [*bpk, "from-wizard", str(bundle), "--output", str(authoring)])
        status = json.loads(converted.stdout).get("status")
        smoke.check("conversion status", status == "converted", status)
        smoke.run("read the converted blueprint", [*bpk, "read", str(authoring), "--output-dir", str(wizard_dir / "read")])
        model2 = wizard_dir / "read" / "smoke__authoring__course_model.json"
        smoke.run("build the converted blueprint", [*bpk, "build", str(model2), "--settings", str(settings), "--output-dir", str(wizard_dir / "build")])
        verify2 = smoke.run("verify the converted blueprint", [*bpk, "verify", str(wizard_dir / "build"), "--model", str(model2)])
        report["wizard_cycle"] = {"bundle": bundle.name, "conversion": status, "verify": verify2.stdout.strip().splitlines()[-1:]}

        # 9. the shipped suite, in the installed copy
        if not args.skip_suite:
            smoke.run("install the dev requirements", [str(py), "-m", "pip", "install", "--quiet", "-r", str(folder / "requirements-dev.txt")])
            suite = smoke.run("shipped suite", [str(py), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", str(folder / "tests")], cwd=folder, timeout=3600)
            summary = suite.stdout.strip().splitlines()[-1]
            report["suite"] = {"summary": summary}
            smoke.check("suite summary", bool(re.search(r"\d+ passed", summary)) and "failed" not in summary, summary)
        report["passed"] = True
    except (SystemExit, Exception) as exc:  # a failed step, or something the steps did not expect
        report["passed"] = False
        report["failure"] = f"{exc.__class__.__name__}: {exc}"
    finally:
        report["steps"] = smoke.steps
        report["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        out = args.report or work / "smoke_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
        print(markdown(report))
        print(f"report: {out}")
        if not args.keep and not args.work_dir and report.get("passed"):
            shutil.rmtree(work, ignore_errors=True)
    return 0 if report.get("passed") else 1


def markdown(report: dict[str, Any]) -> str:
    lines = [f"# Release smoke test: {report.get('release', {}).get('tag') or report.get('asset', {}).get('name')}", ""]
    lines.append(f"Result: **{'passed' if report.get('passed') else 'FAILED'}**. Started {report['started_at_utc']}, "
                 f"finished {report.get('finished_at_utc', '')}, on {report['host']['platform']} "
                 f"(driver Python {report['host']['python']}, venv Python {report.get('venv_python', '?')}).")
    if report.get("failure"):
        lines += ["", f"Failure: {report['failure']}"]
    asset = report.get("asset", {})
    if asset:
        lines += ["", f"Asset `{asset['name']}`: {asset['bytes']:,} bytes, SHA-256 `{asset['sha256']}`."]
    manifest = report.get("manifest")
    if manifest:
        lines.append(f"Manifest: version {manifest['version']}, tag {manifest['tag']}, commit `{manifest['commit']}`, "
                     f"{manifest['file_count']} files, vendored Workbench `{(manifest.get('vendored_workbench') or {}).get('commit')}`.")
    if report.get("ready_course"):
        lines.append(f"Ready course: package `{report['ready_course']['package']}` SHA-256 `{report['ready_course']['package_sha256']}`; "
                     f"verify: {' '.join(report['ready_course']['verify'])}")
    if report.get("wizard_cycle"):
        lines.append(f"Wizard cycle: {report['wizard_cycle']['conversion']}; verify: {' '.join(report['wizard_cycle']['verify'])}")
    if report.get("suite"):
        lines.append(f"Shipped suite: {report['suite']['summary']}")
    lines += ["", "| Step | Result | Seconds |", "| --- | --- | --- |"]
    for step in report.get("steps", []):
        lines.append(f"| {step['step']} | {'ok' if step['ok'] else 'FAILED'} | {step.get('seconds', '')} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
