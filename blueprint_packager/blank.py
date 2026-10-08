"""A blank blueprint in the current convention, for writing a course from nothing.

Every row the reader knows is present, with the prompts an author needs and
nothing else. The frame is Heading 1; content starts at Heading 2; each week
carries a Checklist row pre-filled with the "Items: From this week's
activities" line, which the author may replace with typed items (owner's
decision, 2026-10-08). The result reads with zero errors as it stands, so a
course can be built from it the moment it has content.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt

from . import vocabulary as V

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


def _fill(cell, lines: list[str], first_bold: bool = False) -> None:
    first = True
    for line in lines:
        para = cell.paragraphs[0] if first else cell.add_paragraph()
        run = para.add_run(line)
        if first and first_bold:
            run.bold = True
        first = False


def _one_column(doc, rows: list[list[str]], label_rows: set[int] | None = None):
    table = doc.add_table(rows=len(rows), cols=1)
    table.style = "Table Grid"
    for index, lines in enumerate(rows):
        _fill(table.rows[index].cells[0], lines, first_bold=index in (label_rows or set()))
    return table


def write_blank(path: Path, *, course_number: str, course_title: str, term: str, weeks: int = 8,
                topics: list[str] | None = None) -> Path:
    topics = list(topics or [])
    doc = Document()
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_paragraph("Blueprint", style="Title")
    doc.add_paragraph(f"{course_number} {course_title} – {term} Blueprint")

    # front matter, in the labelled one-column tables the reader expects
    _one_column(doc, [[V.FRONT_LABELS["course_description"] + " (catalog)"], ["(Catalog description.)"]], {0})
    _one_column(doc, [[V.FRONT_LABELS["required_materials"]], ["(Textbook or required materials, with citations.)"]], {0})
    _one_column(doc, [[V.FRONT_LABELS["course_learning_outcomes"]], ["(One outcome per paragraph.)"]], {0})
    doc.add_paragraph("")
    doc.add_paragraph("Points table. One row per graded activity; the names must match the activity lines below.")
    grade_rows = []
    for n in range(1, weeks + 1):
        grade_rows += [(f"Week {n} Assignment: (title)", 10), (f"Week {n} Discussion: (title)", 5)]
    table = doc.add_table(rows=len(grade_rows) + 2, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = V.GRADE_PLAN_HEADER
    for index, (name, points) in enumerate(grade_rows, start=1):
        table.rows[index].cells[0].text, table.rows[index].cells[1].text = name, str(points)
    table.rows[-1].cells[0].text, table.rows[-1].cells[1].text = V.GRADE_PLAN_TOTAL, str(sum(p for _n, p in grade_rows))

    doc.add_paragraph(V.H_COURSE_INTRO, style="Heading 1")
    doc.add_paragraph("Page: Welcome")
    doc.add_paragraph(f"Page heading: Welcome to {course_number}")
    doc.add_paragraph("Placement: Getting Started")
    doc.add_paragraph("(Welcome text. Add more pages with their own Page: and Page heading: lines.)")

    doc.add_paragraph(V.H_BEFORE_WEEK_1, style="Heading 1")
    doc.add_paragraph("One row per module. The first line of a row names the module; the rest are its pages and links.")
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
            rows.append([line.format(n=n, topic=topic) for line in ROW_PROMPTS[key]])
        _one_column(doc, rows, {i for i in range(0, len(rows), 2)})

    doc.add_paragraph(V.H_COURSE_ACTIVITIES, style="Heading 1")
    doc.add_paragraph("(Activities that belong to no week, such as a course questions forum. Delete if none.)")
    doc.add_paragraph(V.H_RUBRICS, style="Heading 1")
    doc.add_paragraph("One rubric per Heading 2: its name, then one 'Used by:' line per activity, then its table. "
                      "Level headers carry a percentage; criterion labels carry a weight in percent; weights add to 100.")
    for name, kind in (("Standard Assignment Rubric", "Assignment"), ("Standard Discussion Rubric", "Discussion")):
        doc.add_paragraph(name, style="Heading 2")
        for n in range(1, weeks + 1):
            doc.add_paragraph(f"Used by: {kind}: Week {n} {kind}: (title)")
        grid = doc.add_table(rows=3, cols=4)
        grid.style = "Table Grid"
        for cell, text in zip(grid.rows[0].cells, ("Criterion", "Exemplary — 100%", "Proficient — 80%", "Developing — 50%")):
            cell.text = text
        for cell, text in zip(grid.rows[1].cells, ("(first criterion) (50%)", "(descriptor)", "(descriptor)", "(descriptor)")):
            cell.text = text
        for cell, text in zip(grid.rows[2].cells, ("(second criterion) (50%)", "(descriptor)", "(descriptor)", "(descriptor)")):
            cell.text = text
    doc.add_paragraph(V.H_NOTES, style="Heading 1")
    doc.add_paragraph("(Notes to the builder that are not course content.)")
    doc.save(str(path))
    return path
