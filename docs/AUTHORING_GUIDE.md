# Writing or editing a blueprint the packager can read

Date: 2026-10-06. For anyone who edits a blueprint that came out of Blueprint
Wizard, or writes one from blank. The packager reads Word structure first and
marker lines second, so the rule throughout is: use what Word already has a
form for, and type a marker only where Word has none.

Items marked *provisional* were added on 2026-10-06 from the owner's notes and
may change after review.

## 0. Starting from nothing

`python3 bpk.py blank out.docx --course-number "NEW 101" --course-title "Title" --term "Spring A 2027" --weeks 8 --topic "Foundations" …`
writes a blank blueprint in this convention: front matter, points table, a
welcome page, one module row before Week 1, every week with its six rows and
the lines each needs, two standard rubrics, and notes. It reads back with no
errors as it stands, so a build works as soon as there is content. Every
week's Checklist row is pre-filled with `Items: From this week's activities`;
replace that line with typed items when you want a hand-written checklist.
A generated example is `docs/examples/blank_blueprint__8_weeks.docx`. The blank opens with a short guide and a key, and Week 1's overview carries a worked dropdown, callout, and internal link to copy from; grey italic text is a prompt to replace, upright text is structure to keep.

## 1. Headings

Use Word's heading styles. Your outline is the page's outline: Heading N in the
blueprint is hN on the page, with one exception that is the same on every
page. The page title is the page's h1, so content starts at Heading 2.

| In the blueprint | In the course page |
|---|---|
| Title style | the course title (the document's title; not on any page) |
| Heading 1 | the frame: Course Introduction, Before Week 1, each Week N, Rubric Appendix. Not content |
| The `Page heading:` line | the page title, h1 |
| Heading 2 | h2 |
| Heading 3 | h3 |
| Heading 4, 5, 6 | h4, h5, h6 |

Inside an activity the same holds: the activity's title is the object's own
title in Brightspace, and its sections start at Heading 2 in the blueprint
(the title line itself is a Heading 2; sections under it Heading 3 and down).

Two small things about headings. A soft line break inside a heading (Shift+Enter
in Word or Google Docs) keeps the words in the heading; on the page the second
line becomes a subtitle under the first. And a heading that is bold from end to
end loses that bold, because the page's own heading weight takes over.

A blueprint written before 2026-10-07 has its frame at Heading 2 and content
from Heading 3. The packager still reads it: every level is read one up and
the companion says so, so pages come out the same. Running such a file through
the normalizer writes it in the new convention.

Do not fake a heading with a bold
line and a colon.

## 2. Lists, tables, emphasis

- Type real bullets and real numbering with Word's list styles. A numbered
  list stays numbered in the course.
- Build a real Word table for tabular content.
- Bold, italic, and underline come through as typed.
- A line break inside a paragraph stays a line break.

If a blueprint came out of the wizard with list items as plain lines, retype
them as bullets. The packager does not guess that discrete lines were a list.
Where the document cannot be edited, the course map can make named paragraphs
list items like another paragraph (`bullet`); the words stay as typed.

How the result looks. Assignment and discussion descriptions are written as
plain semantic HTML with no styling of their own, so they look like every
other description in the tenant. Pages take their look from the selected
template; the heading levels, lists, tables, and emphasis are the same in both.

## 3. Dropdowns, callouts, timelines

Two forms are accepted. The wizard writes the first; the second is shorter to
type. Every opener needs its closer.

| Block | Long form | Short form (*provisional*) |
|---|---|---|
| Dropdown | `Dropdown / expandable section: Title` … `End of dropdown / expandable section` | `[dropdown: Title]` … `[/dropdown]` |
| Callout | `Visual cue: Callout` … `End of visual cue` | `[callout]` … `[/callout]` |
| Timeline | `Visual cue: Timeline` … `End of visual cue` | `[timeline]` … `[/timeline]` |

Each marker sits on its own line. A callout's title is its first heading inside.

A callout can take a tone from the template's palette, or a colour of its own,
as attributes on the opener: `[callout tone=gold]` for "keep this in mind"
snippets and information that needs highlighting, `[callout tone=grey]` for an
aside, or `[callout color=#336699]` for one-off colour. With no attribute the
callout uses the template's default tone. An unknown tone is reported and the
default is used. The palette is listed in the template's manifest under
`callout_tones`; today it is default, gold, and grey (owner's choice,
2026-10-08: minimal optionality until there is a design surface).

## 4. Links to other parts of the course (*provisional*)

Web addresses are ordinary hyperlinks. For a link to something inside the
course, type a bracket where the link should appear:

| Type | Shows | Opens |
|---|---|---|
| `[link to page: Comprehensive Marketing Plan: Assignment Roadmap]` | the page title | that page |
| `[link to assignment: Week 7 Comprehensive Marketing Plan \| the plan]` | the words after the bar | the assignment folder |
| `[link to discussion: …]`, `[link to quiz: …]`, `[link to checklist: …]` | as above | that object |

Titles must match exactly. An unknown title is left visible in the page in
full-width brackets, and the build reports an error, so nothing is guessed. A
page link inside an assignment or discussion description is not supported yet,
because the page's topic code does not exist until the package is built; link to
pages from course pages.

## 5. Activities

An activity opens with a typed header and continues with its own text:

```
Assignment: Week 2 Deliverable: SailGP STP Strategy & Positioning Analysis
Points: 10 pts
Gradebook item: Week 2 Assignment: SailGP STP Strategy & Positioning Analysis
Rubric: SailGP STP Strategy & Positioning Analysis Rubric
```

- The activity's title is its own heading. The build puts "Week N" in front when
  the heading does not start with it.
- Points on the activity are the authority. The `Gradebook item:` line names the
  row of the points table it joins. When the two disagree the build stops and
  asks; it never picks one.
- A discussion also names its `Forum:`.
- Due days belong in the prose as weekdays ("due Friday by 11:59 p.m."). Dates
  come from the build's term calendar, never from the blueprint.

A note on the activity's title. Write it once, on the `Assignment:` or
`Discussion:` line, or as the activity's own heading that the course map
copies into that line. The build does not repeat it inside the description;
Brightspace shows the title above the field, and the wizard writes it back as
the activity line, so the two directions agree.

## 6. Checklists

```
Checklist: Week 3 Checklist
Items: From this week's activities
```

The build makes the items from the week's discussions and assignments in the
course's own wording. Anything typed under the checklist is an extra item.
Leave the `Items:` line out to list every item yourself.

## 7. Before Week 1 (*provisional*)

Each row of the table before Week 1 is one module. Whatever sits under its
`Module:` line belongs to that module, in order: pages, links, a quiz, a
discussion. A `Placement:` line adds a second module for the same object; it is
not needed for the module the object sits in.

```
Module: Welcome, Syllabus, and Getting Started
Page: Comprehensive Marketing Plan: Assignment Roadmap
Placement: Week 1 - Foundations of Marketing
Page: Student and Course Resources
Quiz: Academic Integrity Agreement
```

## 8. Rubrics

A rubric is a Heading 2 with its name, one `Used by:` line per activity that
uses it, and its table. Joins are checked from both sides by exact title.

## 9. What the packager will not do

- Guess a join, a list, a date, or a missing title.
- Change wording. Edits happen only as recorded entries in the course map, with
  an authorizer and a reason.
- Read shading or colour as structure. A box or a marker says where a block
  ends; shading does not survive editing.

## 10. Towards one visual language

Wizard output and hand authoring should look the same, in stages:

1. Now: the packager accepts both the long and the short forms above, and the
   first wizard fixes make its output more native (real lists, headings, line
   breaks).
2. Next: the wizard marks where dropdowns and callouts end, writes a module
   area before Week 1, and names each discussion's forum, using the same forms
   the packager reads.
3. Then: a model revision lets the wizard keep bold, italic, and tables.
4. Later: a blank blueprint template with a course-settings section, and this
   guide folded into it.
