# Who does what

Part of [The big picture](BIG_PICTURE.md). The tools that work on a
Brightspace package, what each takes in and gives back, where one hands off
to the next, and what the Packager leaves to the others. The package itself
is in [Anatomy of a Brightspace package](PACKAGE_ANATOMY.md).

## 1. The suite at a glance

```
                                   BRIGHTSPACE
                      export ▼                        ▲ import (always by a person)
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │                               THE ENGINE                                      │
   │  CourseCraft Workbench: readers for every payload, writers for packages,      │
   │  the page gate, the schemas. Private. Shipped into each product at a pinned  │
   │  commit; never edited downstream.                                            │
   └───────┬───────────────────┬───────────────────┬──────────────────┬───────────┘
           │                   │                   │                  │
   ┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼─────────┐
   │ BLUEPRINT      │  │ RUBRIC LOOM    │  │ QUIZ BINDER    │  │ BLUEPRINT      │
   │ WIZARD         │  │                │  │                │  │ PACKAGER       │
   │ export →       │  │ Unravel:       │  │ Unbind:        │  │ blueprint →    │
   │ blueprint      │  │ export →       │  │ export →       │  │ whole-course   │
   │ (JSON, DOCX,   │  │ rubric DOCX,   │  │ workbook,      │  │ package, with  │
   │ MD, QA)        │  │ workbook, JSON │  │ model, Reading │  │ receipts and   │
   │                │  │ Weave:         │  │ Room           │  │ read-back      │
   │                │  │ rubric →       │  │ Compose:       │  │ verification   │
   │                │  │ rubric package │  │ reviewed quiz  │  │                │
   │                │  │                │  │ Rebind:        │  │ from-wizard:   │
   │                │  │                │  │ quiz package   │  │ bundle → DOCX  │
   └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  └──────┬─────────┘
           │                   │                   │                  │
           ▼                   ▼                   ▼                  ▼
   ┌────────────────────────────────────────────────────────┐  ┌────────────────┐
   │ WHERE THEY RUN                                          │  │ CATALOG        │
   │ Blueprint Bundle + Wizard Runner (local terminal)       │  │ a queryable    │
   │ Rubric Bundle + Loom Runner (local terminal)            │  │ database of    │
   │ Quiz Bundle's Quiz Workshop (local terminal)            │  │ course         │
   │ Workshop Hall (hosted: Wizard, Loom, Quiz Binder Unbind)│  │ components,    │
   │ Packager's guided runner (local terminal)               │  │ fed by the     │
   └────────────────────────────────────────────────────────┘  │ Wizard's JSON  │
                                                               └────────────────┘
   PLANNED, not lit:  INTERACTIVES FORGE (Creator+ practice fragments)
                      PAGEWRIGHTS' GUILD (page design: inline-safe elements, templates)
```

Three rules hold across the suite:

- **No tool touches a tenant.** Exports are made by Brightspace; imports are
  made by a person who records the result. A tool's "verified" is local
  evidence unless a receipt says otherwise.
- **Extraction never edits.** An export, and anything extracted from it, is
  evidence. The Wizard's bundle is immutable; the Packager's `from-wizard`
  reads it and writes a new document.
- **Every run leaves a receipt** naming the tool, its version and release
  commit, the inputs and their hashes, and the engine files used.

## 2. Each tool

### Blueprint Wizard

Takes a course export ZIP. Gives a blueprint: `<label>__blueprint.json`
(`coursecraft.blueprint/5`), the same as Markdown and as a review DOCX, the
structure and activities models it was built from, a rubrics file and DOCX, a
QA report, and a run identity. Never changes the export; never imports.

```
   export ZIP ──► readers (manifest, payloads, questiondb + quiz_d2l, pages)
              ──► models: course_structure (coursecraft.structure/1), course_activities, rubrics
              ──► the blueprint (coursecraft.blueprint/5) ──► Markdown · DOCX · QA report · run identity
```

Pages are parsed once into blocks and only then grouped into segments, so a
panel keeps the heading it owns. Panels are written in a bracket vocabulary
(`[dropdown: Title]`, `[callout tone=…]`, `[timeline]`, `[box: Label]`,
`[link to kind: Title | words]`) that the Packager reads back.

Ships as the [Blueprint Bundle](https://github.com/timebeing92/brightspace-blueprint-bundle)
(the engine, released), the
[Wizard Runner](https://github.com/timebeing92/brightspace-blueprint-runner)
(a local terminal around one pinned Bundle) and a bench in the hosted
Workshop Hall (a browser around the same pin).

### Blueprint Packager (this repository)

Takes a blueprint: one Word document in a small fixed layout. Gives a
whole-course import package with its receipts, an object map, a pages-only
refresh ZIP and a verification report. Never imports. `bpk.py from-wizard`
turns a Wizard bundle into an authoring blueprint for an explicit subset of
shapes and refuses the rest with a ledger.

```
   authoring DOCX ──► ingest (paragraph stream) ──► [normalize with a course map]
                  ──► read: course model · source-accounting ledger · readiness · relationships
                  ──► build (+ settings: template, calendar, identifiers):
                        package.zip · course_pages_refresh.zip · object_map · receipt · run identity
                  ──► verify: the engine's independent readers + the Wizard's page QA,
                        compared with the model → verification_report
```

What it builds, carries and refuses is recorded shape by shape in
`CAPABILITIES.json`; the short form is in section 4.

### Rubric Loom

Takes an export (or a bare `rubrics_d2l.xml`). **Unravel** gives a review
DOCX, an editing workbook and a `coursecraft.rubrics/1` JSON document.
**Weave** takes a completed rubric in Word, Markdown or JSON, runs a
preflight, requires a typed approval, and gives a validated rubric-only import
package with review companions and a receipt. The imported rubric is attached
to its assignment, discussion or quiz by hand. Never imports.

Ships as the [Rubric Bundle](https://github.com/timebeing92/brightspace-rubric-bundle),
the [Loom Runner](https://github.com/timebeing92/brightspace-rubric-loom-runner)
and a Hall bench with both doors.

### Quiz Binder

Takes an export. **Unbind** gives verified local evidence of every quiz and
its question library: a reviewer workbook, a detailed workbook, a normalised
`coursecraft.quiz/1` model, a Reading Room, receipts and a readiness report.
**Compose** takes explicit reviewer proposals and approvals for one, several
or all quizzes and gives each a strict readiness result. **Rebind** takes one
authoring-ready quiz and gives a locally validated Brightspace quiz package.
Never signs in; never imports.

Question content keeps its declared form through the lane: plain text, HTML
or XHTML, and MathML for notation with the fallback image Brightspace keeps
beside it. Rich content the lane cannot represent, a missing or ambiguous
asset, or a colliding target identity refuses the build rather than losing
anything. Inline previews of the images inside questions (molecular diagrams
were the case that forced it) exist as a Workbench candidate awaiting
upstream adoption; rich-math reviewer adapters and typed-equation conversion
run today as course-local adapters and are roadmap work for the lane.

Ships as the [Quiz Bundle](https://github.com/timebeing92/brightspace-quiz-bundle)
with its local Quiz Workshop terminal; the Hall exposes Unbind only.

### Catalog

Takes the Wizard's versioned JSON (never D2L XML) and gives a queryable,
taggable database of course components (assignments, discussions, quizzes,
checklists, rubrics, grade items, content sections) with relations within a
course and, later, across a curriculum. A reader and an archivist wizard sit
on top. It currently reads `coursecraft.blueprint/4` and refuses `/5` until
its intake moves.

### Planned: Interactives Forge and Pagewrights' Guild

Both are visible in the Hall as planned benches and are backed by private,
pre-release scaffolds that are not products yet:

- **Interactives Forge** turns structured practice data (questions, answers,
  feedback in rows) into Brightspace Creator+ practice fragments with a
  preview: today multiple choice, multiple select, fill-in-the-blank, sorting
  and sequencing, each backed by a preserved Brightspace-authored example.
  Hotspot and matching stay out until an example exists. It will never place
  a practice in a course. The generator and its seeds live in the Workbench
  and a private interactives bundle; the bench lights when that ships as a
  verified release.
- **Pagewrights' Guild** is a page-design surface: inline-safe HTML elements
  that survive strict editor fields, full-page templates with a shared
  stylesheet, and checks that every asset and link in a page resolves, with a
  deterministic preview and build. The element library and templates exist
  as a staged, colleague-facing design kit (a private frontend design
  bundle); the bench lights when that kit ships as its own release. The
  Packager's page templates are an early relative of this work.

## 3. The in-between mechanisms

Where one tool's output becomes another's input, and what carries it.

```
   D2L export ZIP ═══════════════════════════════════════════════════════════════
        │ (evidence: hashed, never edited)
        ├──► Wizard ──► blueprint bundle ─────┬──► review in Word / Markdown
        │                                     ├──► Catalog intake (JSON, versioned)
        │                                     └──► Packager from-wizard ──► authoring DOCX
        │                                                 subset only; a ledger of what it
        │                                                 kept, dropped nothing silently
        ├──► Rubric Loom Unravel ──► rubric DOCX / workbook / JSON ──► edit ──► Weave ──► rubric package
        └──► Quiz Binder Unbind ──► workbooks / model ──► review ──► Compose ──► Rebind ──► quiz package

   authoring DOCX ══════════════════════════════════════════════════════════════
        │ (written by people; the whole interface for a subject expert)
        └──► Packager read ──► model (+ ledger, readiness) ──► build ──► package ──► verify
                                      │                                      │
                                      └── the model is the contract ─────────┘
                                          between authoring and the package

   packages ═══════════════════════════════════════════════════════════════════
        whole course (Packager) · one quiz (Rebind) · rubrics only (Weave)
        └──► a person imports into an empty sandbox ──► re-export ──► the Wizard reads it back
                                                                     ──► receipt (L4 evidence)
```

The contracts at the seams are versioned JSON schemas owned upstream:
`coursecraft.blueprint/5` and `coursecraft.structure/1` (the Wizard's
outputs), `coursecraft.rubrics/1`, `coursecraft.quiz/1`, the run identity
record every tool writes, and on the Packager's side its own
`build_settings/0.1`, course model and `packager_release/1` manifest. A
consumer that meets an unknown version refuses rather than guesses; that
refusal is the guard that keeps the lanes honest.

## 4. What the Packager does, and does not do

From `CAPABILITIES.json`, shape by shape. "Builds" has L4 evidence for the
named historical packages or local evidence for the shapes new since 0.2.2
(the record says which). "Carries" means copied forward unchanged from a
source export. "Refuses" means the build stops with a named diagnostic.

| The Packager… | Shapes |
| --- | --- |
| **builds** | modules with HTML topics; hidden modules and topics; external link topics; one page in two modules; relative links between pages; grade items; assignment folders joined to grade items; discussion forums with graded topics, more than one forum per package; checklists with module links and derived items; analytic rubrics with named levels and weighted criteria, attached to folders and topics; dates and a term calendar |
| **carries** | a quiz from a source export, unchanged |
| **refuses** | authoring a quiz from a blueprint; images (native runs and embedded markers); release conditions; intelligent agents; groups; surveys; LTI links; Creator+ practices; unresolved readiness fields in a normal build; a model without source accounting |

And who does the refused things:

| Not the Packager | Who, today | Status |
| --- | --- | --- |
| author or revise a quiz and its questions | Quiz Binder: Unbind, Compose, Rebind | released (public release candidate); Hall exposes Unbind only; authoring is local |
| extract, revise and re-import rubrics on their own | Rubric Loom: Unravel, Weave | released (Bundle, Runner, Hall bench) |
| Creator+ practices and interactives | Interactives Forge | planned; private pre-release scaffold with five evidence-backed modes |
| page design beyond the two templates: inline-safe elements, full-page templates, asset and link checks | Pagewrights' Guild | planned; private pre-release design kit |
| images and other files inside pages | image assets already travel with quizzes through Quiz Binder (Unbind keeps a quiz's image references and the files themselves, and a Workbench candidate shows them inline in the Reading Room), and the Guild's design kit carries asset and link checks for pages; bringing an asset-bearing authoring package into the Packager is backlog family E in `CONVERSION_BACKLOG_2026-10-13.md` | handled elsewhere; integration planned |
| mathematical notation: MathML, typed equations | Quiz Binder keeps MathML and its fallback images through Unbind and Rebind; rich-math review adapters and typed-equation conversion are course-local today (the organic chemistry intake) and roadmap work upstream; the blueprint vocabulary has no equation form today, so notation in pages is outside the Packager | kept by the quiz lane; editing planned |
| release conditions, intelligent agents, groups, surveys, LTI links, announcements, calendar events | set up in Brightspace after import | by design: course operations, not course content |
| a hosted Packager bench | the Hall | under consideration; not started |
| a queryable view across courses | Catalog | in development; reads the Wizard's JSON |
| importing into a tenant | a person, with a receipt | always |

Back to [The big picture](BIG_PICTURE.md).
