# Writing or editing a blueprint the packager can read

Date: 2026-10-06. For anyone who edits a blueprint that came out of Blueprint
Wizard, or writes one from blank. The packager reads Word structure first and
marker lines second, so the rule throughout is: use what Word already has a
form for, and type a marker only where Word has none.

Items marked *provisional* were added on 2026-10-06 from the owner's notes and
may change after review.

## 1. Headings

Use Word's heading styles. The blueprint spends its top two levels on its own
frame, so inside a page or an activity start at Heading 3.

| In the blueprint | In the course page |
|---|---|
| The `Page heading:` line | the page title, h1 |
| Heading 3 | h2 |
| Heading 4 | h3 |
| Heading 5 and 6 | h4 |

Levels keep their order and nesting; the number shifts by one because the
blueprint's own frame uses Heading 1 and 2. Do not fake a heading with a bold
line and a colon.

## 2. Lists, tables, emphasis

- Type real bullets and real numbering with Word's list styles. A numbered
  list stays numbered in the course.
- Build a real Word table for tabular content.
- Bold, italic, and underline come through as typed.
- A line break inside a paragraph stays a line break.

If a blueprint came out of the wizard with list items as plain lines, retype
them as bullets. The packager does not guess that discrete lines were a list.

## 3. Dropdowns, callouts, timelines

Two forms are accepted. The wizard writes the first; the second is shorter to
type. Every opener needs its closer.

| Block | Long form | Short form (*provisional*) |
|---|---|---|
| Dropdown | `Dropdown / expandable section: Title` … `End of dropdown / expandable section` | `[dropdown: Title]` … `[/dropdown]` |
| Callout | `Visual cue: Callout` … `End of visual cue` | `[callout]` … `[/callout]` |
| Timeline | `Visual cue: Timeline` … `End of visual cue` | `[timeline]` … `[/timeline]` |

Each marker sits on its own line. A callout's title is its first heading inside.

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

A rubric is a Heading 3 with its name, one `Used by:` line per activity that
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
