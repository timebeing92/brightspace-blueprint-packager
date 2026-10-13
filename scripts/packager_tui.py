#!/usr/bin/env python3
"""Guided one-terminal runner for the Blueprint Packager.

Splash, a workshop check (Python, packages, the vendored engine's hashes, a
quiet update check), a task menu, a commission that remembers your answers,
the build as live stages with the verification shown as a checklist, and a
results card with what to do next. Pure stdlib on top of the packager's own
modules; --plain (or no TTY, NO_COLOR) degrades to text with the same content.

The shape follows the Blueprint Wizard runner's scripts/blueprint_wizard.py
(brightspace-blueprint-runner, commit 85cef27); the tasks are this tool's.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_DIR = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_DIR))

import art  # noqa: E402
import ui  # noqa: E402
import update_check  # noqa: E402

try:
    from blueprint_packager import __version__ as VERSION  # noqa: E402
except Exception:  # the repository is damaged; the workshop will say so
    VERSION = "0.0.0"

MIN_PYTHON = (3, 11)
REQUIRED_MODULES = [("docx", "python-docx"), ("lxml", "lxml"), ("openpyxl", "openpyxl"), ("jsonschema", "jsonschema")]
BPK = REPO_DIR / "bpk.py"
STATE_PATH = REPO_DIR / ".last_run.json"
CACHE_PATH = REPO_DIR / ".update_check.json"
LOGS_DIR = REPO_DIR / "logs"
VENDOR_MANIFEST = REPO_DIR / "vendor" / "coursecraft_workbench" / "MANIFEST.json"
RESTART_EXIT_CODE = 75
TEMPLATES = [("composite-navy", "Composite navy: the default; dark navy brand, calm spacing, arrow dropdown cards"),
             ("bumk515-classic", "BUMK 515 classic: an earlier course's page style")]
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

TASKS = [
    ("first", "First time here: start a blank blueprint and open it",
     "Writes a blueprint with every row in place and the lines each needs, then opens it for you to fill in."),
    ("build", "Build a package from a blueprint",
     "Reads the blueprint, builds the Brightspace package, and reads it back. The usual path."),
    ("dry", "Read a blueprint and report, without building",
     "A dry run: finds everything the reader can see and writes the course model and its report."),
    ("verify", "Verify an existing build folder",
     "Reads a built package back and reports passed, failed, and unexecuted checks."),
    ("resync", "Re-sync a course map after the document changed",
     "Carries a course map from the old export of a blueprint to the new one and reports what moved."),
    ("update", "Check for updates and show the version",
     "Looks at GitHub Releases. Nothing changes unless you say so."),
]
TASK_TITLES = {key: title for key, title, _ in TASKS}

IMPORT_FACTS = [
    "Import the ZIP once, into an empty course.",
    "Importing it again into the same course duplicates everything except the pages.",
    "Page text alone can be refreshed later: upload the folder inside course_pages_refresh.zip through Manage Files.",
]

TERM = ui.Term(plain=True)  # replaced in main() once flags are parsed
PHASE = {"current": 0, "total": 0, "enabled": False}


# --------------------------------------------------------------------------- small helpers
def phase_heading(text: str, context: str = "") -> str:
    if PHASE["enabled"]:
        PHASE["current"] += 1
        head = ui.heading(TERM, text, note=f"{PHASE['current']} of {PHASE['total']}")
    else:
        head = ui.heading(TERM, text)
    return head + ("\n" + ui.note(TERM, context) if context else "")


def parse_path(value: str) -> Path:
    """A path as typed or dragged into the terminal: quotes and escaped spaces are undone."""
    raw = value.strip()
    if not raw:
        raise ValueError("empty path")
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        raw = raw[1:-1]
    windows_path = bool(re.match(r"^[A-Za-z]:[\\/]", raw) or raw.startswith("\\\\"))
    if not windows_path:
        try:
            parts = shlex.split(raw)
            if len(parts) == 1:
                raw = parts[0]
        except ValueError:
            pass
    # Windows backslashes are path separators, not POSIX shell escapes.
    # Preserve a Windows path literally when inspecting it on another platform.
    path = Path(raw).expanduser()
    return path if windows_path and os.name != "nt" else path.resolve()



def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes}m {secs:02d}s"


def safe_label(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "course"


def command_text(cmd: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in cmd)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def python_for_runs() -> str:
    """The interpreter the stages run with: this one, which the launcher made the .venv's."""
    return sys.executable


def open_path(path: Path) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif shutil.which("xdg-open"):
            subprocess.run(["xdg-open", str(path)], check=False)
        else:
            return False
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- remembered answers
def load_state() -> dict:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(update: dict) -> None:
    state = load_state()
    state.update(update)
    state["saved_at_utc"] = update_check.utc_text(update_check.utc_now())
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


# --------------------------------------------------------------------------- the workshop
def python_version_ok(version_info: tuple = sys.version_info) -> bool:
    return tuple(version_info[:2]) >= MIN_PYTHON


def module_missing() -> list[str]:
    missing = []
    for module, package in REQUIRED_MODULES:
        try:
            __import__(module)
        except Exception:
            missing.append(package)
    return missing


def vendor_integrity(manifest_path: Path = VENDOR_MANIFEST) -> dict:
    """Every vendored file present with the manifest's hash. Reports; never repairs."""
    report = {"ok": False, "commit": "", "files": 0, "missing": [], "changed": [], "error": ""}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        report["error"] = f"manifest unreadable: {exc}"
        return report
    root = manifest_path.parent
    report["commit"] = str(manifest.get("commit_short") or str(manifest.get("commit") or "")[:7])
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        if not path.is_file():
            report["missing"].append(entry["path"])
        elif sha256_file(path) != entry["sha256"]:
            report["changed"].append(entry["path"])
        report["files"] += 1
    report["ok"] = not report["missing"] and not report["changed"] and report["files"] > 0
    return report


def install_requirements(assume_yes: bool) -> bool:
    if not ui.confirm(TERM, "Install the Python packages now?", default=True, assume_yes=assume_yes):
        return False
    cmd = [python_for_runs(), "-m", "pip", "install", "-r", str(REPO_DIR / "requirements.txt")]
    print(TERM.dim("  $ " + command_text(cmd)))
    result = subprocess.run(cmd, cwd=str(REPO_DIR), check=False)
    return result.returncode == 0 and not module_missing()


def workshop(args: argparse.Namespace) -> None:
    print(phase_heading("The workshop", "A quick look at the tools before anything is built. Nothing here changes your files."))
    if not python_version_ok():
        print(ui.status_line(TERM, "bad", "Python 3.11 or later", sys.version.split()[0]))
        raise SystemExit("Python 3.11 or later is required. The launcher can install it; see INSTALL_AND_TROUBLESHOOT.md.")
    print(ui.status_line(TERM, "ok", "Python", f"{sys.version.split()[0]}  {TERM.dim(sys.executable)}"))
    in_venv = Path(sys.prefix).resolve() == (REPO_DIR / ".venv").resolve()
    print(ui.status_line(TERM, "ok" if in_venv else "todo", "Private environment (.venv)",
                         "in use" if in_venv else "not in use; packages are read from this Python"))
    missing = module_missing()
    if missing:
        print(ui.status_line(TERM, "bad", "Python packages", "missing " + ", ".join(missing)))
        if not install_requirements(args.yes):
            raise SystemExit("Cannot continue without " + ", ".join(missing) + ". Run: python3 -m pip install -r requirements.txt")
    print(ui.status_line(TERM, "ok", "Python packages", ", ".join(package for _, package in REQUIRED_MODULES)))
    vendor = vendor_integrity()
    if vendor["ok"]:
        print(ui.status_line(TERM, "ok", "Vendored engine", f"{vendor['files']} files at Workbench {vendor['commit']}, every hash verified"))
    else:
        detail = vendor["error"] or (f"{len(vendor['missing'])} missing, {len(vendor['changed'])} changed")
        print(ui.status_line(TERM, "bad", "Vendored engine", detail))
        for name in (vendor["missing"] + vendor["changed"])[:6]:
            print(TERM.dim(f"      {name}"))
        print(TERM.warn("  The vendored files are never edited here. Reinstall the release, or re-pin from the Workbench"))
        print(TERM.warn("  with scripts/check_vendor_drift.py. Builds will still run, but their receipts will not match a release."))
    print(ui.status_line(TERM, "ok", "Blueprint Packager", f"v{VERSION}  {TERM.dim(str(REPO_DIR))}"))


# --------------------------------------------------------------------------- updates
def update_notice(*, force: bool, offer_install: bool) -> bool:
    """Say when a newer release exists. Returns True when the user chose to install and restart."""
    if not force and (os.environ.get("BPK_NO_UPDATE_CHECK") == "1"):
        return False
    status = update_check.check_latest_release(current_version=VERSION, cache_path=CACHE_PATH, force=force)
    if status.state == "no_access":
        if force:
            print(ui.card(TERM, "Update check needs GitHub access", [
                ("Installed", f"v{VERSION}"),
                ("", "The repository is private. Sign in with `gh auth login`, or set GITHUB_TOKEN, then try again."),
            ]))
        else:
            print(TERM.dim("  Update check skipped: no GitHub access (gh auth login, or GITHUB_TOKEN)."))
        return False
    if status.state == "unavailable":
        if force:
            print(ui.card(TERM, "Update check unavailable", [("Installed", f"v{VERSION}"), ("", status.error or "The latest release could not be read.")]))
        else:
            print(TERM.dim("  Update check skipped: " + (status.error or "GitHub could not be reached") + "."))
        return False
    if not status.update_available:
        if force:
            title = "Newer than the latest published release" if status.state == "ahead" else "Up to date"
            print(ui.card(TERM, title, [("Installed", f"v{VERSION}"), ("Latest", f"v{status.latest_version}"), ("Releases", TERM.supporting(status.release_url))]))
        return False
    if not force and not update_check.notice_is_due(CACHE_PATH, latest_version=status.latest_version):
        return False
    rows = [("Installed", f"v{VERSION}"), ("Available", TERM.bold(f"v{status.latest_version}"))]
    if status.release_name and status.release_name != status.latest_tag:
        rows.append(("Release", status.release_name))
    rows.append(("Releases", TERM.supporting(status.release_url)))
    rows.append(("Update", TERM.supporting(update_check.update_command())))
    rows.append(("", "Nothing has been replaced; this version keeps working."))
    print()
    print(ui.card(TERM, "A newer Blueprint Packager is available", rows))
    update_check.mark_notified(CACHE_PATH, latest_version=status.latest_version)
    if offer_install and ui.confirm(TERM, f"Install v{status.latest_version} beside this one and restart into it?", default=False):
        cmd = [python_for_runs(), str(REPO_DIR / "launcher" / "install_release.py"), "--latest", "--expected-version", status.latest_tag]
        print(TERM.dim("  $ " + command_text(cmd)))
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            return True
        print(TERM.warn("  The update was not installed. This version remains active."))
    return False


# --------------------------------------------------------------------------- peeks
def peek_blueprint(path: Path) -> dict:
    """A cheap look inside a blueprint: title, weeks, paragraphs, size."""
    info = {"title": "", "weeks": 0, "week_numbers": [], "assignments": 0, "discussions": 0,
            "paragraphs": 0, "size": 0, "error": ""}
    try:
        info["size"] = path.stat().st_size
        from blueprint_packager.docx_ingest import read_docx
        from blueprint_packager.joins import all_activities
        from blueprint_packager.reader import Reader

        doc = read_docx(path)
        paras = list(doc.paras())
        info["paragraphs"] = sum(1 for p in paras if p.text().strip())
        for p in paras:
            text = p.text().strip()
            if not text:
                continue
            if (p.style or "").lower() == "subtitle":
                info["title"] = text
            elif not info["title"] and (p.style or "").lower() == "title" and text.lower() not in ("blueprint", "course blueprint"):
                info["title"] = text
        if not info["title"]:
            info["title"] = next((p.text().strip() for p in paras
                                  if p.text().strip() and p.text().strip().lower() not in ("blueprint", "course blueprint")), "")
        if not info["title"]:
            info["title"] = next((p.text().strip() for p in paras if p.text().strip()), "")
        # Count interpreted objects, excluding authoring-reference examples and
        # ordinary prose that happens to contain a directive-looking line.
        model = Reader(doc).read()
        info["week_numbers"] = [week["number"] for week in model["weeks"]]
        info["weeks"] = len(info["week_numbers"])
        for activity in all_activities(model):
            if activity["type"] in ("assignment", "discussion"):
                info["assignments" if activity["type"] == "assignment" else "discussions"] += 1
    except Exception as exc:  # a peek never stops the run
        info["error"] = str(exc).splitlines()[0][:120]
    return info



def verification_counts(report: dict) -> dict[str, int]:
    counts = {key: 0 for key in ("passed", "failed", "not_run", "not_applicable")}
    summary = report.get("summary")
    if isinstance(summary, dict) and all(isinstance(summary.get(key), int) for key in counts):
        return {key: summary[key] for key in counts}
    for check in report.get("checks", []):
        status = check.get("status", "passed" if check.get("passed") else "failed")
        counts[status if status in counts else "not_run"] += 1
    return counts

def peek_build(folder: Path) -> dict:
    info = {"title": "", "zip": "", "sha256": "", "bytes": 0, "verified": None,
            "verification_passed": False, "preview": False, "authoring_state": "unknown", "error": ""}
    try:
        receipt = json.loads((folder / "component_package_receipt.json").read_text(encoding="utf-8"))
        info["title"] = str(receipt.get("package_title") or "")
        zip_info = receipt.get("zip") or {}
        info["zip"] = str(zip_info.get("path") or "")
        info["sha256"] = str(zip_info.get("sha256") or "")
        info["bytes"] = int(zip_info.get("bytes") or 0)
        extension = receipt.get("extensions", {})
        info["preview"] = extension.get("build_mode") == "preview"
        info["authoring_state"] = extension.get("authoring_state", "unknown")
        report = folder / "verification_report.json"
        if report.is_file():
            data = json.loads(report.read_text(encoding="utf-8"))
            counts = verification_counts(data)
            info["verified"] = "; ".join(f"{counts[key]} {key.replace('_', ' ')}"
                                           for key in ("passed", "failed", "not_run", "not_applicable") if counts[key])
            info["verification_passed"] = data.get("passed") is True
    except (OSError, ValueError) as exc:
        info["error"] = str(exc).splitlines()[0][:120]
    return info


def ask_path(prompt: str, *, default: str = "", must_exist: bool = True, kind: str = "file") -> Path:
    """Drag-and-drop friendly path prompt; loops until a usable path is given."""
    print(TERM.dim(f"  Drag the {kind} into this window, or type its path, then press Return."))
    while True:
        try:
            reply = ui.prompt_text(TERM, prompt, default=default)
            path = parse_path(reply)
        except ValueError:
            print(TERM.dim("    Please enter a path."))
            continue
        if must_exist and not path.exists():
            print(TERM.warn(f"    Not found: {path}"))
            continue
        return path


def pick_blueprint(default: str = "", *, revisit: bool = False) -> Path:
    print(ui.heading(TERM, "The blueprint") if revisit else phase_heading("The blueprint", "The Word document the course is written in."))
    while True:
        path = ask_path("Blueprint (.docx)", default=default, kind="blueprint")
        peek = peek_blueprint(path)
        rows = [("File", path.name), ("Size", human_size(peek["size"]))]
        if peek["error"]:
            rows.append(("", TERM.warn("Could not read it as a Word file: " + peek["error"])))
        else:
            if peek["title"]:
                rows.append(("Title", TERM.bold(peek["title"][:70])))
            rows.append(("Weeks", str(peek["weeks"]) if peek["weeks"] else TERM.warn("none found; is the frame at Heading 1?")))
            rows.append(("Activities", f"{peek['assignments']} assignments; {peek['discussions']} discussions"))
            rows.append(("Paragraphs", str(peek["paragraphs"])))
        print()
        print(ui.card(TERM, "A look inside", rows))
        if ui.confirm(TERM, "Is this the right blueprint?", default=True):
            return path
        default = ""


# --------------------------------------------------------------------------- settings
def derive_weeks(start: str, count: int) -> dict[str, list[str]]:
    """Consecutive seven-day weeks from the first day of Week 1."""
    first = _dt.date.fromisoformat(start)
    weeks = {}
    for index in range(count):
        a = first + _dt.timedelta(days=7 * index)
        b = a + _dt.timedelta(days=6)
        weeks[str(index + 1)] = [a.isoformat(), b.isoformat()]
    return weeks


def make_settings(answers: dict) -> dict:
    """A build settings file the builder accepts, from a few answers. Everything is editable afterwards."""
    label = safe_label(answers.get("label") or (answers.get("course_label") or "").split("·")[0].strip() or answers.get("package_title") or "course")
    settings: dict = {
        "schema": "blueprint_packager.build_settings/0.1",
        "package": {
            "title": answers["package_title"],
            "manifest_identifier": answers.get("manifest_identifier") or "D2L_" + re.sub(r"[^A-Z0-9]+", "_", label.upper()).strip("_"),
            "base_resource_code": answers.get("base_resource_code") or str(uuid.uuid4()).upper(),
            "zip_name": f"{label}__package.zip",
        },
        "template": answers.get("template") or "composite-navy",
        "fragment_styles": "template",
    }
    if answers.get("course_label"):
        settings["package"]["course_label"] = answers["course_label"]
    if answers.get("week1_start") and int(answers.get("weeks") or 0) > 0:
        settings["calendar"] = {
            "timezone": answers.get("timezone") or "America/New_York",
            "weeks": derive_weeks(answers["week1_start"], int(answers["weeks"])),
            "due_time": "23:59",
            "rules": {
                "assignment": {"day": answers.get("assignment_day") or "Sunday"},
                "discussion_initial": {"day": answers.get("initial_day") or "Friday"},
                "discussion_response": {"day": answers.get("response_day") or "Sunday"},
            },
        }
    return settings



def unique_path(path: Path) -> Path:
    candidate, index = path, 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}__{index}{path.suffix}")
        index += 1
    return candidate


def validate_calendar(spec: dict, week_numbers: list[int] | None = None) -> dict:
    from blueprint_packager.calendar import Calendar

    if not isinstance(spec, dict) or not isinstance(spec.get("weeks"), dict) or not spec["weeks"]:
        raise ValueError("Calendar needs a nonempty weeks mapping.")
    try:
        calendar = Calendar(spec)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid calendar: {exc}") from exc
    if any(number < 1 for number in calendar.weeks):
        raise ValueError("Calendar week numbers must be positive.")
    if len(calendar.weeks) != len(spec["weeks"]):
        raise ValueError("Calendar week numbers must be unique.")
    missing = sorted(set(week_numbers or []) - set(calendar.weeks))
    if missing:
        raise ValueError(f"Calendar is missing blueprint weeks: {missing}")
    previous_end = None
    for number, (start, end) in sorted(calendar.weeks.items()):
        if previous_end is not None and start <= previous_end:
            raise ValueError(f"Week {number} overlaps or precedes the previous week.")
        previous_end = end
    return spec


def calendar_from_file(path: Path, existing: dict | None = None, timezone: str | None = None) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Calendar file must contain a weeks mapping or a complete calendar object.")
    payload = payload.get("calendar", payload)
    if not isinstance(payload, dict):
        raise ValueError("Calendar must be a JSON object.")
    if "weeks" in payload:
        spec = copy.deepcopy(payload)
    else:
        spec = copy.deepcopy(existing or {})
        spec["weeks"] = payload
    spec.setdefault("timezone", timezone or (existing or {}).get("timezone") or "America/New_York")
    if timezone:
        spec["timezone"] = timezone
    return validate_calendar(spec)


def review_calendar(spec: dict, *, interactive: bool, week_numbers: list[int] | None = None) -> dict:
    """Show every configured boundary; edits never shift other weeks implicitly."""
    spec = copy.deepcopy(validate_calendar(spec, week_numbers))
    while True:
        rows = [("Time zone", spec["timezone"])]
        for number, dates in sorted(spec["weeks"].items(), key=lambda item: int(item[0])):
            start, end = map(_dt.date.fromisoformat, dates)
            rows.append((f"Week {number}", f"{start.isoformat()} ({start:%a}) to {end.isoformat()} ({end:%a}); {(end-start).days + 1} days"))
        rules = spec.get("rules", {})
        for role, rule in rules.items():
            rows.append((role.replace("_", " "), str(rule.get("day", ""))
                         + (f"; final week: {rule['last_week_day']}" if rule.get("last_week_day") else "")))
        if not rules:
            rows.append(("Due rules", "none configured; week boundaries alone do not assign due dates"))
        print(ui.card(TERM, "Review the term calendar", rows))
        if not interactive:
            return spec
        reply = ui.prompt_text(TERM, "Return accepts these dates; enter a week number to edit", default="").strip()
        if not reply:
            return spec
        if reply not in spec["weeks"]:
            print(TERM.warn("  Enter a listed week number."))
            continue
        candidate = copy.deepcopy(spec)
        old = spec["weeks"][reply]
        candidate["weeks"][reply] = [ui.prompt_text(TERM, "First day (YYYY-MM-DD)", default=old[0]),
                                       ui.prompt_text(TERM, "Last day (YYYY-MM-DD)", default=old[1])]
        try:
            validate_calendar(candidate, week_numbers)
        except (ValueError, TypeError, KeyError) as exc:
            print(TERM.warn(f"  Calendar unchanged: {exc}"))
            continue
        spec = candidate


def prepare_calendar_settings(path: Path, args: argparse.Namespace, out_dir: Path, peek: dict) -> Path:
    original = json.loads(path.read_text(encoding="utf-8"))
    settings = copy.deepcopy(original)
    if args.calendar_file:
        settings["calendar"] = calendar_from_file(parse_path(args.calendar_file), settings.get("calendar"), args.timezone)
    if settings.get("calendar"):
        settings["calendar"] = review_calendar(settings["calendar"], interactive=not args.yes,
                                                week_numbers=peek.get("week_numbers"))
    if settings == original:
        return path
    # Moving a settings copy must not change what relative source paths mean.
    if settings.get("workbench_scripts") and not Path(settings["workbench_scripts"]).is_absolute():
        settings["workbench_scripts"] = str((path.parent / settings["workbench_scripts"]).resolve())
    for quiz in settings.get("carried_quizzes", []):
        if quiz.get("source_dir") and not Path(quiz["source_dir"]).is_absolute():
            quiz["source_dir"] = str((path.parent / quiz["source_dir"]).resolve())
    out_dir.mkdir(parents=True, exist_ok=True)
    prepared = unique_path(out_dir / "build_settings__reviewed.json")
    prepared.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(ui.status_line(TERM, "ok", "Reviewed settings copy", str(prepared)))
    return prepared


def show_readiness(model_path: Path, settings: dict | None = None) -> dict:
    from blueprint_packager.authoring import readiness

    model = json.loads(model_path.read_text(encoding="utf-8"))
    report = readiness(model, settings)
    pending = [finding for finding in report["findings"] if finding["status"] == "unresolved"]
    retained = [finding for finding in report["findings"] if finding["status"] == "retained"]
    rows = [("State", "ready for packaging" if report["ready"] else "draft"),
            ("Unfinished", str(len(pending))), ("Explicitly retained", str(len(retained)))]
    for finding in pending[:8]:
        rows.append((finding["where"], finding["message"]))
    if len(pending) > 8:
        rows.append(("", f"{len(pending) - 8} more items are listed in the readiness report."))
    readiness_path = model_path.with_name(model_path.name.replace("__course_model.json", "__readiness.json"))
    if readiness_path.is_file():
        rows.append(("Source report", str(readiness_path)))
    print(ui.card(TERM, "Authoring readiness", rows))
    return report

def guess_course_label(title: str) -> str:
    """'MBA 620 Marketing - Fall B 2026 ...' -> 'MBA 620 · Marketing'."""
    match = re.match(r"\s*([A-Z]{2,5}\s?\d{3}[A-Z]?)\s*[-–:·]?\s*([A-Za-z][^-–:·(]*)", title or "")
    if not match:
        return ""
    number, name = match.group(1).strip(), match.group(2).strip()
    name = re.split(r"\s+(Fall|Spring|Summer|Winter)\b", name)[0].strip()
    return f"{number} · {name}" if name else number


def ask_settings(blueprint: Path, peek: dict, out_dir: Path, remembered: dict, args: argparse.Namespace) -> Path:
    """Pick a settings file: an existing one, the remembered one, or make one from a few answers."""
    options = [("make", "Make one for me: a few questions, then a settings file next to the build")]
    if remembered.get("settings") and Path(remembered["settings"]).is_file():
        options.insert(0, ("last", f"Use the last one: {Path(remembered['settings']).name}"))
    options.append(("file", "Use an existing build settings file (drag it in)"))
    default = "last" if options[0][0] == "last" else "make"
    choice = ui.choose(TERM, "Build settings:", options, default=default)
    if choice == "last":
        return Path(remembered["settings"])
    if choice == "file":
        return ask_path("Settings file (.json)", default=remembered.get("settings", ""), kind="settings file")
    print(TERM.dim("  Return keeps the suggestion. Everything here can be changed in the file later."))
    title_default = peek.get("title") or remembered.get("package_title") or blueprint.stem
    answers = {
        "package_title": ui.prompt_text(TERM, "Package title (the course title in Brightspace)", default=title_default),
    }
    answers["course_label"] = ui.prompt_text(TERM, "Course label above each page title, e.g. MBA 620 · Marketing",
                                             default=remembered.get("course_label") or guess_course_label(answers["package_title"]))
    answers["label"] = safe_label(answers["course_label"].split("·")[0] or answers["package_title"])
    answers["manifest_identifier"] = ui.prompt_text(TERM, "Manifest identifier", default=remembered.get("manifest_identifier") or ("D2L_" + re.sub(r"[^A-Z0-9]+", "_", answers["label"].upper()).strip("_")))
    answers["template"] = ui.choose(TERM, "Page template:", TEMPLATES, default=remembered.get("template") or "composite-navy")
    print(TERM.dim("  Dates: the blueprint says 'due Sunday'; the term calendar turns that into real dates."))
    if ui.confirm(TERM, "Add a term calendar now?", default=bool(remembered.get("week1_start"))):
        answers["timezone"] = ui.prompt_text(TERM, "Time zone", default=remembered.get("timezone") or "America/New_York")
        while True:
            start = ui.prompt_text(TERM, "First day of Week 1 (YYYY-MM-DD)", default=remembered.get("week1_start", ""))
            try:
                _dt.date.fromisoformat(start)
                break
            except ValueError:
                print(TERM.dim("    A date like 2026-10-28, please."))
        answers["week1_start"] = start
        answers["weeks"] = int(ui.prompt_text(TERM, "Number of weeks", default=str(remembered.get("weeks") or peek.get("weeks") or 8)) or 8)
        print(TERM.dim("  Proposed boundaries are consecutive seven-day weeks. Review and edit them before the build."))
        print(TERM.dim("  Suggested due rules: assignments/responses Sunday; initial posts Friday."))
        for key, label, default_day in (("assignment_day", "Assignment due day", "Sunday"),
                                         ("initial_day", "Discussion initial-post day", "Friday"),
                                         ("response_day", "Discussion response day", "Sunday")):
            answers[key] = ui.prompt_text(TERM, label + " (weekday, first_day, or last_day)", default=default_day)
    settings = make_settings(answers)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(out_dir / "build_settings.json")
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(ui.status_line(TERM, "ok", "Settings written", str(path)))
    save_state({k: v for k, v in answers.items() if k in ("package_title", "course_label", "manifest_identifier", "template", "timezone", "week1_start", "weeks")})
    return path


# --------------------------------------------------------------------------- running stages
def open_log(task: str) -> tuple[Path, object]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = LOGS_DIR / f"packager_{stamp}_{task}.log"
    return path, path.open("x", encoding="utf-8")


CHECK_RE = re.compile(r"^\s*\[(pass|FAIL|passed|failed|not_run|not_applicable)\]\s+(.*?):\s*(.*)$")


def run_stage(label: str, cmd: list[str], log, *, checklist: bool = False, context: str = "") -> tuple[int, list[str], float]:
    """Run one bpk stage with live, dimmed output; a verify stage renders its checks as a checklist."""
    print()
    print("  " + TERM.bold(label) + ("  " + TERM.dim(context) if context else ""))
    print(TERM.dim("  $ " + command_text(cmd)))
    log.write(f"\n== {label}\n$ {command_text(cmd)}\n")
    started = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=str(REPO_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    lines: "queue.Queue[str | None]" = queue.Queue()

    def _reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=_reader, daemon=True).start()
    recent: list[str] = []
    spin = 0
    try:
        while True:
            try:
                line = lines.get(timeout=0.1)
            except queue.Empty:
                if not TERM.plain:
                    spin += 1
                    sys.stdout.write("\r  " + TERM.dim(ui.SPINNER[spin % len(ui.SPINNER)] + f" {time.monotonic() - started:5.1f}s"))
                    sys.stdout.flush()
                continue
            if line is None:
                break
            log.write(line)
            text = line.rstrip()
            if not text:
                continue
            recent.append(text)
            recent = recent[-20:]
            if not TERM.plain:
                sys.stdout.write("\r\x1b[2K")
            match = CHECK_RE.match(text) if checklist else None
            if match:
                status, name, detail = match.groups()
                if status in ("not_run", "not_applicable"):
                    print(ui.status_line(TERM, "bad" if status == "not_run" else "todo", name,
                                         status.replace("_", " ") + ": " + detail[:90]))
                else:
                    print(ui.check_line(TERM, status in ("pass", "passed"), name, detail[:90]))
            elif text.startswith("  ERROR"):
                print(TERM.bad("  " + text.strip()[:TERM.width - 4]))
            else:
                print(TERM.dim("  " + text[:TERM.width - 4]))
        code = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.write("\n[canceled by user]\n")
        raise
    elapsed = time.monotonic() - started
    if not TERM.plain:
        sys.stdout.write("\r\x1b[2K")
    status = "ok" if code == 0 else "bad"
    print(ui.status_line(TERM, status, label, f"{format_duration(elapsed)}" + ("" if code == 0 else f"  exit {code}")))
    log.write(f"== exit {code} after {elapsed:.1f}s\n")
    return code, recent, elapsed


def failure_card(label: str, code: int, recent: list[str], log_path: Path) -> None:
    rows: list[tuple[str, str]] = [("Failed stage", TERM.bold(label)), ("Exit code", str(code)), ("", "")]
    seen: set[str] = set()
    for line in recent[-10:]:
        if line not in seen:
            seen.add(line)
            rows.append(("", TERM.dim(line[:TERM.width - 8])))
    rows.append(("", ""))
    rows.append(("Full log", str(log_path)))
    print()
    print(ui.card(TERM, TERM.bad("The build stopped"), rows))
    if code == 1:
        print(TERM.dim("  Exit 1 means the stage ran and found problems in the blueprint or the package; the lines above name them."))
    print(TERM.dim("  Fix what they name and run again; your answers are remembered."))


# --------------------------------------------------------------------------- the tasks
def model_path_for(out_dir: Path, stem: str) -> Path:
    return out_dir / "model" / f"{stem}__course_model.json"


def task_build(args: argparse.Namespace, *, dry: bool) -> int:
    remembered = load_state()
    use_last = False
    if args.yes:
        use_last = True
    elif remembered.get("blueprint") and Path(remembered["blueprint"]).is_file() and not args.blueprint:
        use_last = ui.confirm(TERM, f"Build it again from {Path(remembered['blueprint']).name}, with the same answers?", default=True)
    if args.blueprint:
        blueprint = parse_path(args.blueprint)
        if not blueprint.is_file():
            raise SystemExit(f"Blueprint not found: {blueprint}")
    elif use_last and remembered.get("blueprint"):
        blueprint = Path(remembered["blueprint"])
        if not blueprint.is_file():
            raise SystemExit("No remembered blueprint to build again; run without --yes.")
    elif args.yes:
        raise SystemExit("No blueprint was supplied or remembered; pass --blueprint with --yes.")
    else:
        blueprint = pick_blueprint(remembered.get("blueprint", ""))
    peek = peek_blueprint(blueprint)
    stem = safe_label(blueprint.stem)

    if not use_last or args.output_dir:
        print(phase_heading("The commission", "Where the results go, and the settings the build needs."))
    out_default = args.output_dir or remembered.get("output_dir") or str(blueprint.parent / f"{stem}__packager")
    if args.yes or (use_last and not args.output_dir):
        out_dir = Path(out_default)
    else:
        out_dir = parse_path(ui.prompt_text(TERM, "Output folder", default=out_default))
    settings_path: Path | None = None
    if dry and args.settings:
        settings_path = parse_path(args.settings)
        if not settings_path.is_file():
            raise SystemExit(f"Settings file not found: {settings_path}")
    if not dry:
        if args.settings:
            settings_path = parse_path(args.settings)
        elif args.yes or use_last:
            if not remembered.get("settings") or not Path(remembered["settings"]).is_file():
                raise SystemExit("No remembered settings file; run without --yes to make one.")
            settings_path = Path(remembered["settings"])
        else:
            settings_path = ask_settings(blueprint, peek, out_dir, remembered, args)
        if not settings_path.is_file():
            raise SystemExit(f"Settings file not found: {settings_path}")

    rows = [("1. Blueprint", str(blueprint)), ("2. Output folder", str(out_dir))]
    if not dry:
        rows.append(("3. Settings", str(settings_path)))
    rows.append(("Stages", "read → report" if dry else "read → build → verify"))
    if not args.yes:
        while True:
            print()
            print(ui.card(TERM, "Review run settings" if not dry else "Review dry-run settings", rows))
            try:
                reply = input(f"  {TERM.accent('?')} Press Return to run, or a number to change: ").strip()
            except EOFError:
                print("")
                break
            if not reply:
                break
            if reply == "1":
                blueprint = pick_blueprint(str(blueprint), revisit=True)
                peek = peek_blueprint(blueprint)
                stem = safe_label(blueprint.stem)
                rows[0] = ("1. Blueprint", str(blueprint))
            elif reply == "2":
                out_dir = parse_path(ui.prompt_text(TERM, "Output folder", default=str(out_dir)))
                rows[1] = ("2. Output folder", str(out_dir))
            elif reply == "3" and not dry:
                settings_path = ask_settings(blueprint, peek, out_dir, remembered, args)
                rows[2] = ("3. Settings", str(settings_path))
            else:
                print(TERM.dim(f"    Enter 1-{3 if not dry else 2}, or Return to run."))
    if settings_path is not None and not dry:
        settings_path = prepare_calendar_settings(settings_path, args, out_dir, peek)
    save_state({"blueprint": str(blueprint), "output_dir": str(out_dir), **({"settings": str(settings_path)} if settings_path else {})})

    print(phase_heading("The build" if not dry else "The reading", "Each stage reads the one before it and writes its own records, so a problem is found where it happened."))
    log_path, log = open_log("dry" if dry else "build")
    py = python_for_runs()
    model = model_path_for(out_dir, stem)
    build_dir = out_dir / "build"
    total = 0.0
    try:
        code, recent, elapsed = run_stage("Read the blueprint", [py, str(BPK), "read", str(blueprint), "--output-dir", str(out_dir / "model"), "--label", stem], log,
                                          context="weeks, pages, activities, rubrics, joins, diagnostics")
        total += elapsed
        effective_settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path else {}
        for key, selected in (("retain_video_placeholders", args.retain_video_placeholder), ("video_link_fallbacks", args.video_link_fallback)):
            if selected:
                effective_settings[key] = list(dict.fromkeys(selected))
        readiness = show_readiness(model, effective_settings) if model.is_file() else None
        if code != 0:
            failure_card("Read the blueprint", code, recent, log_path)
            return code
        if dry:
            report_rows = [("Course model", str(model)), ("Readable report", str(out_dir / "model" / f"{stem}__normalized.md"))]
            summary = next((line for line in recent if line.startswith("model:")), "")
            if summary:
                report_rows.insert(0, ("Read", summary[len("model: "):]))
            report_rows.append(("Run log", TERM.dim(str(log_path))))
            print()
            print(ui.card(TERM, "The blueprint reads clean" if readiness and readiness["ready"] else "The blueprint is a draft", report_rows))
            next_steps(["Review readiness findings and the readable report.", "Complete unfinished fields, or use --preview to inspect a draft package."], out_dir)
            return 0
        assert settings_path is not None
        preview = args.preview or effective_settings.get("build_mode") == "preview"
        if readiness and not readiness["ready"] and not preview:
            if args.yes:
                print(TERM.warn("  Build stopped: complete the readiness findings, or explicitly rerun with --preview."))
                return 1
            preview = ui.confirm(TERM, "Build a draft preview for inspection?", default=False)
            if not preview:
                return 1
        build_command = [py, str(BPK), "build", str(model), "--settings", str(settings_path), "--output-dir", str(build_dir), "--force"]
        if preview:
            build_command.append("--preview")
        for flag, titles in (("--retain-video-placeholder", args.retain_video_placeholder), ("--video-link-fallback", args.video_link_fallback)):
            for title in titles:
                build_command.extend([flag, title])
        code, recent, elapsed = run_stage("Build the package", build_command, log,
                                          context="pages from the template, descriptions, dates, checklists, grade items, rubrics")
        total += elapsed
        if code != 0:
            failure_card("Build the package", code, recent, log_path)
            return code
        code, recent, elapsed = run_stage("Verify the package", [py, str(BPK), "verify", str(build_dir), "--model", str(model)], log,
                                          checklist=True, context="the package read back with independent readers and compared with the model")
        total += elapsed
        if code != 0:
            failure_card("Verify the package", code, recent, log_path)
            if preview:
                results_card(build_dir, log_path, total)
                next_steps(build_next_steps(build_dir), build_dir)
            return code
    finally:
        log.close()
    results_card(build_dir, log_path, total)
    next_steps(build_next_steps(build_dir), build_dir, primary=True)
    return 0


def results_card(build_dir: Path, log_path: Path, elapsed: float) -> None:
    peek = peek_build(build_dir)
    rows: list[tuple[str, str]] = [("Built in", format_duration(elapsed))]
    if peek["title"]:
        rows.append(("Package", TERM.bold(peek["title"])))
    zip_path = build_dir / peek["zip"] if peek["zip"] else None
    if zip_path and zip_path.is_file():
        use = "draft preview — review only" if peek["preview"] or peek["authoring_state"] == "draft" else "local package — review before import"
        rows.append(("ZIP", TERM.bold(zip_path.name) + f"  {TERM.dim(human_size(zip_path.stat().st_size))}  " + use))
        rows.append(("SHA-256", TERM.supporting(peek["sha256"])))
    refresh = build_dir / "course_pages_refresh.zip"
    if refresh.is_file():
        rows.append(("Pages refresh", f"{refresh.name}  {TERM.dim(human_size(refresh.stat().st_size))}"))
    for label, name in (("Readiness", "readiness_report.json"), ("Object map", "object_map.md"), ("Verification", "verification_report.md"), ("Receipt", "component_package_receipt.json")):
        if (build_dir / name).is_file():
            detail = f"  {peek['verified']}" if name.startswith("verification") and peek["verified"] else ""
            rows.append((label, name + detail))
    rows.append(("", ""))
    rows.append(("Folder", str(build_dir)))
    rows.append((TERM.dim("Run log"), TERM.dim(str(log_path))))
    print()
    title = "The draft preview is built" if peek["preview"] or peek["authoring_state"] == "draft" else "The package is built"
    if (peek["preview"] or peek["authoring_state"] == "draft") and not peek["verification_passed"]:
        title = "Draft preview built; checks need attention"
    rows.append(("Evidence", "Local checks only; no Brightspace import performed."))
    print(ui.card(TERM, title, rows))



def build_next_steps(build_dir: Path) -> list[str]:
    peek = peek_build(build_dir)
    if peek["preview"] or peek["authoring_state"] == "draft":
        return ["Open the generated pages and inspect the draft presentation.",
                "Resolve the unfinished items listed in readiness_report.json.",
                "Build again without --preview when authoring is complete; this preview is for review."]
    return ["Review the local verification report and package contents before tenant validation.", *IMPORT_FACTS]

def next_steps(steps: list[str], folder: Path, *, primary: bool = False) -> None:
    rows = [("", f"{index}. {text}") for index, text in enumerate(steps, start=1)]
    print()
    print(ui.card(TERM, "What to do next", rows))
    if TERM.plain or not sys.stdin.isatty():
        return
    if folder.exists() and ui.confirm(TERM, "Open the folder?", default=primary):
        open_path(folder)


def task_first(args: argparse.Namespace) -> int:
    print(phase_heading("The commission", "Name the course and choose its activity scaffold."))
    remembered = load_state()

    def answer(value, prompt, key, default=""):
        if value is not None:
            return value
        suggestion = remembered.get(key, default)
        return suggestion if args.yes else ui.prompt_text(TERM, prompt, default=str(suggestion))

    number = answer(args.course_number, "Course number, e.g. NEW 101", "course_number", "NEW 101")
    title = answer(args.course_title, "Course title", "course_title", "Course Title")
    term = answer(args.term, "Term, e.g. Spring A 2027", "term", "Term")
    weeks = int(answer(args.weeks, "Number of weeks", "weeks", 8) or 8)
    if weeks < 1:
        raise ValueError("Number of weeks must be positive.")
    assignments = int(answer(args.assignments_per_week, "Assignments per week (0 or more)", "assignments_per_week", 1))
    discussions = int(answer(args.discussions_per_week, "Discussions per week (0 or more)", "discussions_per_week", 1))
    if min(assignments, discussions) < 0:
        raise ValueError("Activity counts cannot be negative.")
    overrides = list(args.week_count)
    if not args.yes and not overrides:
        value = ui.prompt_text(TERM, "Optional weekly overrides, e.g. 2:3:1 4:0:2 (week:assignments:discussions)", default="")
        overrides = value.split()
    for value in overrides:
        match = re.fullmatch(r"([1-9][0-9]*):([0-9]+):([0-9]+)", value)
        if not match or not 1 <= int(match[1]) <= weeks:
            raise ValueError(f"Invalid weekly count '{value}'; use W:A:D with a week from 1 to {weeks}.")
    worked_example = args.worked_example
    if not args.yes and not worked_example:
        worked_example = ui.confirm(TERM, "Include a worked example with sample points and rubrics?", default=False)
    label = safe_label(number or title or "course") + "__" + safe_label(term or "Term")
    out_default = args.output_dir or remembered.get("blank_dir") or str(Path.home() / "Documents" / "blueprints")
    out_dir = parse_path(out_default) if args.yes else parse_path(ui.prompt_text(TERM, "Folder to write it in", default=out_default))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{label}__blueprint.docx"
    if target.exists() and not args.force:
        target = unique_path(target)
        print(ui.status_line(TERM, "todo", "Existing blueprint preserved", f"new file: {target.name}"))
    save_state({"course_number": number, "course_title": title, "term": term, "weeks": weeks,
                "assignments_per_week": assignments, "discussions_per_week": discussions, "blank_dir": str(out_dir)})

    print(phase_heading("The writing", "One stage: the blank blueprint."))
    log_path, log = open_log("blank")
    try:
        command = [python_for_runs(), str(BPK), "blank", str(target), "--course-number", number or "NEW 101",
                   "--course-title", title or "Course Title", "--term", term or "Term", "--weeks", str(weeks),
                   "--assignments-per-week", str(assignments), "--discussions-per-week", str(discussions)]
        for value in overrides:
            command.extend(["--week-count", value])
        if worked_example:
            command.append("--worked-example")
        if args.force:
            command.append("--force")
        code, recent, _ = run_stage("Write the blank blueprint", command, log)
    finally:
        log.close()
    if code != 0:
        failure_card("Write the blank blueprint", code, recent, log_path)
        return code
    print()
    print(ui.card(TERM, "The blueprint is ready to fill in", [("File", TERM.bold(str(target))), ("Weeks", str(weeks)), ("", "The scaffold is a draft. Readiness checks identify fields to complete before packaging.")]))
    next_steps(["Fill in Week 1's six rows: Overview, Learning Objectives, Resources, Assignments, Discussions, Checklist.",
                "Keep the frame at Heading 1 and start content at Heading 2; see docs/AUTHORING_GUIDE.md.",
                "Use Read a blueprint for readiness findings, or Build with --preview to inspect unfinished content."], out_dir)
    if not TERM.plain and sys.stdin.isatty() and ui.confirm(TERM, "Open the blueprint in Word now?", default=True):
        open_path(target)
    save_state({"blueprint": str(target)})
    return 0


def task_verify(args: argparse.Namespace) -> int:
    print(phase_heading("The commission", "A build folder, and the course model it was built from."))
    remembered = load_state()
    build_dir = parse_path(args.build_dir) if args.build_dir else ask_path("Build folder", default=remembered.get("build_dir", ""), kind="build folder")
    peek = peek_build(build_dir)
    rows = [("Folder", str(build_dir))]
    if peek["error"]:
        rows.append(("", TERM.warn("No receipt found here: " + peek["error"])))
    else:
        rows += [("Package", peek["title"]), ("ZIP", f"{peek['zip']}  {TERM.dim(human_size(peek['bytes']))}"), ("SHA-256", TERM.supporting(peek["sha256"][:16] + "…"))]
        if peek["verified"]:
            rows.append(("Last verified", peek["verified"] + " checks"))
    print()
    print(ui.card(TERM, "A look inside", rows))
    guess = ""
    model_guess = sorted((build_dir.parent / "model").glob("*__course_model.json")) if (build_dir.parent / "model").is_dir() else []
    if model_guess:
        guess = str(model_guess[0])
    model = parse_path(args.model) if args.model else ask_path("Course model (.json)", default=remembered.get("model", guess), kind="course model")
    save_state({"build_dir": str(build_dir), "model": str(model)})
    print(phase_heading("The checks", "Read-back checks with explicit pass, failure, and not-run status."))
    log_path, log = open_log("verify")
    try:
        code, recent, elapsed = run_stage("Verify the package", [python_for_runs(), str(BPK), "verify", str(build_dir), "--model", str(model)], log, checklist=True)
    finally:
        log.close()
    if code != 0:
        failure_card("Verify the package", code, recent, log_path)
        if peek["preview"] or peek["authoring_state"] == "draft":
            results_card(build_dir, log_path, elapsed)
            next_steps(build_next_steps(build_dir), build_dir)
        return code
    results_card(build_dir, log_path, elapsed)
    next_steps(build_next_steps(build_dir), build_dir)
    return 0


def task_resync(args: argparse.Namespace) -> int:
    print(phase_heading("The commission", "The export the map was written against, the new export, and the map itself."))
    remembered = load_state()
    old = parse_path(args.old) if args.old else ask_path("Old export (.docx), the one the map is bound to", default=remembered.get("old", ""), kind="old blueprint")
    new = parse_path(args.new) if args.new else ask_path("New export (.docx)", default=remembered.get("new", ""), kind="new blueprint")
    course_map = parse_path(args.map) if args.map else ask_path("Course map (.json)", default=remembered.get("map", ""), kind="course map")
    out_default = args.output_dir or str(course_map.with_name(course_map.stem + "__rebased.json"))
    out = Path(out_default) if args.yes else parse_path(ui.prompt_text(TERM, "Write the carried map to", default=out_default))
    save_state({"old": str(old), "new": str(new), "map": str(course_map)})
    print(phase_heading("The re-sync", "Paragraphs are lined up by their words; every id the map uses is translated."))
    log_path, log = open_log("resync")
    report = out.with_suffix(".report.md")
    try:
        code, recent, _ = run_stage("Carry the course map", [python_for_runs(), str(BPK), "rebase-map", str(old), str(new), "--map", str(course_map), "--output", str(out), "--report", str(report)], log)
    finally:
        log.close()
    if code != 0:
        failure_card("Carry the course map", code, recent, log_path)
        return code
    print()
    print(ui.card(TERM, "The map follows the document", [("Carried map", TERM.bold(str(out))), ("Report", str(report))] +
                  [("", TERM.dim(line.strip())) for line in recent if line.strip().startswith(("[", "2", "3", "4", "5", "6", "7", "8", "9", "1"))][:6]))
    next_steps(["Read the report: anything placed by inference wants a look.", "Normalize the new export with the carried map, then build."], out.parent)
    return 0


def task_update(args: argparse.Namespace) -> int:
    print(phase_heading("Updates", "Looks at GitHub Releases through gh or a token. Nothing changes unless you say so."))
    print(ui.status_line(TERM, "ok", "Installed", f"v{VERSION}  {TERM.dim(str(REPO_DIR))}"))
    vendor = vendor_integrity()
    print(ui.status_line(TERM, "ok" if vendor["ok"] else "bad", "Vendored engine", f"Workbench {vendor['commit']}" if vendor["commit"] else "manifest unreadable"))
    restart = update_notice(force=True, offer_install=not args.yes and sys.stdin.isatty())
    return RESTART_EXIT_CODE if restart else 0


# --------------------------------------------------------------------------- main flow
def choose_task(args: argparse.Namespace) -> str:
    if args.task:
        return args.task
    if args.yes:
        return "build"
    print(phase_heading("The task", "Pick one; each line says what it does."))
    remembered = load_state()
    options = [(key, f"{title}\n         {TERM.dim(blurb)}" if not TERM.plain else f"{title} ({blurb})") for key, title, blurb in TASKS]
    default = "build" if remembered.get("blueprint") and Path(remembered["blueprint"]).is_file() else "first"
    return ui.choose(TERM, "What would you like to do?", options, default=default)


def run_tui(args: argparse.Namespace) -> int:
    PHASE["enabled"] = not args.yes
    PHASE["total"] = {"build": 5, "dry": 5, "first": 4, "verify": 4, "resync": 4, "update": 3}.get(args.task or "build", 5) - (1 if args.task else 0)
    PHASE["current"] = 0
    if not args.no_splash and not args.yes:
        art.splash(TERM, animate=not args.brisk, version=f"v{VERSION}")
    else:
        print(TERM.accent(TERM.bold("  Blueprint Packager")) + TERM.dim(f"  v{VERSION}"))
    workshop(args)
    if not args.no_update_check and not args.yes and sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get("BPK_NO_UPDATE_CHECK") != "1":
        if update_notice(force=False, offer_install=True):
            return RESTART_EXIT_CODE
    task = choose_task(args)
    if task == "first":
        return task_first(args)
    if task == "build":
        return task_build(args, dry=False)
    if task == "dry":
        return task_build(args, dry=True)
    if task == "verify":
        return task_verify(args)
    if task == "resync":
        return task_resync(args)
    if task == "update":
        return task_update(args)
    raise SystemExit(f"unknown task {task!r}")


def doctor() -> int:
    print(ui.heading(TERM, "Blueprint Packager doctor"))
    ok = python_version_ok()
    print(ui.status_line(TERM, "ok" if ok else "bad", "Python 3.11 or later", sys.version.split()[0]))
    missing = module_missing()
    print(ui.status_line(TERM, "ok" if not missing else "bad", "Python packages", "ok" if not missing else "missing " + ", ".join(missing)))
    vendor = vendor_integrity()
    print(ui.status_line(TERM, "ok" if vendor["ok"] else "bad", "Vendored engine",
                         f"{vendor['files']} files at Workbench {vendor['commit']}" if vendor["ok"] else (vendor["error"] or f"{len(vendor['missing'])} missing, {len(vendor['changed'])} changed")))
    print(ui.status_line(TERM, "ok", "Version", f"v{VERSION}"))
    return 0 if ok and not missing and vendor["ok"] else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"blueprint-packager v{VERSION}")
    parser.add_argument("--task", choices=[key for key, _, _ in TASKS], help="skip the menu")
    parser.add_argument("--yes", "-y", action="store_true", help="accept remembered defaults and run without prompts (repeat builds)")
    parser.add_argument("--plain", action="store_true", help="no colour, art, or animation")
    parser.add_argument("--no-splash", action="store_true")
    parser.add_argument("--brisk", action="store_true", help="skip the splash animation")
    parser.add_argument("--no-update-check", action="store_true", help="skip the once-daily release check")
    parser.add_argument("--check-for-updates", action="store_true", help="check GitHub Releases, then exit")
    parser.add_argument("--doctor", action="store_true", help="check the setup, then exit")
    parser.add_argument("--blueprint", help="the blueprint .docx (build, dry run)")
    parser.add_argument("--output-dir", help="where results go")
    parser.add_argument("--settings", help="a build settings file (build)")
    parser.add_argument("--build-dir", help="a build folder (verify)")
    parser.add_argument("--model", help="a course model .json (verify)")
    parser.add_argument("--old", help="old export .docx (re-sync)")
    parser.add_argument("--new", help="new export .docx (re-sync)")
    parser.add_argument("--map", help="course map .json (re-sync)")
    parser.add_argument("--course-number")
    parser.add_argument("--course-title")
    parser.add_argument("--term")
    parser.add_argument("--weeks", type=int)
    parser.add_argument("--assignments-per-week", type=int, help="common assignment count for a new blank, including zero")
    parser.add_argument("--discussions-per-week", type=int, help="common discussion count for a new blank, including zero")
    parser.add_argument("--week-count", action="append", default=[], metavar="W:A:D", help="override one week's assignment and discussion counts; repeatable")
    parser.add_argument("--worked-example", action="store_true", help="include sample points, rubric grids, and panel examples")
    parser.add_argument("--force", action="store_true", help="explicitly replace an existing blank and retain its backup")
    parser.add_argument("--dry-run", action="store_true", help="read and report readiness without building (alias for --task dry)")
    parser.add_argument("--preview", action="store_true", help="build a draft for review, including unresolved authoring placeholders")
    parser.add_argument("--retain-video-placeholder", action="append", default=[], metavar="TITLE", help="explicitly retain one named video placeholder")
    parser.add_argument("--video-link-fallback", action="append", default=[], metavar="TITLE", help="use a link for one named video with an unsupported embed provider")
    parser.add_argument("--calendar-file", help="JSON with explicit week boundaries or a complete calendar")
    parser.add_argument("--timezone", help="time zone for --calendar-file (otherwise existing zone or America/New_York)")
    args = parser.parse_args(argv)
    if args.dry_run:
        if args.task not in (None, "build", "dry"):
            parser.error("--dry-run applies to a blueprint read/build task")
        args.task = "dry"
    return args


def main(argv: list[str] | None = None) -> int:
    global TERM
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    args = parse_args(argv if argv is not None else sys.argv[1:])
    TERM = ui.Term(plain=args.plain)
    try:
        if args.doctor:
            return doctor()
        if args.check_for_updates:
            return RESTART_EXIT_CODE if update_notice(force=True, offer_install=not args.yes and sys.stdin.isatty()) else 0
        return run_tui(args)
    except (ValueError, OSError) as exc:
        print(TERM.bad(f"  Cannot continue: {exc}"))
        return 1
    except KeyboardInterrupt:
        TERM.show_cursor()
        print(f"\n  Canceled. Any partial run log is under {LOGS_DIR}.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
