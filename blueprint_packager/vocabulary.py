"""Canonical structure vocabulary for a packager-readable flat blueprint.

A flat blueprint is a Word/Google document. Structure has to survive a Google
Docs round trip, so it is carried by text, not by custom Word styles:

* fixed section headings and week-table row labels (the Blueprint Wizard
  template wording), and
* directive lines: a whole paragraph that starts with a reserved keyword
  followed by a colon, for example ``Assignment: Week 2 Assignment: ...``.

Everything else in the document is authored content and is never rewritten.

The wizard already emits several of these lines (``Points:``, ``Rubric:``,
``Gradebook item:``, ``Dropdown / expandable section:``, ``Visual cue:``,
``Video embed:``). This vocabulary keeps those spellings and adds the few
lines a packager needs to read a blueprint without guessing: explicit object
types, explicit placement, and explicit block endings.
"""
from __future__ import annotations

import re

VOCABULARY_VERSION = "blueprint-structure/0.1"

# --- top-level headings (Heading 2) ---------------------------------------------
H_COURSE_INTRO = "Course Introduction"
H_BEFORE_WEEK_1 = "Before Week 1: Additional Resources and Information"
H_COURSE_ACTIVITIES = "Unplaced Activities"  # wizard wording, kept
H_RUBRICS = "Rubric Appendix"
H_RETIRED_RUBRICS = "Retired Rubrics (not built)"
H_NOTES = "Extraction Notes"
WEEK_HEADING_RE = re.compile(r"^Week\s+(\d{1,2})\s*[-–—:]\s*(.*)$")

# --- week table row labels (matched by prefix, wizard wording kept) -------------
SECTION_LABELS = [
    ("overview", "Overview:", "Overview: (add an introduction to the week's topic and activities here, with references as needed)"),
    ("objectives", "Learning Objectives:", "Learning Objectives: Must follow the guidelines in this Learning Objectives Guide."),
    ("resources", "Assigned Reading and Multimedia:", "Assigned Reading and Multimedia: (add links, articles, textbook readings, videos). Include style-correct citations."),
    ("assignments", "Assignment(s) and Instructions:", "Assignment(s) and Instructions:"),
    ("discussions", "Discussion Board Prompts:", "Discussion Board Prompts:"),
    ("checklist", "Checklist", "Checklist"),
]
SECTION_KEYS = [key for key, _prefix, _label in SECTION_LABELS]
OBJECTIVES_SUBLABEL = "Students will be able to:"

# --- front matter table labels (matched by prefix) -------------------------------
FRONT_LABELS = {
    "course_description": "COURSE DESCRIPTION",
    "required_materials": "TEXTBOOK/S OR REQUIRED MATERIALS",
    "course_learning_outcomes": "COURSE LEARNING OUTCOMES",
}
GRADE_PLAN_HEADER = ("Assignment", "Points")
GRADE_PLAN_TOTAL = "Total Points"

# --- directive keywords -----------------------------------------------------------
# object openers
D_MODULE = "Module"
D_PAGE = "Page"
D_LINK = "Link"
D_ASSIGNMENT = "Assignment"
D_DISCUSSION = "Discussion"
D_QUIZ = "Quiz"
D_CHECKLIST = "Checklist"
D_RUBRIC_USED_BY = "Used by"
OBJECT_OPENERS = (D_MODULE, D_PAGE, D_LINK, D_ASSIGNMENT, D_DISCUSSION, D_QUIZ, D_CHECKLIST)

# Openers are section-scoped: a keyword opens an object only where that object
# type can live. Elsewhere the same words are ordinary authored content.
SCOPE_COURSE_PAGES = (D_MODULE, D_PAGE, D_LINK)
SCOPE_OVERVIEW = (D_PAGE,)
SCOPE_ASSIGNMENTS = (D_ASSIGNMENT, D_QUIZ)
SCOPE_DISCUSSIONS = (D_DISCUSSION,)
SCOPE_CHECKLIST = (D_CHECKLIST,)
SCOPE_ACTIVITIES = (D_ASSIGNMENT, D_DISCUSSION, D_QUIZ)
# A module row before Week 1 may hold the module's pages, links, and activities.
# Whatever sits under a Module line belongs to that module.
SCOPE_PRE_WEEK = SCOPE_COURSE_PAGES + SCOPE_ACTIVITIES

# object attributes (must directly follow an opener or another attribute)
D_PAGE_HEADING = "Page heading"
D_PLACEMENT = "Placement"
D_VISIBILITY = "Visibility"
D_URL = "URL"
D_POINTS = "Points"
D_GRADE_ITEM = "Gradebook item"
D_RUBRIC = "Rubric"
D_FORUM = "Forum"
D_SOURCE = "Source"
D_ATTEMPTS = "Attempts allowed"
D_TIME_LIMIT = "Time limit"
D_SECTIONS = "Sections"
D_QUESTION_TYPES = "Question types"
D_ITEMS = "Items"
# A checklist can list its own items, or say that its items are built from the
# activities of its week. Authored items under such a checklist are extra items.
ITEMS_FROM_ACTIVITIES = "From this week's activities"
OBJECT_ATTRIBUTES = (
    D_PAGE_HEADING, D_PLACEMENT, D_VISIBILITY, D_URL, D_POINTS, D_GRADE_ITEM, D_RUBRIC,
    D_FORUM, D_SOURCE, D_ATTEMPTS, D_TIME_LIMIT, D_SECTIONS, D_QUESTION_TYPES, D_ITEMS,
)

# inline block markers inside page/activity bodies
D_DROPDOWN = "Dropdown / expandable section"
D_DROPDOWN_END = "End of dropdown / expandable section"
D_VISUAL = "Visual cue"
D_VISUAL_END = "End of visual cue"
D_VIDEO = "Video embed"
D_IMAGE = "Embedded image"
BLOCK_MARKERS = (D_DROPDOWN, D_VISUAL, D_VIDEO, D_IMAGE)
BLOCK_END_MARKERS = (D_DROPDOWN_END, D_VISUAL_END)

VISIBILITY_HIDDEN = "Hidden from students"
VISIBILITY_VISIBLE = "Visible to students"

ALL_DIRECTIVES = tuple(
    sorted(set(OBJECT_OPENERS + OBJECT_ATTRIBUTES + BLOCK_MARKERS + (D_RUBRIC_USED_BY,)), key=len, reverse=True)
)
_DIRECTIVE_RE = re.compile(r"^(" + "|".join(re.escape(k) for k in ALL_DIRECTIVES) + r"):\s*(.*)$", re.S)


# Bracket tags: a shorter way to mark a block by hand. "[dropdown: Title]" opens a
# dropdown and "[/dropdown]" closes it; "[callout]" ... "[/callout]" and
# "[timeline]" ... "[/timeline]" mark visual cues. They read exactly like the
# longer marker lines, which the wizard writes and which stay accepted.
BRACKET_BLOCKS = {
    "dropdown": (D_DROPDOWN, D_DROPDOWN_END, None),
    "callout": (D_VISUAL, D_VISUAL_END, "Callout"),
    "timeline": (D_VISUAL, D_VISUAL_END, "Timeline"),
    "box": (D_VISUAL, D_VISUAL_END, "Styled section"),
}
_BRACKET_RE = re.compile(r"^\[\s*(/?)\s*([A-Za-z]+)\s*(?::\s*(.*?))?\s*\]$", re.S)


def parse_bracket_block(text: str) -> tuple[str, str] | None:
    """Return the (keyword, value) a bracket tag stands for, or None."""
    match = _BRACKET_RE.match(text.strip())
    if not match:
        return None
    closing, name, title = match.group(1) == "/", match.group(2).lower(), (match.group(3) or "").strip()
    if name not in BRACKET_BLOCKS:
        return None
    opener, closer, cue = BRACKET_BLOCKS[name]
    if closing:
        return closer, ""
    if cue is None:
        return opener, title
    return opener, cue


def parse_directive(text: str) -> tuple[str, str] | None:
    """Return (keyword, value) when the paragraph text is a directive line."""
    stripped = text.strip()
    if stripped in BLOCK_END_MARKERS:
        return stripped, ""
    bracket = parse_bracket_block(stripped)
    if bracket:
        return bracket
    match = _DIRECTIVE_RE.match(stripped)
    if not match:
        return None
    return match.group(1), match.group(2).strip()


def format_points(value: float | int) -> str:
    number = float(value)
    text = str(int(number)) if number.is_integer() else f"{number:g}"
    return f"{text} pts"


def parse_points(value: str) -> float | None:
    match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(?:pts?|points?)?\s*$", value)
    return float(match.group(1)) if match else None


def section_for_label(text: str) -> str | None:
    stripped = text.strip()
    for key, prefix, _label in SECTION_LABELS:
        if stripped.startswith(prefix):
            return key
    return None
