# The big picture

What a Brightspace course package is, what the tools around it do, and how
they close a loop. Three pages, drawn from real builds and the tools' own
outputs:

| Page | What it shows |
| --- | --- |
| **This one** | the loop, where the engine lives, the evidence ladder |
| [Anatomy of a Brightspace package](PACKAGE_ANATOMY.md) | every file kind in a package, the manifest's two trees, the joins between objects, and which tool reads or writes each kind |
| [Who does what](WHO_DOES_WHAT.md) | each tool's intake and output, the hand-off points between them, what the Packager does not do, and which released or planned tool does it instead |

## 1. The loop

```
                 ┌─────────────────────────────────────────────────────────────┐
                 │                      BRIGHTSPACE (D2L)                       │
                 │   a live course: modules · pages · assignment folders ·      │
                 │   discussions · checklists · quizzes · rubrics · grade items │
                 └──────────────┬───────────────────────────────▲──────────────┘
                     export     │                               │  import
                   (by D2L)     │                               │  (by an operator,
                                ▼                               │   never by a tool)
                 ┌──────────────────────────┐     ┌─────────────┴──────────────┐
                 │    course export ZIP     │     │     import package ZIP      │
                 │    what D2L writes       │     │     what the Packager writes │
                 └──────────────┬───────────┘     └─────────────▲──────────────┘
                                │                               │
                       BLUEPRINT WIZARD                 BLUEPRINT PACKAGER
                       reads the export                 reads the blueprint,
                       and writes a blueprint           builds the package,
                       for review                       reads it back to check
                                │                               │
                                ▼                               │
                 ┌──────────────────────────┐     ┌─────────────┴──────────────┐
                 │   blueprint bundle       │     │   authoring blueprint      │
                 │   JSON + DOCX + Markdown │ ──► │   one Word document in a   │
                 │   + QA report + receipt  │     │   small fixed layout       │
                 └──────────────────────────┘     └────────────────────────────┘
                                    bpk.py from-wizard        written by designers
                                    (an explicit subset)      and subject experts
```

Two more lanes run beside this one on the same engine and the same exports:
**Rubric Loom** (rubrics out of an export, rubrics back in as their own
package) and **Quiz Binder** (quizzes and their question library out, a
reviewed quiz back in). The Packager builds a whole course shell; it carries a
quiz forward unchanged and refuses to author one, and it builds rubrics from
the blueprint's appendix. [Who does what](WHO_DOES_WHAT.md) draws the lanes
side by side.

The same engine sits under every tool: the package writers and the
independent readers come from CourseCraft Workbench and are vendored into
this repository at one named commit (section 3). The Wizard extracts; the
Packager composes; the Packager's `verify` step runs the Wizard's readers over
the package it just built, so what was authored is checked by the same eyes
that read real exports.

## 2. What "verified" means here

```
   blueprint ──read──► model ──build──► package ──(the engine's readers)──► extracted
       │                 │                                                     │
       │                 └──────────────────── compared in verify ─────────────┘
       │
       └── from-wizard ◄── bundle ◄── Wizard ◄── (the same package, or a real export)
```

A build is verified when the package, read back by readers written
independently of the writers, matches the model it was built from. That is
local evidence: the tool agrees with itself through two code paths. It is not
the same as a package having been imported into a tenant and re-exported.
The evidence ladder in `CAPABILITIES.json` keeps the two apart:

| Level | Meaning |
| --- | --- |
| L1 | the tool reads its own output back (every build) |
| L2 | the output matches a real Brightspace export of the same shape |
| L3 | the package imported into a course |
| L4 | the package imported, was re-exported, and the re-export was read back (`IMPORT_RECEIPTS.md`) |

Every run also leaves a receipt: who built it (tool, version, release
commit), from which inputs (hashes), with which engine files (hashes), with
which settings. A page's HTML opens with one comment naming its build:

```html
<!-- Blueprint Packager 0.3.1 · Demo Course · blueprint course.docx sha256 dd481fe158d9 · template composite-navy · built from the course model, not hand-edited -->
```

## 3. Where the engine lives

```
   CourseCraft Workbench (private: the engine's home, the evidence lane, the R&D)
   │   d2l_package_lib.py · rubric_package_lib.py · the readers · the page gate · the schemas
   │
   ├──► Blueprint Bundle (public release, tagged) ──► Wizard Runner (local) ──► Workshop Hall (hosted)
   │                                                  pins one Bundle release    pins one Bundle release
   ├──► Rubric Bundle, "Rubric Loom" (public) ──────► Loom Runner (local) ────► Workshop Hall
   ├──► Quiz Bundle, "Quiz Binder" (public rc) ─────────────────────────────► Workshop Hall (Unbind only)
   │
   └──► Blueprint Packager (this repository, public)
            vendor/coursecraft_workbench/   33 files copied at one named commit,
            MANIFEST.json                   each file's SHA-256 recorded; the commit
                                            is written into every receipt
```

Nothing in a vendored file is edited here. A change to engine behaviour is
made upstream and brought here by re-pinning (`scripts/check_vendor_drift.py`),
so the Wizard and the Packager keep reading and writing the same shapes.
Which commit a run used is in its receipt, so any package can be tied to the
exact engine that made it.

Next: [Anatomy of a Brightspace package](PACKAGE_ANATOMY.md).
