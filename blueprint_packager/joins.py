"""Join resolution and validation for a course model.

Every relationship a Brightspace package needs is made explicit here and
checked from both sides: activity -> grade item, activity -> rubric,
rubric -> activities, object -> module placement, discussion -> forum,
checklist -> week. Nothing is matched fuzzily; titles must be identical.
"""
from __future__ import annotations

import re
from typing import Any
from collections import Counter
from .authoring import absolute_web_url

from .render_text import plain

TYPE_LABEL = {"assignment": "Assignment", "discussion": "Discussion", "quiz": "Quiz"}


def all_activities(model: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for week in model["weeks"]:
        for key in ("assignments", "discussions", "quizzes"):
            out.extend(week[key])
    out.extend(a for a in model["course_activities"] if a["type"] in TYPE_LABEL)
    return out


def module_titles(model: dict[str, Any]) -> list[str]:
    return [m["title"] for m in model["modules"]] + [w["title"] for w in model["weeks"]]


def first_heading(blocks: list[dict[str, Any]]) -> str | None:
    for block in blocks:
        if block["kind"] == "heading":
            return plain(block["runs"])
    return None


def resolve(model: dict[str, Any]) -> dict[str, Any]:
    """Return {"joins": [...], "diagnostics": [...]} for the model."""
    joins: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []

    def diag(severity: str, code: str, message: str, where: str = "") -> None:
        diagnostics.append({"severity": severity, "code": code, "message": message, "where": where})

    def join(kind: str, source: str, target: str, status: str, detail: str = "") -> None:
        joins.append({"kind": kind, "from": source, "to": target, "status": status, "detail": detail})

    plan = {item["name"]: item["points"] for item in (model.get("grade_plan") or {}).get("items", [])}
    rubrics = {rubric["name"]: rubric for rubric in model["rubrics"]}
    modules = module_titles(model)
    activities = all_activities(model)
    labels: dict[str, dict[str, Any]] = {}
    used_grade_items: dict[str, str] = {}
    for label, names in (
        ("GRADE_ITEM", [i["name"] for i in (model.get("grade_plan") or {}).get("items", [])]),
        ("RUBRIC", [r["name"] for r in model["rubrics"]]),
        ("MODULE", modules),
        ("PAGE", [p["title"] for p in model["pages"]] + [w["overview_page"]["title"] for w in model["weeks"] if w["overview_page"]]),
    ):
        for name, count in Counter(names).items():
            if count > 1:
                diag("error", f"{label}_TITLE_DUPLICATE", f"{count} {label.lower().replace('_', ' ')} entries share the title '{name}'; give each object an exact unique title.", name)

    for activity in activities:
        label = f"{TYPE_LABEL[activity['type']]}: {activity['title']}"
        if label in labels:
            diag("error", "ACTIVITY_TITLE_DUPLICATE", f"Two activities are titled '{activity['title']}'", label)
        labels[label] = activity
        where = label if not activity.get("week") else f"Week {activity['week']} / {label}"
        # grade item + points
        grade_item = activity.get("grade_item")
        if grade_item:
            if grade_item not in plan:
                diag("error", "GRADE_ITEM_UNKNOWN", f"Gradebook item '{grade_item}' is not a row of the points table", where)
                join("activity→grade item", label, grade_item, "unresolved")
            else:
                if grade_item in used_grade_items:
                    diag("error", "GRADE_ITEM_SHARED", f"Gradebook item '{grade_item}' is claimed by two activities", where)
                used_grade_items[grade_item] = label
                points = activity.get("points")
                if points is None:
                    diag("error", "POINTS_MISSING", f"Graded activity states no points; points table says {plan[grade_item]:g}", where)
                    join("activity→grade item", label, grade_item, "points missing", f"{plan[grade_item]:g} in the points table")
                elif abs(points - plan[grade_item]) > 1e-9:
                    # Keep both values visible; the builder requires a recorded determination.
                    diag("warning", "POINTS_DIFFER_FROM_GRADE_ROW",
                         f"Activity says {points:g} pts; its points table row says {plan[grade_item]:g}. Reconcile the values or record a points determination before building.", where)
                    join("activity→grade item", label, grade_item, "resolved", f"{points:g} pts (points table row says {plan[grade_item]:g})")
                else:
                    join("activity→grade item", label, grade_item, "resolved", f"{plan[grade_item]:g} pts")
        elif activity.get("points"):
            diag("error", "POINTS_WITHOUT_GRADE_ITEM", "Activity has points but no gradebook item", where)
        else:
            join("activity→grade item", label, "(ungraded)", "none", "no points and no gradebook item")
        # rubric
        rubric_name = activity.get("rubric")
        if rubric_name:
            rubric = rubrics.get(rubric_name)
            if rubric is None:
                diag("error", "RUBRIC_UNKNOWN", f"Rubric '{rubric_name}' has no heading in the Rubric Appendix", where)
                join("activity→rubric", label, rubric_name, "unresolved")
            elif label not in rubric["used_by"]:
                diag("error", "RUBRIC_NOT_RECIPROCAL", f"Rubric '{rubric_name}' does not list this activity under 'Used by'", where)
                join("activity→rubric", label, rubric_name, "one-sided")
            else:
                join("activity→rubric", label, rubric_name, "resolved")
        elif activity.get("grade_item") and activity["type"] != "quiz":
            diag("warning", "GRADED_WITHOUT_RUBRIC", "Graded activity has no rubric", where)
        # title vs points-table row (informational: the row stays as written and is the join)
        if grade_item and grade_item in plan and re.sub(r"\W+", "", grade_item).lower() != re.sub(r"\W+", "", activity["title"]).lower():
            diag("info", "TITLE_DIFFERS_FROM_GRADE_ROW",
                 f"Object title '{activity['title']}' differs from its points table row '{grade_item}'", where)
        # heading vs title (informational: both stay as written)
        heading = first_heading(activity.get("blocks", []))
        if heading and re.sub(r"\W+", "", heading).lower() != re.sub(r"\W+", "", activity["title"]).lower():
            diag("info", "TITLE_DIFFERS_FROM_BODY_HEADING",
                 f"Object title '{activity['title']}' differs from the activity's own first heading '{heading}'", where)
        # forum
        if activity["type"] == "discussion":
            if activity.get("forum"):
                join("discussion→forum", label, activity["forum"], "resolved")
            else:
                diag("error", "FORUM_MISSING", "Discussion names no forum", where)
        # placement
        for placement in activity.get("placement", []) or []:
            if placement not in modules:
                diag("error", "PLACEMENT_UNKNOWN", f"Placement '{placement}' is not a declared module or week", where)
                join("object→module", label, placement, "unresolved")
            else:
                join("object→module", label, placement, "resolved")
        if activity.get("week"):
            join("object→module", label, next(w["title"] for w in model["weeks"] if w["number"] == activity["week"]), "resolved", "week section")
        elif not activity.get("placement"):
            join("object→module", label, "(no module link)", "none", "course-level activity reached through its tool, not a module")

    # rubric side
    for rubric in model["rubrics"]:
        for user in rubric["used_by"]:
            if user not in labels:
                diag("error", "RUBRIC_USER_UNKNOWN", f"'Used by: {user}' matches no activity", f"rubric '{rubric['name']}'")
            elif labels[user].get("rubric") != rubric["name"]:
                diag("error", "RUBRIC_NOT_RECIPROCAL", f"'{user}' does not name this rubric", f"rubric '{rubric['name']}'")
        if not rubric["used_by"]:
            diag("warning", "RUBRIC_UNATTACHED", "Rubric is not used by any activity", f"rubric '{rubric['name']}'")
            join("rubric→activity", rubric["name"], "(none)", "unattached")

    # grade plan coverage
    for name, points in plan.items():
        if name not in used_grade_items:
            diag("error", "GRADE_ITEM_ORPHAN", f"Points table row '{name}' ({points:g} pts) has no activity", "points table")
            join("grade item→activity", name, "(none)", "orphan")

    # pages and links placement
    for obj in model["pages"] + model["links"]:
        label = f"{obj['type'].title()}: {obj['title']}"
        placements = obj.get("placement") or []
        if not placements:
            diag("error", "PLACEMENT_MISSING", "Object has no placement", label)
        for placement in placements:
            if placement not in modules:
                diag("error", "PLACEMENT_UNKNOWN", f"Placement '{placement}' is not a declared module or week", label)
                join("object→module", label, placement, "unresolved")
            else:
                join("object→module", label, placement, "resolved")
        if obj["type"] == "link" and not absolute_web_url(obj.get("url", "")):
            diag("error", "LINK_URL", "Link has no absolute URL", label)
    for week in model["weeks"]:
        if week["overview_page"]:
            join("object→module", f"Page: {week['overview_page']['title']}", week["title"], "resolved", "week overview")
        if week["checklist"]:
            join("object→module", f"Checklist: {week['checklist']['title']}", week["title"], "resolved", "week checklist")
        else:
            diag("warning", "CHECKLIST_MISSING", "Week has no checklist", week["title"])

    # checklist items that mention an activity type the week does not have
    for week in model["weeks"]:
        if not week["checklist"]:
            continue
        has = {"quiz": bool(week["quizzes"]), "discussion": bool(week["discussions"]), "assignment": bool(week["assignments"])}
        for item in week["checklist"].get("items", []):
            other_week = re.search(r"\bWeek\s+(\d+)\b", "".join(run["text"] for run in item.get("runs", [])))
            if other_week and int(other_week.group(1)) != week["number"]:
                continue  # the item points at another week's activity on purpose
            text = plain(item["runs"])
            for word, present in has.items():
                if re.search(rf"\b{word}\b", text, re.I) and not present:
                    diag("warning", "CHECKLIST_ITEM_STALE",
                         f"Checklist item '{text}' mentions a {word}, and this week has none", week["title"])
        if not week["checklist"].get("items") and not week["checklist"].get("derive"):
            diag("warning", "CHECKLIST_EMPTY", "Checklist has no items", week["title"])
        if week["checklist"].get("derive") and not (week["discussions"] or week["assignments"] or week["quizzes"]) \
                and not week["checklist"].get("items"):
            diag("warning", "CHECKLIST_EMPTY", "Checklist is built from the week's activities, and the week has none", week["title"])

    return {"joins": joins, "diagnostics": diagnostics}
