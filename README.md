# Blueprint Packager

<p align="center">
  <img src="docs/assets/blueprint-packager.svg"
       alt="Colour pixel-art wizard waving a wand as a wrapped course package slides into a monitor showing a course page"
       width="520">
</p>

Blueprint Packager turns a course blueprint, a Word document written in a
small, fixed layout, into a Brightspace (D2L) import package: modules, pages,
assignment folders, discussions, checklists, quizzes, rubrics, grade items,
due dates, and the links between them. It works in inspectable stages, writes
a receipt at every one, and reads its own package back to prove the course
came through whole before anyone imports it.

It is the forward half of a round trip. The reverse half is **Blueprint
Wizard**, which reads a Brightspace export back into the same blueprint
layout. Together they let a course move between a Word document and a
Brightspace course without hand assembly in either direction.

**Status:** version 0.1.1, October 2026. One whole course (eight weeks, 16
graded activities, 10 rubrics) has been built with it, imported into a
Brightspace sandbox, re-exported, and read back with every structural check
passing. See [Evidence and provenance](#evidence-and-provenance).

---

## Contents

1. [Who this is for](#who-this-is-for)
2. [The idea in one picture](#the-idea-in-one-picture)
3. [What you need](#what-you-need)
4. [Quick start](#quick-start)
5. [How it works](#how-it-works)
6. [What a build produces](#what-a-build-produces)
7. [Importing, and updating a course later](#importing-and-updating-a-course-later)
8. [Writing a blueprint](#writing-a-blueprint)
9. [Page styling](#page-styling)
10. [Evidence and provenance](#evidence-and-provenance)
11. [Repository map](#repository-map)
12. [Questions and changes](#questions-and-changes)

---

## Who this is for

- **Instructional designers and course builders** who write or receive a
  course blueprint and want a Brightspace course from it without rebuilding
  it by hand, page by page and folder by folder.
- **Subject-matter experts** who only ever touch the Word document. The
  blueprint is the whole interface; nothing here needs to be run by them.
- **Anyone checking a build** before import. Every run leaves a readable
  report of what it did and what it found.

You do not need access to any other repository to use this one. Everything
the packager runs on is included and pinned (see
[Evidence and provenance](#evidence-and-provenance)).

## The idea in one picture

```
   Word blueprint  ──►  Blueprint Packager  ──►  Brightspace package (.zip)  ──►  import
   (SME + designer)      normalize · read ·        + receipts, object map,
                         build · verify            page-refresh zip, runbook

   Brightspace export  ──►  Blueprint Wizard  ──►  Word blueprint      (the reverse half)
```

The two tools read and write one layout, so a course can go round: write it,
build it, teach it, export it, read it back as a document, revise, build
again.

## What you need

- **Python 3.11 or later** and the packages in `requirements.txt`.
- **A blueprint** in the packager's layout. Start one with `bpk.py blank`
  (below), or read a Brightspace export into one with Blueprint Wizard, or
  convert an existing document with a course map (see
  [How it works](#how-it-works)).
- **A Brightspace course to import into**, ideally an empty sandbox for the
  first round. Importing needs the course's Import/Export/Copy Components
  permission; nothing here talks to Brightspace directly.

## Quick start

```bash
# once
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

# 1. a blank blueprint to fill in (eight weeks, every row the reader knows)
python3 bpk.py blank MY_COURSE.docx --course-number "NEW 101" --course-title "Course Title" \
        --term "Spring A 2027" --weeks 8

# 2. read the filled-in blueprint into a course model (reports every problem it finds)
python3 bpk.py read MY_COURSE.docx --output-dir out --label my_course

# 3. build the package (settings: template, calendar, grade item names, and so on)
python3 bpk.py build out/my_course__course_model.json --settings build_settings.json \
        --output-dir build --force

# 4. read the package back and compare it with the model: twelve checks
python3 bpk.py verify build --model out/my_course__course_model.json
```

Then import `build/<package>.zip` into Brightspace as a course package. The
build folder's `object_map.md` says what to expect to find, and a course's
own runbook, when it supplies one, says what to check by eye.

Exit codes: 0 success; 1 the step ran and found errors; 2 usage or refusal;
130 interrupted.

## How it works

Each stage reads the previous stage's output and writes its own, so a problem
can be found where it happened.

| Stage | Command | What it does |
|---|---|---|
| Blank | `bpk.py blank` | Writes a blank blueprint with every row and the lines each needs. It reads back with no errors as it stands. |
| Ingest | `bpk.py ingest` | Dumps a Word file as a stream of paragraphs with stable ids, the ids every later record refers to. |
| Normalize | `bpk.py normalize` | For a document not yet in the layout: applies a **course map** of structural decisions (move, restyle, mark a panel, make a list, carry a title into a line) and writes a normalized copy. A fidelity proof shows every authored word is still there. Wording changes happen only as recorded entries that name who authorized them and why. |
| Read | `bpk.py read` | Turns the blueprint into a course model: weeks, pages, activities, rubrics, checklists, and the joins between them, with diagnostics for anything that does not line up (a rubric no activity names, points that disagree with the points table, a heading level that jumps, a link that says "click here"). |
| Build | `bpk.py build` | Writes the Brightspace package from the model and a settings file: page HTML from a template, activity descriptions, dates from a term calendar and due-day rules, checklists built from each week's activities, grade items, rubrics. Deterministic: the same inputs give a byte-identical ZIP. |
| Verify | `bpk.py verify` | Reads the package back with independent readers and compares it with the model: structure, joins, points, rubrics cell by cell, every authored paragraph, checklists, dates, and an accessibility gate on every page. |
| Re-sync | `bpk.py rebase-map` | When the source document changes, carries a course map from the old export to the new one and reports what moved, was added, or was removed. |

A blueprint written in the layout from the start skips Normalize.

## What a build produces

| File | What it is for |
|---|---|
| `<package>.zip` | The Brightspace course package. Import this. |
| `package/` | The same package unzipped, for inspection. |
| `course_pages_refresh.zip` | Just the HTML pages. Uploading its folder through Manage Files refreshes page content in a course that is already built, with no new objects (see the next section). |
| `object_map.json`, `object_map.md` | Every object the build made, its resource code, its placement, its dates, which paragraphs went where, and every build note. |
| `component_package_receipt.json` | The receipt: what was read (with hashes), what was written, which engine files were used, which engine commit they came from. |
| `verification_report.md`, `.json` | The twelve read-back checks and their evidence. |
| `build_settings.json` | A copy of the settings the build used. |

Every page's HTML opens with a one-line comment naming the tool version, the
package, the blueprint file and its hash, and the template, so a page found
in a course can be traced to the build that made it.

## Importing, and updating a course later

These are facts from the sandbox rounds, not assumptions.

- **First import into an empty course:** everything arrives, and a re-export
  reads back identical to the build.
- **Importing the same package again into a course that already holds it
  duplicates every object** except the HTML pages: modules, folders, forums,
  checklists, quizzes, rubrics, and grade items all double, and the new
  activities are left without grade items. Brightspace does not match
  objects by the package's identities. So a built course is updated by
  deleting the built content first and importing again.
- **Page text alone can be refreshed in place.** Pages are course files and
  Brightspace overwrites a file at the same path. Upload the folder inside
  `course_pages_refresh.zip` through Manage Files; every page updates, and
  nothing else changes.
- **A reused course mints fresh resource codes** even after the old objects
  are deleted. Nothing in the tool depends on the codes coming back; they are
  for the records.

The receipts behind these statements are in `docs/IMPORT_RECEIPTS.md`.

## Writing a blueprint

The full rules are in [`docs/AUTHORING_GUIDE.md`](docs/AUTHORING_GUIDE.md).
The ones that matter most:

- **Headings are one to one with the page.** The blueprint's frame (Course
  Introduction, Before Week 1, each week, Rubric Appendix) is Heading 1. The
  page title is its own line. Content inside a page starts at Heading 2 and
  keeps its level on the page: Heading 2 is h2, Heading 3 is h3.
- **Panels are bracket lines.** `[dropdown: Title]` … `[/dropdown]`,
  `[callout]` … `[/callout]`, `[callout tone=gold]` for something to keep in
  mind, `[timeline]`, `[box]`. Nothing depends on shading, which does not
  survive editing.
- **Links to the course's own objects** are `[link to assignment: Title |
  words]`, `[link to page: Title]`, and so on. The build turns them into
  working links; an unknown target is left visible as an error.
- **Every week has the same six rows:** Overview, Learning Objectives,
  Assigned Reading and Multimedia, Assignments, Discussions, Checklist. A
  checklist can list its items or carry one line, `Items: From this week's
  activities`, and the build makes the list.
- **Dates are never typed.** The blueprint says "due Sunday"; the build
  settings carry the term's week table and the program's due-day rules.
- **Activities say what they are** on one line (`Assignment: Week 2
  Deliverable: …`, `Points: 10 pts`, `Rubric: …`), and the points table at
  the front of the document must agree. The build stops on a disagreement
  until someone records which is right.

Real bullets, real numbering, bold and italic all come through as typed.

## Page styling

Pages take their look from a template chosen in the build settings. The
default, `composite-navy`, is a composite of three earlier course designs:
a dark navy brand, calm spacing, arrow-marked dropdown cards, a restrained
callout with a warm tone available, and an accessibility pass (skip link,
visible keyboard focus, print rules). `bumk515-classic` reproduces an earlier
course's page style. Assignment and discussion descriptions take a modest
style set derived from the same template, or none, by setting
`fragment_styles` to `plain`. Details: [`docs/TEMPLATE_COMPOSITE_NAVY.md`](docs/TEMPLATE_COMPOSITE_NAVY.md).

## Evidence and provenance

**Evidence levels.** Every shape the tool can build is listed in
`CAPABILITIES.json` with how well it is proven, on a ladder from L1 (the tool
reads its own output back) to L4 (a package was imported into Brightspace,
re-exported, and read back). The whole-course package is at L4 as of
2026-10-08; `docs/IMPORT_RECEIPTS.md` holds the receipts, each with the
package hash, the sandbox, the counts, and what Brightspace changed.

**What every run records.** The receipt names the producer and version, the
input file and its hash, every engine file used and its hash, the settings,
and the outputs. The object map ties every built object to the blueprint
paragraphs that fed it. Verification reports name the readers that were used.
Nothing is edited by hand after a build; a change means a rebuild.

**The engine, pinned.** The packager writes packages with, and verifies
against, scripts and schemas from the team's internal engineering repository,
the CourseCraft Workbench. You do not need access to it: the files the
packager needs are copied under `vendor/coursecraft_workbench/` at one named
commit, and `vendor/coursecraft_workbench/MANIFEST.json` records that commit
and every file's hash. Those copies are never edited here. When the Workbench
changes, `scripts/check_vendor_drift.py` reports the difference and can
re-pin; the pinned commit is written into every receipt and verification
report, so a build can always be tied to the exact engine that made it.

**Wording.** The tool never changes authored text on its own. A course map
may carry authorized edits, each with who authorized it and why, and the
fidelity proof and the build records list every one apart from the authored
text.

**Records.** `docs/records/` holds the survey reports and work records the
tool was designed from, including the notes on how Brightspace behaves on
import. They are kept so decisions can be checked later, not for reading
first.

## Repository map

| Path | What |
|---|---|
| `bpk.py` | The command line. `python3 bpk.py --help` lists the stages. |
| `blueprint_packager/` | One module per stage: `docx_ingest`, `normalize`, `fidelity`, `reader`, `joins`, `calendar`, `html_render`, `build`, `verify`, `rebase`, `blank`; `vocabulary` holds the blueprint layout's words; `workbench` decides where the engine files come from. |
| `blueprint_packager/templates/` | Page templates: `composite_navy` (default), `bumk515_classic`. |
| `vendor/coursecraft_workbench/` | The pinned engine files and schemas, with their manifest. |
| `scripts/check_vendor_drift.py` | Compares the vendored files with a Workbench checkout; re-pins on request. |
| `scripts/render_readme_art.py` | Draws the picture at the top of this page from a text grid. |
| `docs/AUTHORING_GUIDE.md` | How to write a blueprint. Start here if you will edit one. |
| `docs/DESIGN.md` | Why the tool is shaped as it is, and the open directions. |
| `docs/IMPORT_RECEIPTS.md` | The sandbox receipts behind the evidence level. |
| `docs/TEMPLATE_COMPOSITE_NAVY.md` | The default template and where each part came from. |
| `docs/PROMOTION_MANIFEST.md` | Which parts belong to the shared engine and where that stands. |
| `docs/examples/` | A generated eight-week blank blueprint. |
| `docs/records/` | Survey reports and work records. |
| `tests/` | Synthetic fixtures end to end; `pytest -q`. |
| `CAPABILITIES.json`, `CHANGELOG.md`, `ROADMAP.md`, `AGENTS.md` | What it builds and how well, what changed, what is next, what it must never do. |

## Questions and changes

- Something in a build looks wrong: open the build's `verification_report.md`
  and `object_map.md` first; they say what was read and what was checked.
- A blueprint will not read: the diagnostics name the paragraph and say what
  to change. The authoring guide's last section lists what the tool will not
  guess.
- A change to borrowed engine behaviour belongs upstream first, then a re-pin
  here; `AGENTS.md` says what this repository owns.
- Dependencies: `python-docx`, `lxml`, `openpyxl`, `jsonschema`.
