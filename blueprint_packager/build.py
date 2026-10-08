"""Stage D: plan and write a Brightspace import package from a course model.

Building blocks, used but not owned:
* `d2l_package_lib` (Workbench): grade, dropbox, discussion, checklist, and
  orgunit serializers; resource-code factory; deterministic zip.
* `rubric_package_lib` (Workbench, Rubric Weave lineage): analytic rubric XML
  with custom level names and criterion weights.

Local extensions, each modelled on evidence from a real export of the target
tenant and listed in the build receipt so they can be reviewed for upstream
promotion: several discussion forums in one package, rubric associations on
discussion topics, hidden modules and topics, external link topics, one page
placed in two modules, and carrying a source quiz forward unchanged.
"""
from __future__ import annotations

import copy
import html
import importlib
import json
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from . import __version__
from . import identity as I
from . import workbench as WB
from .calendar import Calendar, CalendarError, WEEKDAYS, utc_parts
from .html_render import LinkRestoration, Template, render_course_page, render_fragment, render_week_page
from .joins import TYPE_LABEL
from .render_text import plain

BUILD_SETTINGS_SCHEMA = "blueprint_packager.build_settings/0.1"
QUICKLINKS = {
    "assignment": ("dropbox", "D2L.LE.Dropbox.Dropbox"),
    "discussion": ("discuss", "D2L.LE.Discussions.DiscussionTopic"),
    "checklist": ("checklist", "D2L.LE.Checklist.ChecklistEntity"),
    "quiz": ("quiz", "D2L.LE.Quizzing.Quiz"),
}


# How a checklist built from a week's activities words its items. A course can
# replace any of these in its build settings ("checklists": {"patterns": ...}).
# "single" is used when the week has one activity of that kind, "multiple" when
# it has several and each item needs the activity's own title to tell them apart.
CHECKLIST_PATTERNS = {
    "discussion_single": ["Week {week} Discussion: Initial Post", "Week {week} Discussion: Response Posts"],
    "discussion_multiple": ["{title} – Initial Post", "{title} – Response Posts"],
    "assignment_single": ["Submit your Week {week} Assignment"],
    "assignment_multiple": ["Submit your {title}"],
    "quiz_single": ["Complete the Week {week} Quiz"],
    "quiz_multiple": ["Complete {title}"],
}
# which calendar role dates each item of a pattern; None leaves the item undated
CHECKLIST_ITEM_ROLES = {"discussion": ["discussion_initial", "discussion_response"], "assignment": [None], "quiz": [None]}
DUE_PHRASE = re.compile(r"\bdue\b[^.;\n]{0,40}?\b(" + "|".join(WEEKDAYS) + r")\b|\b(" + "|".join(WEEKDAYS)
                        + r")\b[^.;\n]{0,12}?\b(?:by|before|at)\s+11:59", re.IGNORECASE)


class BuildError(ValueError):
    pass


def _find_repo_root(start: Path) -> Path:
    """Kept for callers that still pass a repository root; the scripts directory is what matters now."""
    for candidate in [start, *start.parents]:
        if (candidate / "scripts" / "d2l_package_lib.py").is_file():
            return candidate
    return WB.REPO_DIR


def _producer_path(path: Path, repo_root: Path, scripts_dir: Path) -> str:
    """A producer file's path as the receipt names it: relative to this repository when inside it,
    else relative to the scripts directory's parent (a Workbench checkout), else absolute."""
    for base in (repo_root, scripts_dir.parent):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.as_posix()


def load_building_blocks(scripts_dir: Path):
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    lib = importlib.import_module("d2l_package_lib")
    rlib = importlib.import_module("rubric_package_lib")
    return lib, rlib


def slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
    return text or "item"


def cell_html(blocks: list[dict[str, Any]]) -> str:
    """Rubric cell text as simple paragraphs (no styling; Brightspace styles rubric cells itself)."""
    parts = []
    for block in blocks:
        if not block.get("runs"):
            continue
        text = "".join(html.escape(run["text"], quote=False) for run in block["runs"]).replace("\n", "<br>").strip()
        if text:
            parts.append(f"<p>{text}</p>")
    return "".join(parts)


class Builder:
    def __init__(self, model: dict[str, Any], settings: dict[str, Any], settings_dir: Path) -> None:
        self.model = model
        self.settings = settings
        self.settings_dir = settings_dir
        try:
            scripts = WB.scripts_dir(settings.get("workbench_scripts"), start=settings_dir)
        except WB.WorkbenchNotFound as exc:
            raise BuildError(str(exc)) from exc
        self.scripts_dir = scripts
        self.workbench = WB.describe(scripts)
        self.repo_root = WB.REPO_DIR
        self.lib, self.rlib = load_building_blocks(scripts)
        self.template = Template.load(settings.get("template", "composite-navy"))  # owner's default since 2026-10-07
        self.rendered_html: dict[str, str] = {}
        source = model.get("source", {})
        self.template.course_label = str(settings.get("package", {}).get("course_label", "")).strip()
        self.template.provenance = (f"Blueprint Packager {__version__} · {settings.get('package', {}).get('title', '')} · "
                                    f"blueprint {source.get('name', '?')} sha256 {str(source.get('sha256', ''))[:12]} · "
                                    f"template {self.template.id} · built from the course model, not hand-edited")
        self.template.heading_offset = int(model.get("conventions", {}).get("heading_offset", 0))
        # owner, 2026-10-08: editor fields carry the template's modest style set by default ("plain is not acceptable")
        self.template.fragment_styles = settings.get("fragment_styles", "template") == "template"
        # link cleanup: named query parameters dropped from web addresses in the package only
        self.template.link_rules = list(settings.get("link_cleanup", {}).get("drop_query_parameters", []))
        try:
            self.calendar = Calendar(settings["calendar"]) if settings.get("calendar") else None
        except (CalendarError, ValueError) as exc:
            raise BuildError(f"Calendar: {exc}") from exc
        self.dates: list[dict[str, Any]] = []
        package = settings["package"]
        self.base_code = package["base_resource_code"]
        self.factory = self.lib.ResourceCodeFactory(self.base_code)
        self.codes: dict[str, str] = {}
        self.objects: list[dict[str, Any]] = []  # object map rows
        self.notes: list[dict[str, str]] = []
        self.files: dict[str, bytes | str] = {}
        self.extensions_used: set[str] = set()
        self.pages_dir = settings.get("pages_dir", "course_pages")
        self.page_files: dict[str, str] = {}
        self.restorations = [
            LinkRestoration(where=item.get("where", ""), anchor_text=item["anchor_text"], href="",
                            remove_text=item.get("remove_text", ""), evidence=item.get("evidence", ""))
            for item in settings.get("link_restorations", [])
        ]
        self._restoration_targets = settings.get("link_restorations", [])
        lineage = settings.get("lineage", {})
        self.lineage_key = I.scoped_key("lineage", lineage.get("basis", "course"), lineage.get("value", package["title"]))

    # ------------------------------------------------------------------ helpers
    def note(self, severity: str, code: str, message: str, where: str = "") -> None:
        self.notes.append({"severity": severity, "code": code, "message": message, "where": where})

    def claim(self, key: str) -> str:
        if key in self.codes:
            raise BuildError(f"Duplicate object key: {key}")
        self.codes[key] = self.factory.next()
        return self.codes[key]

    def record(self, kind: str, key: str, title: str, **extra: Any) -> None:
        row = {"kind": kind, "key": key, "title": title, "resource_code": self.codes.get(key), **extra}
        row.update(I.entity_identity(self.lineage_key, kind, title, self.codes.get(key)))
        self.objects.append(row)

    # --------------------------------------------------------------------- plan
    def plan(self) -> None:
        model = self.model
        errors = [d for d in model.get("diagnostics", []) if d["severity"] == "error"]
        if errors and not self.settings.get("allow_model_errors"):
            raise BuildError(f"Course model has {len(errors)} error(s); fix the blueprint before building. First: {errors[0]['message']}")

        # grade items, in points-table order. The points-table row is the join.
        # The name shown in the gradebook follows the activity it grades unless
        # the settings ask for the row text ("grade_item_names": "points_table").
        naming = self.settings.get("grade_item_names", "activity_title")
        if naming not in ("activity_title", "points_table"):
            raise BuildError(f"grade_item_names must be 'activity_title' or 'points_table', not {naming!r}")
        graded_by: dict[str, str] = {}
        points_by: dict[str, float] = {}
        graded = [a for week in model["weeks"] for kind in ("discussions", "assignments", "quizzes") for a in week[kind]]
        graded += [a for a in model["course_activities"] if a["type"] in TYPE_LABEL]
        table_points = {item["name"]: float(item["points"]) for item in model["grade_plan"]["items"]}
        determinations = self.settings.get("points_determinations", {})
        undecided: list[str] = []
        self.effective_points: dict[tuple[str, str], float] = {}
        for activity in graded:
            row = activity.get("grade_item")
            if not row:
                continue
            graded_by.setdefault(row, activity["title"])
            if activity.get("points") is None:
                continue
            stated, planned = float(activity["points"]), table_points.get(row)
            use = stated
            if planned is not None and abs(stated - planned) > 1e-9:
                # the activity and its points table row disagree: a person decides, and the choice is recorded
                choice = determinations.get(row) or determinations.get(activity["title"])
                if choice not in ("activity", "points_table"):
                    undecided.append(f"'{activity['title']}' says {stated:g} pts; its points table row '{row}' says {planned:g}")
                    continue
                use = stated if choice == "activity" else planned
                self.note("warning", "POINTS_DETERMINED", f"Activity says {stated:g} pts and its points table row says {planned:g}; "
                          f"the build uses {use:g} by the recorded determination '{choice}'", activity["title"])
            self.effective_points[(activity["type"], activity["title"])] = use
            points_by.setdefault(row, use)
        if undecided:
            raise BuildError("Points disagree and no determination is recorded. Add \"points_determinations\": "
                             "{\"<points table row>\": \"activity\" or \"points_table\"} to the build settings for: " + "; ".join(undecided))
        self.grade_items = []
        self.grade_key: dict[str, str] = {}
        for index, item in enumerate(model["grade_plan"]["items"], start=1):
            key = f"grade_{index:02d}"
            self.claim(key)
            self.grade_key[item["name"]] = key
            name = graded_by.get(item["name"], item["name"]) if naming == "activity_title" else item["name"]
            points = points_by.get(item["name"], float(item["points"]))
            self.grade_items.append({"key": key, "name": name, "points": int(points) if float(points).is_integer() else points})
            self.record("grade_item", key, name, points=points, points_table_row=item["name"],
                        points_table_points=item["points"], name_source=naming)
        names = [g["name"] for g in self.grade_items]
        if len(set(names)) != len(names):
            raise BuildError("Two grade items would share a name; give the activities distinct titles or set grade_item_names to 'points_table'.")

        # rubrics (ids are positional; codes come from the rubric library's own scheme)
        self.rubrics = [r for r in model["rubrics"] if r.get("grid")]
        self.rubric_id = {r["name"]: str(i) for i, r in enumerate(self.rubrics, start=1)}
        self.rubric_key = {r["name"]: f"rubric_{i:02d}" for i, r in enumerate(self.rubrics, start=1)}

        # activities
        self.folders: list[dict[str, Any]] = []
        self.forums: dict[str, list[dict[str, Any]]] = {}
        self.quizzes: list[dict[str, Any]] = []
        self.activity_key: dict[tuple[str, str], str] = {}
        counters = {"assignment": 0, "discussion": 0, "quiz": 0}
        activities = []
        week_of: dict[int, int] = {}
        self.due_by_activity: dict[tuple[str, str], str] = {}
        for week in model["weeks"]:
            for kind in ("discussions", "assignments", "quizzes"):
                activities.extend(week[kind])
                for activity in week[kind]:
                    week_of[id(activity)] = week["number"]
        activities.extend(a for a in model["course_activities"] if a["type"] in TYPE_LABEL)
        # claim every activity's key first, so a description may link to an activity that comes later
        keys: dict[int, str] = {}
        for activity in activities:
            kind = activity["type"]
            counters[kind] += 1
            key = f"{kind}_{counters[kind]:02d}"
            self.claim(key)
            self.activity_key[(kind, activity["title"])] = key
            keys[id(activity)] = key
        # checklists
        self.checklists = []
        self.checklist_key: dict[str, str] = {}
        for index, week in enumerate(model["weeks"], start=1):
            checklist = week["checklist"]
            if not checklist:
                continue
            authored = [plain(item["runs"]) for item in checklist.get("items", []) if plain(item["runs"])]
            extra_dates = self.settings.get("checklists", {}).get("extra_item_dates", {})
            items: list[dict[str, Any]] = self.derive_checklist_items(week) if checklist.get("derive") else []
            for text in authored:
                item = {"name": text}
                if text in extra_dates:
                    if not self.calendar:
                        raise BuildError(f"Checklist item '{text}' has a date rule and the build settings have no calendar")
                    rule = extra_dates[text]
                    due = self._stamp(int(rule.get("week", week["number"])), rule["day"], rule.get("time"), f"checklist item '{text}'")
                    item["date_end"] = due["utc"]
                    self.dates.append({"object": f"Checklist item: {text}", "kind": "checklist item end date", "checklist": checklist["title"], **due})
                items.append(item)
            if not items and not self.settings.get("build_empty_checklists", False):
                self.note("warning", "CHECKLIST_NOT_BUILT", f"'{checklist['title']}' has no items in the blueprint, so it was not built and has no module link", week["title"])
                continue
            key = f"checklist_{index:02d}"
            self.claim(key)
            self.checklist_key[checklist["title"]] = key
            link_type, _type_key = QUICKLINKS["checklist"]
            self.template.link_targets[("checklist", checklist["title"])] = {
                "page": None, "quicklink": f"/d2l/common/dialogs/quickLink/quickLink.d2l?ou={{orgUnitId}}&type={link_type}&rCode={self.codes[key]}"}
            self.checklists.append({"key": key, "name": checklist["title"],
                                    "categories": [{"name": checklist["title"], "items": items}]})
            self.record("checklist", key, checklist["title"], week=week["number"], items=len(items),
                        item_names=[item["name"] for item in items], item_dates=[item.get("date_end", "") for item in items],
                        items_source=("built from the week's activities" + (f", plus {len(authored)} listed in the blueprint" if authored else ""))
                        if checklist.get("derive") else "listed in the blueprint")

        self._register_link_targets()
        for activity in activities:
            kind = activity["type"]
            key = keys[id(activity)]
            where = f"{TYPE_LABEL[kind]}: {activity['title']}"
            grade_key = self.grade_key.get(activity.get("grade_item") or "")
            points = self.effective_points.get((kind, activity["title"]), activity.get("points"))
            week_number = week_of.get(id(activity))
            self.record(kind, key, activity["title"], week=week_number, points=points,
                        grade_item=activity.get("grade_item"), rubric=activity.get("rubric"), forum=activity.get("forum"))
            if kind == "assignment":
                fragment, diags = render_fragment(self._description_blocks(activity), self.template, activity["title"], self.restorations)
                self.rendered_html[f"{activity['type']}: {activity['title']}"] = fragment
                self.notes.extend(diags)
                folder = {"key": key, "name": activity["title"], "instructions_html": fragment,
                          "submission_type": self.settings.get("dropbox_defaults", {}).get("submission_type", "0")}
                if grade_key:
                    folder.update(grade_item=grade_key, points=points)
                if activity.get("rubric"):
                    folder["rubric"] = self.rubric_key[activity["rubric"]]
                due = self.due("assignment", week_number, activity, "assignment folder due date") if week_number else None
                if due:
                    folder["date_due"] = due["utc"]
                    self.due_by_activity[(kind, activity["title"])] = due["utc"]
                if self.calendar and week_number:
                    self.check_prose_days(activity, [due])
                self.folders.append(folder)
            elif kind == "discussion":
                fragment, diags = render_fragment(self._description_blocks(activity), self.template, activity["title"], self.restorations)
                self.rendered_html[f"{activity['type']}: {activity['title']}"] = fragment
                self.notes.extend(diags)
                topic = {"key": key, "title": activity["title"], "description_html": fragment, "_rubric": activity.get("rubric")}
                if grade_key:
                    topic.update(score_out_of=int(points) if float(points).is_integer() else points, grade_item=grade_key)
                self.forums.setdefault(activity["forum"], []).append(topic)
            else:
                self.quizzes.append({"key": key, "activity": activity, "grade_key": grade_key, "week": week_number})


    def _register_link_targets(self) -> None:
        """Tell the renderer which objects "[link to ...]" may name, and how to reach each one."""
        targets: dict[tuple[str, str], dict[str, str | None]] = {}
        for (kind, title), key in self.activity_key.items():
            link_type, _type_key = QUICKLINKS[kind]
            targets[(kind, title)] = {"page": None, "quicklink": f"/d2l/common/dialogs/quickLink/quickLink.d2l?ou={{orgUnitId}}&type={link_type}&rCode={self.codes[key]}"}
        for page in self.model["pages"] + [week["overview_page"] for week in self.model["weeks"]]:
            # relative address between pages in the same folder; no topic code exists yet for a quicklink
            targets[("page", page["title"])] = {"page": self.page_filename(page["title"]).rsplit("/", 1)[-1], "quicklink": None}
        self.template.link_targets = targets

    # ----------------------------------------------------------- dates, checklists
    def _stamp(self, week: int, day: str, at: str | None, what: str) -> dict[str, Any]:
        try:
            return self.calendar.stamp(week, day, at)
        except CalendarError as exc:
            raise BuildError(f"Calendar: {what}: {exc}") from exc

    def due(self, role: str, week: int | None, activity: dict[str, Any], kind: str) -> dict[str, Any] | None:
        """Resolve one due date from the calendar, record it, and compare it with any day the prose names."""
        if not self.calendar:
            return None
        try:
            due = self.calendar.due(role, week, activity["title"])
        except CalendarError as exc:
            raise BuildError(f"Calendar: {activity['title']}: {exc}") from exc
        if due:
            self.dates.append({"object": f"{TYPE_LABEL.get(activity['type'], activity['type'])}: {activity['title']}", "kind": kind, "role": role, **due})
        return due

    def check_prose_days(self, activity: dict[str, Any], resolved: list[dict[str, Any]]) -> None:
        """Say so when an activity's own text names a due day the calendar did not give it."""
        def texts(blocks: list[dict[str, Any]]) -> list[str]:
            out = []
            for block in blocks:
                if isinstance(block, dict):
                    out.append(plain(block.get("runs", [])))
                    out.extend(texts(block.get("blocks", [])))
            return out
        named = set()
        own_week = resolved[0]["week"] if resolved and resolved[0] else None
        for text in texts(activity.get("blocks", [])):
            for match in DUE_PHRASE.finditer(text):
                other = re.search(r"\bWeek\s+(\d+)\b", match.group(0), re.IGNORECASE)
                if other and own_week is not None and int(other.group(1)) != own_week:
                    continue  # the text is naming a deadline in another week
                named.add((match.group(1) or match.group(2)).title())
        given = {d["weekday"] for d in resolved if d}
        if named and not named <= given:
            self.note("warning", "DUE_DAY_DIFFERS_FROM_TEXT",
                      f"The activity's text names {', '.join(sorted(named))} as due days; the calendar gives {', '.join(sorted(given)) or 'no date'}. "
                      "Set a calendar override for this activity or correct the text.", activity["title"])

    def derive_checklist_items(self, week: dict[str, Any]) -> list[dict[str, Any]]:
        """Checklist items built from the week's own activities, worded by the course's patterns."""
        config = self.settings.get("checklists", {})
        patterns = {**CHECKLIST_PATTERNS, **config.get("patterns", {})}
        items: list[dict[str, Any]] = []
        for group, kind in (("discussions", "discussion"), ("assignments", "assignment"), ("quizzes", "quiz")):
            activities = week[group]
            form = "multiple" if len(activities) > 1 else "single"
            for activity in activities:
                resolved = []
                for pattern, role in zip(patterns[f"{kind}_{form}"], CHECKLIST_ITEM_ROLES[kind] * len(patterns[f"{kind}_{form}"])):
                    item = {"name": pattern.format(week=week["number"], title=activity["title"])}
                    if role and self.calendar:
                        due = self.due(role, week["number"], activity, f"checklist item end date ({item['name']})")
                        if due:
                            item["date_end"] = due["utc"]
                            resolved.append(due)
                    items.append(item)
                if kind == "discussion" and self.calendar:
                    self.check_prose_days(activity, resolved)
        return items

    # ------------------------------------------------------------------- pages
    def page_filename(self, title: str) -> str:
        if title not in self.page_files:
            name = f"{self.pages_dir}/{slug(title)}.html"
            if name in self.page_files.values():
                raise BuildError(f"Two pages map to the same file name: {name}")
            self.page_files[title] = name
        return self.page_files[title]

    def render_pages(self) -> None:
        model = self.model
        for page in model["pages"]:
            self.page_filename(page["title"])
        for week in model["weeks"]:
            self.page_filename(week["overview_page"]["title"])
        # resolve restoration targets now that file names exist (pages sit in one folder)
        for restoration, spec in zip(self.restorations, self._restoration_targets):
            target = spec["target"]
            if target["type"] == "url":
                restoration.href = target["url"]
            elif target["type"] == "page":
                if target["title"] not in self.page_files:
                    raise BuildError(f"Link restoration targets an unknown page: {target['title']}")
                restoration.href = self.page_files[target["title"]].rsplit("/", 1)[-1]
            else:
                raise BuildError(f"Unknown restoration target type: {target['type']}")
        for page in model["pages"]:
            rendered, diags = render_course_page(page, self.template, self.restorations)
            self.rendered_html[f"page: {page['title']}"] = rendered
            self.files[self.page_files[page["title"]]] = rendered
            self.notes.extend(diags)
            self.record("page", f"page:{slug(page['title'])}", page["title"], file=self.page_files[page["title"]],
                        placement=page.get("placement"), visibility=page.get("visibility"))
        for week in model["weeks"]:
            page = week["overview_page"]
            rendered, diags = render_week_page(week, self.template, self.restorations)
            self.rendered_html[f"page: {week['overview_page']['title']}"] = rendered
            self.files[self.page_files[page["title"]]] = rendered
            self.notes.extend(diags)
            self.record("page", f"page:{slug(page['title'])}", page["title"], file=self.page_files[page["title"]], week=week["number"])
        for restoration in self.restorations:
            if restoration.used != 1:
                self.note("error" if restoration.used == 0 else "warning", "LINK_RESTORATION",
                          f"Link restoration for '{restoration.anchor_text[:50]}' matched {restoration.used} time(s); expected 1", restoration.where)

    # ----------------------------------------------------------------- payloads
    def write_payloads(self, package_dir: Path) -> dict[str, list[tuple[str, str, str]]]:
        """Write payload XML. Returns {material_type: [(identifier, href, title)]}."""
        lib, rlib = self.lib, self.rlib
        payloads: dict[str, list[tuple[str, str, str]]] = {}
        package_meta = {"package": {"title": self.settings["package"]["title"],
                                    **{k: v for k, v in self.settings["package"].items() if k.startswith("orgunit")}}}
        lib.write_xml(lib.build_orgunit_xml(package_meta), package_dir / "orgunitconfig" / "orgunitconfig.xml")
        payloads["orgunitconfig"] = [("res_orgunitconfig", r"orgunitconfig\orgunitconfig.xml", "")]

        lib.write_xml(lib.build_grades_xml(self.grade_items, self.codes), package_dir / "grades_d2l.xml")
        payloads["d2lgrades"] = [("res_d2lgrades", "grades_d2l.xml", "")]

        if self.rubrics:
            contract = {
                "schema": "coursecraft.rubric_authoring/1",
                "package": {"rubric_id_start": 1, "resource_code_start": 980001, "level_id_base_start": 660000,
                            "resource_prefix": self.base_code},
                "rubrics": [],
            }
            for rubric in self.rubrics:
                grid = rubric["grid"]
                levels = [{"name": level["name"], "multiplier": level["percent"] / 100.0, "sort_order": order}
                          for order, level in enumerate(grid["levels"], start=1)]
                ascending = sorted(grid["levels"], key=lambda level: level["percent"])
                overall = [{"name": level["name"], "sort_order": len(ascending) - position, "range_start_value": level["percent"]}
                           for position, level in enumerate(ascending)]
                criteria = [{"name": criterion["name"], "weight": criterion["weight"],
                             "descriptions": {level["name"]: cell_html(cell) for level, cell in zip(grid["levels"], criterion["cells"])}}
                            for criterion in grid["criteria"]]
                contract["rubrics"].append({"name": rubric["name"], "levels": levels, "criteria": criteria, "overall_levels": overall})
            root = rlib.build_rubrics_xml(contract)
            for rubric, element in zip(self.rubrics, root.findall("rubric")):
                key = self.rubric_key[rubric["name"]]
                self.codes[key] = element.get("resource_code")
                self.record("rubric", key, rubric["name"], rubric_id=element.get("id"), used_by=rubric["used_by"],
                            criteria=len(rubric["grid"]["criteria"]), levels=[l["name"] for l in rubric["grid"]["levels"]])
            lib.write_xml(root, package_dir / "rubrics_d2l.xml")
            payloads["d2lrubrics"] = [("res_d2lrubrics", "rubrics_d2l.xml", "")]

        if self.folders:
            rubric_ids = {self.rubric_key[name]: rid for name, rid in self.rubric_id.items()}
            root = lib.build_dropbox_xml(self.folders, self.codes, rubric_ids)
            submissions = self.settings.get("dropbox_defaults", {}).get("submissions")
            for folder in root.findall("folder"):
                if submissions is not None:
                    folder.set("submissions", str(submissions))
            lib.write_xml(root, package_dir / "dropbox_d2l.xml")
            payloads["d2ldropbox"] = [("res_d2ldropbox", "dropbox_d2l.xml", "")]

        forum_order = self.settings.get("forum_order") or list(self.forums)
        missing = [name for name in self.forums if name not in forum_order]
        if missing:
            raise BuildError(f"Forums missing from 'forum_order': {missing}")
        topic_id = 700
        payloads["d2ldiscussion"] = []
        must_post = self.settings.get("discussion_defaults", {}).get("must_post_to_participate")
        for index, forum_title in enumerate([name for name in forum_order if name in self.forums], start=1):
            forum_key = f"forum_{index:02d}"
            self.claim(forum_key)
            topics = self.forums[forum_title]
            root = lib.build_discussion_xml({"key": forum_key, "forum_title": forum_title, "topics": topics}, self.codes)
            forum = root.find("forum")
            forum.set("id", str(609 + index))
            forum.find("properties/display_order").text = str(index)
            has_association = False
            for topic, element in zip(topics, forum.findall("topics/topic")):
                topic_id += 1
                element.set("id", str(topic_id))
                if must_post is not None and topic.get("grade_item"):
                    element.find("properties/must_post_to_participate").text = "True" if must_post else "False"
                if topic.get("_rubric"):
                    associations = ET.Element(f"{{{lib.D2L_NS}}}associations")
                    ET.SubElement(associations, f"{{{lib.D2L_NS}}}rubric").text = self.rubric_id[topic["_rubric"]]
                    element.insert(0, associations)
                    has_association = True
            if has_association:
                # namespaced children make ElementTree declare the prefix itself; a second literal copy would be invalid XML
                root.attrib.pop("xmlns:d2l_2p0", None)
                self.extensions_used.add("rubric association on discussion topics")
            name = f"discussion_d2l_{index}.xml"
            lib.write_xml(root, package_dir / name)
            payloads["d2ldiscussion"].append((f"res_d2ldiscussion_{index}", name, ""))
            self.record("forum", forum_key, forum_title, topics=[t["title"] for t in topics])
        if len(payloads["d2ldiscussion"]) > 1:
            self.extensions_used.add("more than one discussion forum in a package")

        if self.checklists:
            lib.write_xml(lib.build_checklists_xml(self.checklists, self.codes, self.factory), package_dir / "checklist_d2l.xml")
            payloads["d2lchecklist"] = [("res_d2lchecklist", "checklist_d2l.xml", "")]

        payloads["d2lquiz"] = []
        for quiz in self.quizzes:
            payloads["d2lquiz"].append(self._carry_quiz(quiz, package_dir))
        return {k: v for k, v in payloads.items() if v}

    def _carry_quiz(self, quiz: dict[str, Any], package_dir: Path) -> tuple[str, str, str]:
        title = quiz["activity"]["title"]
        spec = next((s for s in self.settings.get("carried_quizzes", []) if s["title"] == title), None)
        if spec is None:
            raise BuildError(f"Quiz '{title}' is described in the blueprint but no 'carried_quizzes' source is configured. This tool does not author quizzes.")
        source = (self.settings_dir / spec["source_dir"]).resolve() if not Path(spec["source_dir"]).is_absolute() else Path(spec["source_dir"])
        text = (source / spec["payload"]).read_text(encoding="utf-8-sig")
        if title not in text:
            raise BuildError(f"Carried quiz payload {spec['payload']} does not contain the title '{title}'")
        code = self.codes[quiz["key"]]

        def sub(pattern: str, replacement: str, label: str, flags: int = 0) -> None:
            nonlocal text
            text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
            if count != 1:
                raise BuildError(f"Carried quiz {spec['payload']}: could not rewrite {label}")

        sub(r'(<assessment\b[^>]*?d2l_2p0:resource_code=")[^"]+(")', rf"\g<1>{code}\g<2>", "the quiz resource code")
        if quiz["grade_key"]:
            grade_code = self.codes[quiz["grade_key"]]
            position = next(i for i, item in enumerate(self.grade_items, start=1) if item["key"] == quiz["grade_key"])
            sub(r'(<grade_item\b[^>]*?resource_code=")[^"]+("[^>]*>)[^<]*(</grade_item>)',
                rf"\g<1>{grade_code}\g<2>{700000 + position}\g<3>", "the grade item join")
        due = None
        if self.calendar and spec.get("due"):
            rule = spec["due"]
            due = self._stamp(int(rule["week"]), rule["day"], rule.get("time"), f"quiz '{title}'")
            self.dates.append({"object": f"Quiz: {title}", "kind": "quiz due date", "role": "quiz", **due})
        elif self.calendar and quiz.get("week"):
            due = self.due("quiz", quiz["week"], quiz["activity"], "quiz due date")
        stale = re.search(r"<d2l_2p0:date_due>.*?</d2l_2p0:date_due>", text, flags=re.S)
        if due:
            # the nested form is how Brightspace itself exports a quiz date; the flat form did not survive an import
            parts = utc_parts(due["utc"])
            nested = "<d2l_2p0:date_due><d2l_2p0:timestamp>" + "".join(
                f"<d2l_2p0:{name}>{parts[name]}</d2l_2p0:{name}>" for name in ("month", "day", "year", "hour", "minutes", "seconds")
            ) + "</d2l_2p0:timestamp></d2l_2p0:date_due>"
            sub(r"<d2l_2p0:date_due>.*?</d2l_2p0:date_due>|<d2l_2p0:date_due\s*/>", nested, "the due date", flags=re.S)
            self.extensions_used.add("due date written on a carried quiz in Brightspace's nested timestamp form")
            self.note("info", "QUIZ_DUE_DATE_SET", f"The carried quiz's due date was set to {due['label']}", title)
        elif stale:
            sub(r"<d2l_2p0:date_due>.*?</d2l_2p0:date_due>", "<d2l_2p0:date_due />", "the stale due date", flags=re.S)
            self.note("info", "QUIZ_DUE_DATE_CLEARED", "The carried quiz had a due date from an earlier term; it was cleared", title)
        match = re.search(r'ident="(res_quiz_\d+)"', text)
        identifier = match.group(1) if match else f"res_quiz_{quiz['key']}"
        (package_dir / spec["payload"]).write_text(text, encoding="utf-8")
        self.extensions_used.add("quiz carried forward unchanged from a source export")
        self.note("info", "QUIZ_CARRIED", f"Quiz payload copied from {spec['payload']}; only its resource code, grade join, and due date were rewritten", title)
        return identifier, spec["payload"], title

    # ----------------------------------------------------------------- manifest
    def module_plan(self) -> list[dict[str, Any]]:
        model = self.model
        modules: list[dict[str, Any]] = []
        by_title: dict[str, dict[str, Any]] = {}
        for module in model["modules"]:
            entry = {"title": module["title"], "hidden": (module.get("visibility") or "").lower().startswith("hidden"), "items": []}
            modules.append(entry)
            by_title[module["title"]] = entry
        for week in model["weeks"]:
            entry = {"title": week["title"], "hidden": False, "items": [], "week": week["number"]}
            modules.append(entry)
            by_title[week["title"]] = entry
        # course pages and links, in blueprint order, into every module they name
        for obj in model["pages"] + model["links"]:
            for placement in obj.get("placement") or []:
                hidden = (obj.get("visibility") or "").lower().startswith("hidden")
                if obj["type"] == "page":
                    item = {"type": "page", "title": obj["title"], "href": self.page_files[obj["title"]], "hidden": hidden}
                else:
                    item = {"type": "link", "title": obj["title"], "url": obj["url"], "hidden": hidden}
                by_title[placement]["items"].append(item)
        # week modules: overview first, then extra pages already placed, then the tool links in profile order
        order = self.settings.get("week_item_order", ["page", "placed", "checklist", "discussions", "assignments", "quizzes"])
        for week in model["weeks"]:
            entry = by_title[week["title"]]
            placed = entry["items"]
            groups: dict[str, list[dict[str, Any]]] = {
                "page": [{"type": "page", "title": week["overview_page"]["title"], "href": self.page_files[week["overview_page"]["title"]], "hidden": False}],
                "placed": placed,
                "checklist": [],
                "discussions": [{"type": "discussion", "title": a["title"]} for a in week["discussions"]],
                "assignments": [{"type": "assignment", "title": a["title"]} for a in week["assignments"]],
                "quizzes": [{"type": "quiz", "title": a["title"]} for a in week["quizzes"]],
            }
            if week["checklist"] and week["checklist"]["title"] in self.checklist_key:
                groups["checklist"] = [{"type": "checklist", "title": week["checklist"]["title"]}]
            entry["items"] = [item for name in order for item in groups[name]]
        # course-level activities that name a module
        for activity in model["course_activities"]:
            for placement in activity.get("placement") or []:
                by_title[placement]["items"].append({"type": activity["type"], "title": activity["title"]})
        return modules

    def build_manifest(self, payloads: dict[str, list[tuple[str, str, str]]]) -> ET.Element:
        lib = self.lib
        package = self.settings["package"]
        manifest = ET.Element("manifest", {"identifier": package.get("manifest_identifier", "D2L_BLUEPRINT_PACKAGE"), "xmlns": lib.IMSCP_NS})
        metadata = ET.SubElement(manifest, "metadata")
        lom = ET.SubElement(metadata, f"{{{lib.IMSMD_NS}}}lom")
        general = ET.SubElement(lom, f"{{{lib.IMSMD_NS}}}general")
        title = ET.SubElement(general, f"{{{lib.IMSMD_NS}}}title")
        ET.SubElement(title, f"{{{lib.IMSMD_NS}}}langstring", {"xml:lang": "en-us"}).text = package["title"]
        keyword = ET.SubElement(general, f"{{{lib.IMSMD_NS}}}keyword")
        ET.SubElement(keyword, f"{{{lib.IMSMD_NS}}}langstring", {"xml:lang": "en-us"}).text = package.get("keyword", package["title"])
        ET.SubElement(general, f"{{{lib.IMSMD_NS}}}language").text = "en-us"
        organizations = ET.SubElement(manifest, "organizations", {"default": "d2l_orgs"})
        organization = ET.SubElement(organizations, "organization", {"identifier": "d2l_org"})
        resources = ET.SubElement(manifest, "resources")
        for material_type, entries in payloads.items():
            for identifier, href, title_text in entries:
                lib.make_resource(resources, identifier, material_type, href, title=title_text)

        counter = [2000]

        def attrs(hidden: bool = False, extra: dict[str, str] | None = None) -> dict[str, str]:
            counter[0] += 1
            out = {f"{{{lib.D2L_NS}}}id": str(counter[0])}
            if hidden:
                out["isvisible"] = "False"
                self.extensions_used.add("hidden modules and topics (isvisible=False)")
            out.update({f"{{{lib.D2L_NS}}}resource_code": self.factory.next(), "description": "", "completion_type": "2"})
            if extra:
                out.update(extra)
            out[f"{{{lib.D2L_NS}}}ai_human_origin"] = "0"
            return out

        self.structure: list[dict[str, Any]] = []
        placed_pages: dict[str, int] = {}
        for m_index, module in enumerate(self.module_plan(), start=1):
            module_id = f"M{m_index:02d}"
            module_item = ET.SubElement(organization, "item", {"identifier": f"ITEM_{module_id}", "identifierref": f"RES_CONTENT_{module_id}", **attrs(module["hidden"])})
            ET.SubElement(module_item, "title").text = module["title"]
            lib.make_resource(resources, f"RES_CONTENT_{module_id}", "contentmodule", "")
            row = {"module": module["title"], "hidden": module["hidden"], "items": []}
            self.structure.append(row)
            for t_index, item in enumerate(module["items"], start=1):
                topic_id = f"{module_id}_T{t_index:02d}"
                extra: dict[str, str] = {}
                hidden = bool(item.get("hidden")) or module["hidden"]
                if item["type"] == "page":
                    href, material, target = item["href"], "content", ""
                    placed_pages[item["title"]] = placed_pages.get(item["title"], 0) + 1
                    if placed_pages[item["title"]] > 1:
                        self.extensions_used.add("one page file placed as a topic in two modules")
                elif item["type"] == "link":
                    href, material, target = item["url"], "contentlink", "_blank"
                    self.extensions_used.add("external link topics")
                else:
                    link_type, type_key = QUICKLINKS[item["type"]]
                    key = self.checklist_key[item["title"]] if item["type"] == "checklist" else self.activity_key[(item["type"], item["title"])]
                    href = f"/d2l/common/dialogs/quickLink/quickLink.d2l?ou={{orgUnitId}}&type={link_type}&rCode={self.codes[key]}"
                    material, target = "contentlink", "_self"
                    extra["resource_type_key"] = type_key
                    if (item["type"], item["title"]) in self.due_by_activity:
                        extra["date_due"] = self.due_by_activity[(item["type"], item["title"])]
                child = ET.SubElement(module_item, "item", {"identifier": f"ITEM_{topic_id}", "identifierref": f"RES_CONTENT_{topic_id}", **attrs(hidden, extra)})
                ET.SubElement(child, "title").text = item["title"]
                lib.make_resource(resources, f"RES_CONTENT_{topic_id}", material, href, link_target=target)
                row["items"].append({"type": item["type"], "title": item["title"], "hidden": hidden, "href": href})
        return manifest

    # --------------------------------------------------------------------- run
    def run(self, out_dir: Path, force: bool) -> dict[str, Any]:
        lib = self.lib
        started = I.utc_now()
        out_dir = out_dir.resolve()
        if out_dir.exists() and not force:
            raise BuildError(f"Output directory exists: {out_dir}. Use --force.")
        self.plan()
        self.render_pages()
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_root = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.build-", dir=out_dir.parent))
        try:
            package_dir = temp_root / "package"
            package_dir.mkdir()
            payloads = self.write_payloads(package_dir)
            for relative, content in self.files.items():
                target = package_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8") if isinstance(content, str) else target.write_bytes(content)
            lib.write_xml(self.build_manifest(payloads), package_dir / "imsmanifest.xml")
            zip_name = self.settings["package"].get("zip_name", "package.zip")
            lib.deterministic_zip(package_dir, temp_root / zip_name)
            # Pages-only refresh (sandbox round 2, 2026-10-08): Brightspace overwrites a course file at the
            # same path on import but duplicates every other object, so page content can be refreshed in a
            # built course by uploading this ZIP's folder through Manage Files. Untested until a round tries it.
            pages_dir = package_dir / self.settings.get("pages_dir", "course_pages")
            refresh_name = None
            if pages_dir.is_dir():
                refresh_name = "course_pages_refresh.zip"
                staging = temp_root / "_refresh"
                shutil.copytree(pages_dir, staging / pages_dir.name)
                lib.deterministic_zip(staging, temp_root / refresh_name)
                shutil.rmtree(staging)

            errors = [n for n in self.notes if n["severity"] == "error"]
            receipt = {
                "schema": "coursecraft.component_package_receipt/1",
                "package_title": self.settings["package"]["title"],
                "base_resource_code": self.base_code,
                "deterministic": True,
                "contract_sha256": I.canonical_sha256({"model": self.model.get("source"), "settings": self.settings}),
                "producer_files": [
                    {"path": _producer_path(path, self.repo_root, self.scripts_dir), "role": "producer", "bytes": path.stat().st_size,
                     "sha256": I.sha256_file(path), "extensions": {}}
                    for path in sorted([*Path(__file__).resolve().parent.glob("*.py"),
                                        self.scripts_dir / "d2l_package_lib.py", self.scripts_dir / "rubric_package_lib.py"])
                ],
                "workbench_scripts": self.workbench,
                "codes": dict(sorted(self.codes.items())),
                "support_assets": [],
                "package_files": [
                    {"path": p.relative_to(package_dir).as_posix(), "role": _role(p.relative_to(package_dir).as_posix()),
                     "bytes": p.stat().st_size, "sha256": I.sha256_file(p), "extensions": {}}
                    for p in sorted(x for x in package_dir.rglob("*") if x.is_file())
                ],
                "zip": {"path": zip_name, "role": "package_zip", "bytes": (temp_root / zip_name).stat().st_size,
                        "sha256": I.sha256_file(temp_root / zip_name), "extensions": {}},
                "pages_refresh_zip": ({"path": refresh_name, "role": "pages_refresh", "bytes": (temp_root / refresh_name).stat().st_size,
                                       "sha256": I.sha256_file(temp_root / refresh_name),
                                       "use": "upload the folder inside through Manage Files at the same path to refresh page content in a built course; nothing else changes"}
                                      if refresh_name else None),
                "extensions": {
                    "live_brightspace_operations": "not_performed",
                    "producer": {"tool": I.TOOL, "version": __version__},
                    "template": {"id": self.template.id, "version": self.template.manifest.get("version")},
                    "beyond_workbench_library": sorted(self.extensions_used),
                    "evidence_level": "L1 (local build and read-back); not imported",
                },
            }
            (temp_root / "component_package_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            object_map = {
                "schema": "blueprint_packager.object_map/0.1",
                "lineage_key": self.lineage_key,
                "objects": self.objects,
                "structure": self.structure,
                "dates": self.dates,
                "calendar": ({"timezone": self.calendar.zone_name,
                              "weeks": {str(n): [a.isoformat(), b.isoformat()] for n, (a, b) in sorted(self.calendar.weeks.items())}}
                             if self.calendar else None),
                "link_cleanup": self._cleaned_links(),
                "external_links": self._external_links(),
                "rendering": {"template": self.template.id, "editor_fields": "template inline styles" if self.template.fragment_styles else "plain semantic HTML",
                              "heading_subline": "text after a line break inside a heading is wrapped in <small>"},
                "notes": self.notes,
            }
            (temp_root / "object_map.json").write_text(json.dumps(object_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            (temp_root / "object_map.md").write_text(self._object_map_markdown(), encoding="utf-8")
            (temp_root / "build_settings.json").write_text(json.dumps(self.settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if out_dir.exists():
                shutil.rmtree(out_dir)
            temp_root.rename(out_dir)
        except Exception:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise
        return {"out_dir": out_dir, "package_dir": out_dir / "package", "zip": out_dir / zip_name, "started": started,
                "errors": errors, "receipt": receipt}

    def _cleaned_links(self) -> list[dict[str, Any]]:
        """Each address the link cleanup changed, once, with the places it appears."""
        merged: dict[tuple[str, str], list[str]] = {}
        for row in self.template.cleaned_links:
            places = merged.setdefault((row["from"], row["to"]), [])
            if row["where"] and row["where"] not in places:
                places.append(row["where"])
        return [{"from": a, "to": b, "where": places} for (a, b), places in merged.items()]

    def _description_blocks(self, activity: dict[str, Any]) -> list[dict[str, Any]]:
        """The activity's blocks without a leading heading that repeats its title.

        Owner, 2026-10-08 (item 31): the title and the description split. Brightspace shows the
        title above the field, and the wizard drops such a heading on the way back, so the build
        does not write it either. Recorded in the object map notes once per activity."""
        blocks = activity.get("blocks") or []
        if blocks and blocks[0].get("kind") == "heading":
            first = "".join(r.get("text", "") for r in blocks[0].get("runs", [])).strip().rstrip(":").strip()
            title = activity["title"].strip()
            if first == title or re.sub(r"^Week\s+\d+\s+", "", title) == first:  # a title that inherited its week still matches its heading
                self.note("info", "TITLE_HEADING_SPLIT", "The description's first heading repeats the activity title and is left to the object's title", activity["title"])
                return blocks[1:]
        return blocks

    def _external_links(self) -> list[dict[str, Any]]:
        """Every http(s) link in the rendered pages and editor fields, by object (13c, 2026-10-08)."""
        out: list[dict[str, Any]] = []
        for where, html_text in self.rendered_html.items():
            hrefs = sorted(set(re.findall(r'href="(https?://[^"]+)"', html_text)))
            if hrefs:
                out.append({"object": where, "links": [html.unescape(h) for h in hrefs]})
        return out

    def _object_map_markdown(self) -> str:
        lines = ["# Package object map", "", f"Base resource code: `{self.base_code}`", "", "## Module tree", ""]
        for module in self.structure:
            lines.append(f"- **{module['module']}**" + (" (hidden)" if module["hidden"] else ""))
            for item in module["items"]:
                lines.append(f"  - {item['type']}: {item['title']}" + (" (hidden)" if item["hidden"] else ""))
        lines += ["", "## Objects and joins", "", "| Kind | Title | Points | Gradebook item | Rubric | Resource code |", "|---|---|---|---|---|---|"]
        for obj in self.objects:
            if obj["kind"] in ("assignment", "discussion", "quiz"):
                points = "" if obj.get("points") is None else f"{obj['points']:g}"
                lines.append(f"| {obj['kind']} | {obj['title']} | {points} | {obj.get('grade_item') or ''} | {obj.get('rubric') or ''} | `{obj['resource_code']}` |")
        checklists = [obj for obj in self.objects if obj["kind"] == "checklist"]
        if checklists:
            lines += ["", "## Checklists", "", "| Checklist | Item | Ends | Items come from |", "|---|---|---|---|"]
            label = {d["utc"]: d["label"] for d in self.dates}
            for obj in checklists:
                for name, stamp in zip(obj.get("item_names", []), obj.get("item_dates", [])):
                    lines.append(f"| {obj['title']} | {name} | {label.get(stamp, '')} | {obj.get('items_source', '')} |")
        if self.dates:
            lines += ["", "## Dates", "", f"Time zone: {self.calendar.zone_name}. Package values are UTC.", "",
                      "| Object | Date for | Local | In the package |", "|---|---|---|---|"]
            for d in self.dates:
                lines.append(f"| {d['object']} | {d['kind']} | {d['label']} | `{d['utc']}` |")
        cleaned = self._cleaned_links()
        if cleaned:
            lines += ["", "## Link addresses cleaned for the package", "",
                      "The blueprint keeps the original addresses.", "", "| In the blueprint | In the package | Where |", "|---|---|---|"]
            lines += [f"| `{row['from']}` | `{row['to']}` | {'; '.join(row['where'])} |" for row in cleaned]
        lines += ["", "## Build notes", ""]
        lines += [f"- {n['severity'].upper()} {n['code']}: {n['message']}" + (f" [{n['where']}]" if n["where"] else "") for n in self.notes] or ["- None."]
        lines += ["", "## Shapes beyond the Workbench component library", ""]
        lines += [f"- {name}" for name in sorted(self.extensions_used)] or ["- None."]
        return "\n".join(lines) + "\n"


def _role(path: str) -> str:
    if path == "imsmanifest.xml":
        return "manifest"
    if path.startswith("orgunitconfig/"):
        return "orgunitconfig"
    if path.endswith(".html"):
        return "html_topic"
    for prefix, role in (("grades", "grades"), ("rubrics", "rubrics"), ("dropbox", "dropbox"), ("discussion", "discussion"),
                         ("checklist", "checklist"), ("quiz", "quiz")):
        if path.startswith(prefix):
            return role
    return "package_support"


def build_package(model: dict[str, Any], settings: dict[str, Any], out_dir: Path, *, settings_dir: Path, force: bool = False) -> int:
    try:
        builder = Builder(model, settings, settings_dir)
        result = builder.run(out_dir, force)
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"package: {result['package_dir']}")
    print(f"zip: {result['zip']} ({result['receipt']['zip']['bytes']} bytes)")
    print(f"objects: {len(builder.objects)}; codes: {len(builder.codes)}; build notes: {len(builder.notes)}")
    for note in builder.notes:
        print(f"  {note['severity'].upper()} {note['code']}: {note['message']}" + (f" [{note['where']}]" if note["where"] else ""))
    return 1 if result["errors"] else 0
