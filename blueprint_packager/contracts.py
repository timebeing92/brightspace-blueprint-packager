"""Validate owned authoring inputs before planning a package.

Extracted CourseCraft contracts are deliberately not authoring inputs.
Additional fields remain allowed for additive compatibility.
"""
from __future__ import annotations

from typing import Any
from jsonschema import Draft202012Validator


class ContractError(ValueError):
    pass


def _check(value: Any, schema: dict, name: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        e = errors[0]
        path = ".".join(str(p) for p in e.path) or "root"
        raise ContractError(f"{name} at {path}: {e.message}")


def validate_inputs(model: dict, settings: dict) -> None:
    array = {"type": "array"}
    obj = {"type": "object"}
    _check(model, {
        "type": "object", "required": ["schema", "source", "weeks", "pages", "modules", "links", "rubrics", "course_activities", "grade_plan", "diagnostics"],
        "properties": {
            "schema": {"const": "blueprint_packager.course_model/0.1"},
            "source": obj, "pages": array, "modules": array, "links": array, "rubrics": array,
            "course_activities": array, "diagnostics": array,
            "grade_plan": obj,
            "weeks": {"type": "array", "items": {"type": "object", "required": ["number", "title", "overview_page", "objectives", "resources", "assignments", "discussions", "quizzes", "checklist"],
                "properties": {"number": {"type": "integer", "minimum": 1}, "title": {"type": "string", "minLength": 1},
                               "overview_page": obj,
                               **{k: array for k in ("objectives", "resources", "assignments", "discussions", "quizzes")}}}},
        }}, "Course model")
    _check(settings, {
        "type": "object", "required": ["schema", "package"],
        "properties": {
            "schema": {"const": "blueprint_packager.build_settings/0.1"},
            "package": {"type": "object", "required": ["title", "base_resource_code"], "properties": {
                "title": {"type": "string", "minLength": 1}, "base_resource_code": {"type": "string", "minLength": 1},
                "manifest_identifier": {"type": "string", "minLength": 1}, "zip_name": {"type": "string", "pattern": r"^[^/\\]+\.zip$"}}},
            "build_mode": {"enum": ["ready", "preview"]}, "allow_model_errors": {"const": False},
            "retain_video_placeholders": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True},
            "video_link_fallbacks": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True},
            "calendar": obj,
        }}, "Build settings")
    weeks = [w["number"] for w in model["weeks"]]
    if len(weeks) != len(set(weeks)):
        raise ContractError("Course model: week numbers must be unique.")
    for page in model["pages"] + [w["overview_page"] for w in model["weeks"]]:
        _check(page, {"type": "object", "required": ["type", "title", "blocks"], "properties": {
            "type": {"const": "page"}, "title": {"type": "string", "minLength": 1}, "blocks": array}}, "Page")
    if model["grade_plan"] is not None:
        _check(model["grade_plan"], {"type": "object", "required": ["items", "total_computed"], "properties": {
            "total_computed": {"type": "number", "minimum": 0},
            "items": {"type": "array", "items": {"type": "object", "required": ["name", "points"], "properties": {
                "name": {"type": "string", "minLength": 1}, "points": {"type": "number", "minimum": 0}}}}}}, "Grading plan")
    activities = [a for w in model["weeks"] for key in ("assignments", "discussions", "quizzes") for a in w[key]] + model["course_activities"]
    for activity in activities:
        _check(activity, {"type": "object", "required": ["type", "title", "blocks"], "properties": {
            "type": {"enum": ["assignment", "discussion", "quiz"]}, "title": {"type": "string", "minLength": 1},
            "points": {"type": ["number", "null"], "minimum": 0}, "blocks": array,
            **{key: {"type": "string"} for key in ("grade_item", "rubric", "forum")}}}, "Activity")
    for rubric in model["rubrics"]:
        _check(rubric, {"type": "object", "required": ["name", "used_by", "grid"], "properties": {
            "name": {"type": "string", "minLength": 1}, "used_by": {"type": "array", "items": {"type": "string"}},
            "grid": {"type": ["object", "null"], "required": ["levels", "criteria"], "properties": {"levels": array, "criteria": array}}}}, "Rubric")
    for kind in ("modules", "links"):
        for item in model[kind]:
            _check(item, {"type": "object", "required": ["title", "type"], "properties": {
                "title": {"type": "string", "minLength": 1}, "type": {"const": "module" if kind == "modules" else "link"}}}, kind)

    def blocks(items, where):
        for index, block in enumerate(items):
            label = f"{where} block {index + 1}"
            _check(block, {"type": "object", "required": ["kind"], "properties": {"kind": {"enum": [
                "p", "li", "heading", "dropdown", "visual", "table", "video", "placeholder", "image"]}}}, label)
            kind = block["kind"]
            if kind in ("p", "li", "heading"):
                _check(block, {"required": ["runs"], "properties": {"runs": {"type": "array", "items": {
                    "type": "object", "required": ["text"], "properties": {"text": {"type": "string"}, "href": {"type": "string"}}}}}}, label)
            if kind == "heading":
                _check(block, {"required": ["level"], "properties": {"level": {"type": "integer", "minimum": 1, "maximum": 6}}}, label)
            if kind in ("dropdown", "visual"):
                field = "title" if kind == "dropdown" else "cue"
                _check(block, {"required": [field, "blocks"], "properties": {field: {"type": "string"}, "blocks": array}}, label)
                blocks(block["blocks"], label)
            if kind == "table":
                _check(block, {"required": ["rows"], "properties": {"rows": {"type": "array", "items": {
                    "type": "array", "items": {"type": "array"}}}}}, label)
                for row in block["rows"]:
                    for cell in row:
                        blocks(cell, label)
            if kind in ("video", "placeholder"):
                field = "title" if kind == "video" else "text"
                _check(block, {"required": [field], "properties": {field: {"type": "string"}, "href": {"type": "string"}, "placeholder": {"type": "boolean"}}}, label)
    for item in model["pages"] + activities:
        blocks(item.get("blocks", []), item.get("title", "content"))
    for week in model["weeks"]:
        for field in ("objectives", "resources"):
            blocks(week[field], f"{week['title']} {field}")
        if week["overview_page"]:
            blocks(week["overview_page"]["blocks"], week["title"])
