"""A blank blueprint in the current convention, for writing a course from nothing.

Every row the reader knows is present, with the prompts an author needs and
nothing else that would be built. The frame is Heading 1; content starts at
Heading 2; each week carries a Checklist row pre-filled with the "Items: From
this week's activities" line, which the author may replace with typed items
(owner's decision, 2026-10-08). The result reads with zero errors as it
stands, so a course can be built from it the moment it has content.

Presentation (2026-10-09, on the owner's notes): a short guide and key at the
top as plain paragraphs, which the reader keeps as title lines and never
builds; live examples of a dropdown, a callout, and an internal link inside
Week 1 where they read as real content; room to breathe in the tables; label
rows shaded; prompts in grey italics so they are told apart from structure
lines; the course's navy for headings.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from . import vocabulary as V

NAVY = RGBColor(0x10, 0x39, 0x45)
BRAND = RGBColor(0x17, 0x4B, 0x5C)
GREY = RGBColor(0x5B, 0x6B, 0x72)
LABEL_FILL = "EDF4F6"
HEADER_FILL = "174B5C"

# Prompt lines are italic grey; structure lines (a keyword, a colon, a value) stay upright.
ROW_PROMPTS = {
    "overview": ["Page: Week {n} Overview", "Page heading: Week {n} – {topic}",
                 "(Introduce the week here. Headings inside a page start at Heading 2.)"],
    "objectives": [V.OBJECTIVES_SUBLABEL, "(One objective per bullet.)"],
    "resources": ["(Readings, media, and links. Use a Heading 2 for each group if you group them.)"],
    "assignments": ["Assignment: Week {n} Assignment: (title)", "Points: 10 pts",
                    "Gradebook item: Week {n} Assignment: (title)", "Rubric: Standard Assignment Rubric",
                    "(Instructions. Headings inside an activity start at Heading 2. Change the points here and in the points table together.)"],
    "discussions": ["Discussion: Week {n} Discussion: (title)", "Points: 5 pts",
                    "Gradebook item: Week {n} Discussion: (title)", "Rubric: Standard Discussion Rubric", "Forum: Discussions",
                    "(Prompt. Say when the first post and the responses are due by day of the week, not by date.)"],
    "checklist": ["Checklist: Week {n} Checklist", f"{V.D_ITEMS}: {V.ITEMS_FROM_ACTIVITIES}",
                  "(Leave the Items line to build the list from this week's activities, or replace it with typed items.)"],
}

# Week 1's overview carries worked examples of the three forms authors ask about most.
WEEK_1_OVERVIEW_EXAMPLES = [
    "Page: Week 1 Overview", "Page heading: Week 1 – {topic}",
    "(Introduce the week here. The three examples below are real: keep, change, or delete them.)",
    "[dropdown: Example dropdown – a panel the reader opens]",
    "(Anything between the bracket lines is inside the panel: paragraphs, bullets, links.)",
    "[/dropdown]",
    "[callout tone=gold]",
    "(A callout for something to keep in mind. Leave out tone=gold for the plain navy callout.)",
    "[/callout]",
    "(An internal link reads like this:) Start with the [link to assignment: Week 1 Assignment: (title) | first assignment] before the discussion.",
]

GUIDE = [
    ("How to use this document", [
        "This is a course blueprint: one Word file that a tool turns into a complete Brightspace course. "
        "Write in it as you would any document; the structure comes from a few plain lines, listed in the key below.",
        "Each week is one table with six rows. Fill the rows in order; leave a row's prompt in place if you have nothing for it yet.",
        "Headings are one to one with the page. The big Heading 1 lines are the frame and are already in place; inside a page or an activity, start at Heading 2.",
        "Real bullets, real numbering, bold and italic all come through. Never type dates; say the day of the week and the build adds the term's dates.",
        "Grey italic text in parentheses is a prompt. Replace it or delete it. Upright text is structure: keep its shape and change its words.",
        "These notes at the top are kept with the document but never built into the course; delete them whenever you like.",
    ]),
    ("Key: the lines that make structure", [
        "Page: Title  /  Page heading: Title — a content page and the title shown on it.",
        "Placement: Module name — where a page goes when it is not in its week.",
        "Assignment: Title  /  Discussion: Title — an activity. Under it: Points: N pts, Gradebook item: Name, Rubric: Name, and for a discussion Forum: Name.",
        "Checklist: Title — a week's checklist; the line Items: From this week's activities builds it, or type the items.",
        "Module: Name — before Week 1, a module of its own; its pages and links follow on the lines below.",
        "Link: Title  /  URL: https://… — an external link in a module.",
        "Used by: Assignment: Title — under a rubric, each activity that uses it.",
        "[dropdown: Title] … [/dropdown] — an expandable panel.  [callout] … [/callout] — a highlighted box; [callout tone=gold] for a warm one.  [timeline] … [/timeline] and [box] … [/box] are also available.",
        "[link to assignment: Title | words] — a link to the course's own object; also link to discussion, quiz, checklist, or page. The words after the bar are what the reader clicks.",
    ]),
]


# ------------------------------------------------------------------ styling helpers
def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _cell_margins(table, top: int = 100, bottom: int = 100, left: int = 140, right: int = 140) -> None:
    """Breathing room inside every cell, in twentieths of a point."""
    tbl_pr = table._tbl.tblPr
    margins = OxmlElement("w:tblCellMar")
    for side, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    tbl_pr.append(margins)


def _borders(table, color: str = "C7D8DC") -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "4")
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), color)
        borders.append(node)
    tbl_pr.append(borders)


def _is_prompt(line: str) -> bool:
    return line.startswith("(") and line.endswith(")")


def _is_structure(line: str) -> bool:
    return V.parse_directive(line) is not None or V.parse_bracket_block(line) is not None


def _write_line(para, line: str) -> None:
    """One line into a paragraph: prompts grey italic, structure keywords bold navy, text plain."""
    para.paragraph_format.space_after = Pt(4)
    if _is_prompt(line):
        run = para.add_run(line)
        run.italic = True
        run.font.color.rgb = GREY
        return
    if line.startswith("["):
        run = para.add_run(line)
        run.font.color.rgb = BRAND
        run.bold = True
        return
    if _is_structure(line) and ":" in line:
        keyword, rest = line.split(":", 1)
        lead = para.add_run(keyword + ":")
        lead.bold = True
        lead.font.color.rgb = NAVY
        para.add_run(rest)
        return
    if line.startswith("(An internal link reads like this:)"):
        note, rest = line.split(")", 1)
        prompt = para.add_run(note + ")")
        prompt.italic = True
        prompt.font.color.rgb = GREY
        para.add_run(rest)
        return
    para.add_run(line)


def _fill(cell, lines: list[str], label: bool = False) -> None:
    first = True
    for line in lines:
        para = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        if label:
            run = para.add_run(line)
            run.bold = True
            run.font.color.rgb = NAVY
            para.paragraph_format.space_after = Pt(2)
            para.paragraph_format.space_before = Pt(2)
            continue
        _write_line(para, line)


def _no_split(row) -> None:
    """A row never breaks across pages, so a shaded label is not left alone at a page's top."""
    tr_pr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    tr_pr.append(cant)


def _one_column(doc, rows: list[list[str]], label_rows: set[int] | None = None):
    table = doc.add_table(rows=len(rows), cols=1)
    table.autofit = True
    _borders(table)
    _cell_margins(table)
    for index, lines in enumerate(rows):
        is_label = index in (label_rows or set())
        row = table.rows[index]
        _no_split(row)
        cell = row.cells[0]
        if is_label:
            _shade(cell, LABEL_FILL)
        _fill(cell, lines, label=is_label)
        if is_label:
            for para in cell.paragraphs:
                para.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return table


def _style_document(doc) -> None:
    section = doc.sections[0]
    section.left_margin = section.right_margin = Inches(1)
    section.top_margin = section.bottom_margin = Inches(0.9)
    normal = doc.styles["Normal"]
    normal.font.name = "Lato"
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Lato")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    normal.paragraph_format.line_spacing = 1.15
    for name, size, before, after in (("Title", 26, 0, 6), ("Heading 1", 18, 20, 8), ("Heading 2", 14, 12, 4), ("Heading 3", 12, 10, 3)):
        style = doc.styles[name]
        style.font.name = "Lato"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = NAVY
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)


def _guide(doc) -> None:
    for heading, lines in GUIDE:
        para = doc.add_paragraph()
        run = para.add_run(heading)
        run.bold = True
        run.font.color.rgb = BRAND
        run.font.size = Pt(12)
        para.paragraph_format.space_before = Pt(10)
        para.paragraph_format.space_after = Pt(4)
        for line in lines:
            item = doc.add_paragraph(style="List Bullet")
            item.paragraph_format.space_after = Pt(3)
            if " — " in line and heading.startswith("Key"):
                term, rest = line.split(" — ", 1)
                lead = item.add_run(term)
                lead.bold = True
                lead.font.color.rgb = NAVY
                item.add_run(" — " + rest)
            else:
                item.add_run(line)


def write_blank(path: Path, *, course_number: str, course_title: str, term: str, weeks: int = 8,
                topics: list[str] | None = None) -> Path:
    topics = list(topics or [])
    doc = Document()
    _style_document(doc)
    doc.add_paragraph("Blueprint", style="Title")
    sub = doc.add_paragraph(f"{course_number} {course_title} – {term} Blueprint")
    sub.runs[0].font.size = Pt(13)
    sub.runs[0].font.color.rgb = GREY
    _guide(doc)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # front matter, in the labelled one-column tables the reader expects
    _one_column(doc, [[V.FRONT_LABELS["course_description"] + " (catalog)"], ["(Catalog description.)"]], {0})
    _one_column(doc, [[V.FRONT_LABELS["required_materials"]], ["(Textbook or required materials, with citations.)"]], {0})
    _one_column(doc, [[V.FRONT_LABELS["course_learning_outcomes"]], ["(One outcome per paragraph.)"]], {0})
    intro = doc.add_paragraph("Points table. One row per graded activity; the names must match the activity lines below, and the points must agree.")
    intro.runs[0].font.color.rgb = GREY
    intro.runs[0].italic = True
    grade_rows = []
    for n in range(1, weeks + 1):
        grade_rows += [(f"Week {n} Assignment: (title)", 10), (f"Week {n} Discussion: (title)", 5)]
    table = doc.add_table(rows=len(grade_rows) + 2, cols=2)
    _borders(table)
    _cell_margins(table, top=60, bottom=60)
    for cell, text in zip(table.rows[0].cells, V.GRADE_PLAN_HEADER):
        _shade(cell, HEADER_FILL)
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for index, (name, points) in enumerate(grade_rows, start=1):
        table.rows[index].cells[0].paragraphs[0].add_run(name)
        table.rows[index].cells[1].paragraphs[0].add_run(str(points))
    total = table.rows[-1]
    _shade(total.cells[0], LABEL_FILL)
    _shade(total.cells[1], LABEL_FILL)
    total.cells[0].paragraphs[0].add_run(V.GRADE_PLAN_TOTAL).bold = True
    total.cells[1].paragraphs[0].add_run(str(sum(p for _n, p in grade_rows))).bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    doc.add_paragraph(V.H_COURSE_INTRO, style="Heading 1")
    for line in ("Page: Welcome", f"Page heading: Welcome to {course_number}", "Placement: Getting Started",
                 "(Welcome text. Add more pages with their own Page: and Page heading: lines.)"):
        _write_line(doc.add_paragraph(), line)

    doc.add_paragraph(V.H_BEFORE_WEEK_1, style="Heading 1")
    note = doc.add_paragraph("One row per module. The first line of a row names the module; the rest are its pages and links.")
    note.runs[0].italic = True
    note.runs[0].font.color.rgb = GREY
    _one_column(doc, [
        ["Getting Started"],
        [f"{V.D_MODULE}: Getting Started", "Page: Student Resources", "Page heading: Student and Course Resources",
         "(Resources text.)", "Link: Syllabus", "URL: https://", "Placement: Getting Started"],
    ], {0})

    for n in range(1, weeks + 1):
        topic = topics[n - 1] if n - 1 < len(topics) else "(topic)"
        doc.add_paragraph(f"Week {n} - {topic}", style="Heading 1")
        rows = []
        for key, _prefix, label in V.SECTION_LABELS:
            rows.append([label])
            source = WEEK_1_OVERVIEW_EXAMPLES if (n == 1 and key == "overview") else ROW_PROMPTS[key]
            rows.append([line.format(n=n, topic=topic) for line in source])
        _one_column(doc, rows, {i for i in range(0, len(rows), 2)})

    doc.add_paragraph(V.H_COURSE_ACTIVITIES, style="Heading 1")
    _write_line(doc.add_paragraph(), "(Activities that belong to no week, such as a course questions forum. Delete if none.)")
    doc.add_paragraph(V.H_RUBRICS, style="Heading 1")
    rub_note = doc.add_paragraph("One rubric per Heading 2: its name, then one 'Used by:' line per activity, then its table. "
                                 "Level headers carry a percentage; criterion labels carry a weight in percent; weights add to 100.")
    rub_note.runs[0].italic = True
    rub_note.runs[0].font.color.rgb = GREY
    for name, kind in (("Standard Assignment Rubric", "Assignment"), ("Standard Discussion Rubric", "Discussion")):
        doc.add_paragraph(name, style="Heading 2")
        for n in range(1, weeks + 1):
            _write_line(doc.add_paragraph(), f"Used by: {kind}: Week {n} {kind}: (title)")
        grid = doc.add_table(rows=3, cols=4)
        _borders(grid)
        _cell_margins(grid, top=60, bottom=60)
        for cell, text in zip(grid.rows[0].cells, ("Criterion", "Exemplary — 100%", "Proficient — 80%", "Developing — 50%")):
            _shade(cell, LABEL_FILL)
            run = cell.paragraphs[0].add_run(text)
            run.bold = True
            run.font.color.rgb = NAVY
        for row, first in zip(grid.rows[1:], ("(first criterion) (50%)", "(second criterion) (50%)")):
            for cell, text in zip(row.cells, (first, "(descriptor)", "(descriptor)", "(descriptor)")):
                _write_line(cell.paragraphs[0], text)
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
    doc.add_paragraph(V.H_NOTES, style="Heading 1")
    _write_line(doc.add_paragraph(), "(Notes to the builder that are not course content.)")
    doc.save(str(path))
    return path
