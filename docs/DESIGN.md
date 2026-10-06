# Blueprint Packager design

Status: working design, written 2026-10-06 beside the first implementation.
Scope: one course so far (MBA 620). Written so the reusable parts can be
reviewed for promotion into CourseCraft later.

## 1. The problem

Blueprint Wizard turns a Brightspace export into a flat blueprint that SMEs can
edit. Nothing turned an edited blueprint back into a course. Every course build
that needed it wrote its own packager with the course's shape hard-coded.

Three things block a general tool:

- **A flat blueprint loses structure.** Module names, object types, panel
  endings, links on headings, and resource codes are not in it.
- **Editing breaks what structure remains.** Objects get typed into the wrong
  row, headings get split, body text gets heading styles, wizard lines go stale.
- **Joins live in people's heads.** Which rubric goes with which assignment is
  a note in a margin, not a field.

This tool handles each with a separate, inspectable step.

## 2. Pipeline

```text
blueprint DOCX ──A──▶ paragraph stream
                         │
       course map ───────┤
                         B
                         ▼
               normalized DOCX ──C──▶ course model ──D──▶ package
                         │                 ▲                 │
                  ledger + proof     build settings     three readers
```

| Stage | Module | Contract it emits |
|---|---|---|
| A. Ingest | `docx_ingest.py` | `blueprint_packager.docx_stream/1` |
| B. Normalize | `normalize.py`, `fidelity.py` | `…paragraph_ledger/0.1`, `…fidelity/1` |
| C. Read | `reader.py`, `joins.py` | `blueprint_packager.course_model/0.1` |
| D. Build | `html_render.py`, `build.py` | `coursecraft.component_package_receipt/1`, `…object_map/0.1` |
| Verify | `verify.py` | `blueprint_packager.verification/0.1` |

The normalized Word file is the only thing stage C reads. The normalizer does
not hand the reader a model behind the scenes. Whatever the packager builds, it
read from the document a person can open.

## 3. The canonical blueprint

A canonical blueprint is the wizard's layout with three additions. Structure is
carried by text, not by custom Word styles, because blueprints travel through
Google Docs and custom styles do not survive the trip.

### 3.1 Fixed frame

Heading 2 sections, in order: `Course Introduction`, `Before Week 1: Additional
Resources and Information`, one `Week N - Title` per week, `Unplaced
Activities`, `Rubric Appendix`, optionally `Retired Rubrics (not built)`, and
`Extraction Notes`. Front matter is four tables: course description, materials,
outcomes, and the `Assignment | Points` table.

Each week is a one-column table of six label and body row pairs, always in this
order: Overview, Learning Objectives, Assigned Reading and Multimedia,
Assignment(s) and Instructions, Discussion Board Prompts, Checklist. Labels are
matched by their opening words, so the wizard's long label text still works.

### 3.2 Directive lines

A directive is a whole paragraph that starts with a reserved keyword and a colon.

| Kind | Keywords |
|---|---|
| Object openers | `Module`, `Page`, `Link`, `Assignment`, `Discussion`, `Quiz`, `Checklist` |
| Object attributes | `Page heading`, `Placement`, `Visibility`, `URL`, `Points`, `Gradebook item`, `Rubric`, `Forum`, `Source`, `Attempts allowed`, `Time limit`, `Sections`, `Question types` |
| Block markers | `Dropdown / expandable section`, `Visual cue`, `Video embed`, `Embedded image` |
| Block ends | `End of dropdown / expandable section`, `End of visual cue` |
| Rubric side of a join | `Used by` |

`Points`, `Gradebook item`, `Rubric`, the dropdown opener, `Visual cue`, and
`Video embed` are the wizard's own spellings. The rest are new.

An activity therefore reads like this in the document:

```text
Assignment: Week 2 Assignment: SailGP STP Strategy & Positioning Analysis
Points: 10 pts
Gradebook item: Week 2 Assignment: SailGP STP Strategy & Positioning Analysis
Rubric: SailGP STP Strategy & Positioning Analysis Rubric
…authored instructions, untouched…
```

### 3.3 Three rules that keep it unambiguous

1. **Openers are scoped by section.** `Checklist:` opens an object only in the
   Checklist row. In an overview page the same words are authored content. This
   rule exists because MBA 620 has an inherited sentence that begins "Checklist:".
2. **Attributes count only in the header.** Once authored content starts, a line
   beginning "Points:" is content.
3. **Openers never start inside an open dropdown or visual cue.**

### 3.4 Joins are written on both sides

An activity names its rubric. The rubric names its activities with `Used by`.
An activity names its gradebook item, and that name must be a row of the points
table. The reader checks both directions and never matches loosely. A
one-letter difference is an error, by design.

### 3.5 What an activity is called and what it is worth

Owner determination, 2026-10-06. Both rules put the activity itself first and
treat the points table as the plan it joins to.

- **Title.** The opener carries the activity's title. The title is the
  activity's own heading, copied, with the heading left in the instructions.
  The `Gradebook item:` line still quotes the points table row, and that row is
  the join. Where the two differ the reader says so as a note.
- **Points.** The activity's `Points:` line is the authority. When a body
  states no points, the normalizer fills the line from the points table. When
  a body and the table disagree, the map must say which to use, and the choice
  is recorded with its reason. The reader reports any remaining disagreement
  as a warning and the build follows the activity.
- **Gradebook name.** The grade item is named after the activity it grades.
  `grade_item_names: "points_table"` in the build settings names it by its row
  instead.
- **Week.** A title inherits its week. When an activity's heading does not
  already begin with "Week N", the opener puts it in front. The heading inside
  the instructions is left as written.
- **Disagreement stops the tool.** When an activity's points and its points
  table row differ, the tool names both and stops until a person records which
  to use. It does this at normalization, where the choice goes in the course
  map, and again at build, where it goes in the build settings. It never
  picks one.

### 3.4a Heading levels: the convention and its alternative

Where the numbers come from. The Word blueprint uses the Title style for the
document's title and Heading 2 for its frame: Course Introduction, Before
Week 1, each week, Rubrics. Heading 1 is unused. Content inside a page or an
activity therefore begins at Heading 3. On the course page the page heading is
the one h1, so the first content level must be h2. Hence Heading 3 becomes h2,
Heading 4 becomes h3, and Heading 5 and 6 become h4. Order and nesting are
kept; the number shifts by one. The wizard candidate writes the reverse: a
page's h2 becomes Heading 3.

What is fixed and what is not. The frame level is a rule of the blueprint
grammar and applies to every blueprint the tool reads. The page-side numbers
sit in each template's manifest, so a template could map differently, but any
template must give one h1 and sequential levels, so the first content level
will be h2 in practice. The convention is universal in effect.

The alternative, not chosen. Make the frame Heading 1 and start content at
Heading 2, so Word levels equal page levels one to one. Easier for someone
writing from blank, and closer to a Google Doc's default outline. The cost is
a change to the wizard's frame and a one-level restyle of every existing
blueprint, which the normalizer can do by rule. The owner asked for this
detail on 2026-10-06 and has not yet decided.

### 3.5a Short forms for hand authoring (provisional)

Everything in 3.1 to 3.4 is what Blueprint Wizard writes. For a person typing
a blueprint, the reader also accepts bracket forms that mean the same thing:
`[dropdown: Title]` … `[/dropdown]`, `[callout]` … `[/callout]`,
`[timeline]` … `[/timeline]`, and inline `[link to page: Title]` or
`[link to assignment: Title | words to show]` for a link to another object of
the course. Targets are matched by exact title; an unknown one stays visible
and fails the build. Both forms are read everywhere, so wizard output and hand
authoring can converge without a change on one side breaking the other. The
long and short forms are listed side by side in `AUTHORING_GUIDE.md`.

### 3.5b The area before Week 1

Each row of the table before Week 1 is one module. Whatever sits under its
`Module:` line belongs to it: pages, links, and activities, in order. A
`Placement:` line adds a second module for the same object. The wizard's flat
layout, one page per row with a `Placement:` line, is still read; the module
row is what a formal before-Week-1 area looks like, as the owner asked for.

### 3.6 Checklists

A checklist can list its items, or it can carry one line:
`Items: From this week's activities`. The builder then makes the items from
that week's discussions and assignments, so the checklist cannot drift from
the week. Wording comes from patterns in the build settings, with a default
that names the week ("Week 3 Discussion: Initial Post") when the week has one
activity of a kind and the activity's own title when it has several. Items
listed under such a checklist are added after the built ones. Without the line
a checklist is copied as typed, and the reader warns when a typed item names an
activity kind the week does not have.

### 3.7 Dates

The blueprint speaks in weeks and weekdays. A calendar in the build settings
supplies each week's dates, a time zone, and a rule per role: assignment,
discussion first post, discussion response, quiz. A rule names a weekday or
the week's last day, and may name a different day for the term's last week. An
activity can override its rule. Offsets come from the time zone database, so a
term that crosses a daylight-saving change is right on both sides.

Where dates go follows what Brightspace accepted from an earlier build:
assignment folders carry a due date; discussion deadlines ride on dated
checklist items, because topics hold no dates; assignment checklist items stay
undated so the calendar shows each deadline once. The builder also compares its
dates with any due day the activity's own text names and warns when they
differ.

Open: the blueprint has no line for a due rule, so today the rules live only in
the build settings. A course-settings section in a blank blueprint would be the
natural home, alongside tool settings such as post-before-reading and
conditional release.

Direction from the owner, 2026-10-06. For MBA 620 the dates are custom to the
term supplied. More generally the process should encode: choose the term (Fall
A, Fall B, and so on) and the program, since each program's week pattern
differs, and derive the week table from the course start and end dates. That
is a term-calendar registry keyed by term and program, with the program's
due-day conventions beside it, so a build names a term instead of typing
dates. The other practice in the ecosystem, building with one term's dates and
bulk-managing them in Brightspace before each later term, stays available.

### Changing a course after it is built

Not solved, and worth stating. A rebuild gives a new package; what it does to
a course that already exists is the open question. Three routes:

1. **Replace.** Delete the built content and import again. Fine for a template
   shell before a term starts; it loses any change made in the tenant.
2. **Re-import with the same identities.** The packager mints the same resource
   code for the same object on every build. Whether Brightspace treats a
   re-import with matching codes as an update or as a duplicate is untested
   here. The sandbox runbook now includes that experiment.
3. **Bring tenant edits back first.** Blueprint Wizard reads an export into a
   blueprint. Export the live course, re-sync the course map, edit, rebuild.
   This is the round trip the two tools are meant to make.

The owner is comfortable with the first route for MBA 620 and notes others may
not be, or it may not be appropriate.

## 4. Normalization

A course map is a JSON file of structural decisions for one source file,
identified by SHA-256. For MBA 620 it is written by a short script so each
decision sits beside its reason.

The normalizer can do five things to an authored paragraph:

| Operation | Recorded as |
|---|---|
| Move it to the section it belongs in | `kept` with its new section |
| Change its paragraph style | `kept_restyled`, from and to |
| Remove accidental bold from a block that is bold end to end | `kept_unbolded` |
| Merge a heading that was split across paragraphs | `merged_into_heading` |
| Carry a title line into a directive value | `carried_into_directive` |

It cannot retype or delete authored words. Paragraphs are copied as XML, so
inline formatting, links, and list membership come along unchanged.

A directive value can be written three ways: carried from a title line, which
is then consumed; copied from a paragraph that stays in place; or stated in the
map with its source.

**Authorized wording changes.** The normalizer changes wording only when the
map tells it to, and the map must say who authorized each change and why. There
are three forms. `additions` place named paragraphs. `edits` drop whole
paragraphs or replace one exact stretch of text inside a paragraph; the stretch
must occur exactly once, and the run it starts in keeps its formatting. A
rubric `clone` copies an authored rubric with named cell edits under a new
name. The fidelity proof lists all three apart from authored text and fails on
any other difference. The tool applies such changes; it never proposes or
decides one. In MBA 620 the instructional designer directed each one and an
assistant wrote the entries.

The first of these, described as it was introduced:

**Authorized additions.** One operation adds words, and only on the operator's
say-so. An `additions` entry places named paragraphs after an authored one. It
must say who authorized it and where its words came from, and it can borrow
the paragraph properties of an authored neighbor. The fidelity proof counts
these words apart from authored text and fails if any other new words appear.
The first use was three links and one sentence taken from a comment thread.
The source document does not contain an addition, so each one is a standing
difference between the document and the build until someone closes it.

Wizard-generated lines are structure. They are kept (`structure_kept`), or
replaced by a regenerated directive and logged with their original text
(`structure_superseded`).

A run stops if any source paragraph is left unaccounted for, or if the map was
written for a different file.

### When the source changes

A map names paragraphs by position, and a live document keeps moving. The
`rebase-map` command lines two exports up paragraph by paragraph and translates
every id the map uses: single paragraphs, ranges, cells, tables, and ids quoted
inside notes. It reports what was edited in place, added, removed, and which
suggestions were resolved.

Three rules keep it honest:

1. A range survives while any paragraph inside it survives; its ends move inward.
2. A removed paragraph is dropped from a list of things to act on, with a note.
   If a single required value points at it, the command stops.
3. An added paragraph inside a mapped range comes along. One outside every
   range is reported and left for the normalizer to refuse, so a person places it.

The decisions stay written against the export they were made on. A later
export is reached by translation, with a report each time.

### Fidelity proof

After writing, the tool reads the normalized file back from disk and checks:
every source paragraph has one disposition; every kept paragraph is
text-identical; kept paragraphs keep their bold, italic, underline, and links;
the word multiset is equal; no pending suggestion remains; every carried title
appears verbatim; the only words not in the source are the authorized
additions; and authored wording differs only where the map carries an
authorized edit.

### Evidence, not guesses

Where the blueprint lost structure, the map takes it from evidence and says so:

- **Dropdown endings** come from the `<details>` blocks of the source export.
- **Module names and placements** come from the source export's manifest.
- **Links lost on headings** come from the source export's pages.
- **Object types** come from the object's own text and the points table.

## 5. The course model

The model is an authoring contract. It is deliberately separate from
`coursecraft.blueprint/4`, which is an extraction and review model with a closed
schema. A suitable upstream name would be `coursecraft.blueprint_authoring/1`.

Top level: `title_lines`, `front_matter`, `grade_plan`, `modules`, `pages`,
`links`, `weeks`, `course_activities`, `rubrics`, `retired_rubrics`, `joins`,
`diagnostics`.

Blocks keep what the wizard's block model drops: bold, italic, and underline on
runs; dropdowns and visual cues as containers with their content inside; tables.

| Record | Shape | Borrowed from |
|---|---|---|
| Join | `kind, from, to, status, detail, relationship_key, identity.quality` | Workbench relationship records |
| Diagnostic | `id, code, severity, message, location, remediation, extensions` | Rubric Weave diagnostics |
| Object identity | `entity_key` (`cc:entity:…`), `identity.quality: fallback`, `basis: title` | `course_artifact_contracts.py` |
| Run receipt | `coursecraft.run/1` field names | same |

Authored objects are identified by title until a resource code is minted for
them at build time. The object map then carries both, so a later re-export can
be joined by code.

Severity vocabulary: `info`, `warning`, `error`.

## 6. Pages and templates

Brightspace treats two surfaces differently, so the renderer does too.

| Surface | Used for | Styling |
|---|---|---|
| Page | packaged HTML topics | one `<style>` block per page |
| Fragment | assignment instructions, discussion descriptions | inline styles on every element |

A template is a folder with a manifest: page CSS, section headings the template
supplies, a heading map, the inline style table for fragments, and how each
visual cue renders. Build settings pick a template by id.

`bumk515-classic` is the only template so far. Its page CSS is the old course's
own `<style>` element, verbatim, plus the timeline rules from the old roadmap
page. Its fragment styles are the inline styles the old course used most.

A week's overview page is assembled from three blueprint sections: Overview,
Learning Objectives, and Assigned Reading and Multimedia.

### Open direction: template selection

The intent is that a user picks from several templates. Two facts shape that.

- **The Workbench already has an experimental page compiler**, Page Kit. Its
  block vocabulary lines up with this model almost one for one:

  | This model | Page Kit block |
  |---|---|
  | paragraph, list, heading | `prose` |
  | objectives section | `outcomes` |
  | video | `video` |
  | dropdown | `disclosure` |
  | resources section | `resources` |
  | visual cue: callout | `callout` |
  | table, timeline | `raw_html`, declared |

- **The ecosystem's standing rule is one builder per job.** A second page
  compiler should not outlive this prototype.

So the renderer sits behind a narrow interface: blocks in, HTML out, per
surface. The recommended convergence is an adapter that emits `coursecraft.page/1`
and `coursecraft.module_composition/1` and calls the upstream compiler, with
each selectable template expressed as a kit. The BUMK 515 design would become a
course-local kit. That is where Pagewrights' Guild and the frontend design
bundle would plug in. It was not done now because the brief for MBA 620 was the
original design, and Page Kit's fixed markup cannot reproduce it without a kit.

Borrowed from Page Kit already: its page gate. Verification runs the compiler's
own conformance check on the package's pages in learner mode. It asks for one
h1, alt text on images, titles on iframes, matched dropdown markup, and no
scripts or inline handlers. It reads compiled HTML, so it needed no adapter.

Owner position, 2026-10-06. The built-in renderer is an accepted temporary
exception. Use whatever in Page Kit is useful or more advanced, especially for
later work on style sheets, page configurations, and markup choices. How page
design enters the packager is undecided. Three shapes are on the table:

| Shape | What the user does | What it asks of the tool |
|---|---|---|
| One choice, applied broadly | Picks a template; the packager applies it to every page | A registry of kits and one setting. Closest to what exists. |
| Granular choices | Picks per page type, per week, or per block | Page-level and block-level overrides in the model or the settings |
| A separate building surface | Arranges pages in an interface, with global and narrow choices, inside deterministic limits | A different product surface. Page Kit may be its home. |

The choice is deferred. Settling it needs an effort of its own, on the scale of
the quiz consolidation or of this one. Until then the interface stays narrow so
none of the three is closed off: the model carries no styling, and a template
is chosen by id in the build settings.

## 7. Building the package

Payload XML comes from the Workbench libraries wherever they cover the shape:
grades, assignment folders, discussions, checklists, orgunit config, and
analytic rubrics. The manifest is written locally, modelled on the library's.

Six shapes go beyond the component library. Each copies a shape found in the
target tenant's own export, and each is listed in the build receipt:

1. more than one discussion forum in a package;
2. a rubric attached to a discussion topic;
3. hidden modules and topics;
4. external link topics;
5. one page file placed in two modules;
6. a quiz carried forward unchanged from a source export.

Build settings hold only packaging choices and their sources: package identity,
a fixed base resource code, template, item order inside week modules, forum
order, tool defaults taken from the template shell, carried quizzes, and link
restorations. With a fixed base code, two builds are byte-identical.

The builder refuses a model that has errors.

### Link cleanup

A build setting can drop named query parameters from web addresses as pages are
rendered. The blueprint keeps the original address, and the object map lists
each address before and after. MBA 620 uses it for one tracking tag.

## 8. Verification and evidence

Three independent readers look at the package before anyone imports it:

1. the Workbench conformance gate;
2. the Workbench activity and structure extractors, which trace every join;
3. Blueprint Wizard's own pipeline, run on the package as if it were an export.

What the wizard reads back is compared with the model: module tree, each
activity's grade item, points, and rubric, the gradebook, every rubric cell,
every checklist item, and every authored paragraph.

This is L1 evidence. It shows the package says what the model says, in a shape
the ecosystem's readers understand. It does not show Brightspace accepts it.
`CAPABILITIES.json` lists the best evidence that exists for each shape.

## 9. What is general and what was MBA 620

| Part | General | MBA 620 only |
|---|---|---|
| Ingest, vocabulary, reader, joins, renderer, builder, verifier | yes | |
| Course map engine and fidelity proof | yes | |
| The course map itself | | yes, hand-authored from a listing of the source |
| Dropdown endings from an export | yes, as a helper | needs the source export |
| `bumk515-classic` template | | yes |
| Module layout defaults | partly | item order follows the UNE Online template |

A blueprint fresh from Blueprint Wizard has regular wizard lines, so most of a
course map could be generated. A blueprint written in the canonical layout needs
no map. The hand-authored map is the cost of an SME-edited document, and it is
the part most worth reducing next.

## 10. Wizard behaviors that cost structure

Blueprint Wizard was built to read an export for review, so it keeps wording
and drops much of the shape around it. Sixteen such places were found and
checked against the reader's code and against this course. The full list, with
counts, line references, and a proposed fix for each, is in the MBA 620 review
lane: `workspace/review/mba_620/blueprint_normalization_2026-10-06/wizard_structure_losses/`.

They fall into three groups by where the fix belongs.

| Lost in | Items |
|---|---|
| The reader | list items that wrap a paragraph, links on headings, headings below level 4, line breaks, table cells run together |
| The model, which is a closed schema | bold and italic, numbered lists, tables, link targets, module names and placement before Week 1 |
| The Word writer | heading levels, dropdown and callout endings, non-web links written as grey text, activity settings, the HTML title printed as content |

The Word writer group matters most for the return trip. Those five changes
would let a Word blueprint say enough by itself, which a blueprint written from
blank needs, since it has no export to consult. Today the packager repairs all
sixteen after the fact from the old export. Every one is Workbench-owned
behavior and none was changed.

## 11. Open questions

- Resolved 2026-10-06: the activity title comes from the activity's own heading, and points come from the body before the points table. See section 3.5.
- Should a stale wizard `Points:` line count as the body stating points? MBA 620 has two that say 1 point against 5 and 10 in the table. The map records the choice either way.
- Where should an authorized addition live once it is made: only in the map, or written back to the source document by a person?
- Should a heading ever be a link? The owner's inclination is no. Then a linked heading is a finding to report, not structure to preserve.
- Should label rows keep the wizard's wording ("Checklist (mirrored from the export)") once a blueprint can be authored from blank?
- Answered in part 2026-10-06: dates come from a calendar and due-day rules in the build settings. Still open: whether a due rule also gets a line in the blueprint.
- A blank blueprint template should have a course-settings section: tool defaults, conditional release of modules or items, the term calendar. The packager would set those up from the answers. Owner note of 2026-10-06; not designed yet.
- Authorized edits make the build differ from the source document. Should the tool offer a list in a form a person can paste back, or should the source always be corrected first?
- How should an object that exists only in the shell, such as a syllabus link, be declared?
