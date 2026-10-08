# Blueprint Packager

Turns a flat course blueprint, a Word document in a fixed grammar, into a
Brightspace import package, in inspectable stages with a receipt at each one.
It is the forward half of a round trip whose reverse half is Blueprint Wizard
in the CourseCraft Workbench, which reads a Brightspace export back into the
same grammar. The two share one visual language: headings one to one with the
page, bracket lines for panels and links, one row per module before Week 1.

Status: version 0.1.0, its own repository since 2026-10-08. Evidence level L4:
a whole course built with it was imported into a Brightspace sandbox,
re-exported, and read back with every structural check passing (see
`docs/IMPORT_RECEIPTS.md`).

## How it relates to the Workbench

The packager builds on the Workbench's package-writing libraries and verifies
with its readers. Those scripts and the schema files they load are vendored
under `vendor/coursecraft_workbench/` at commit `9d3a620`, so this repository
runs on its own. `vendor/coursecraft_workbench/MANIFEST.json` names the commit
and every file's hash.

```bash
python3 scripts/check_vendor_drift.py /path/to/coursecraft_workbench            # report drift
python3 scripts/check_vendor_drift.py /path/to/coursecraft_workbench --commit X  # re-pin from upstream
```

Vendored files are never edited here; a change to borrowed behaviour belongs
upstream first. A run can use a checkout instead of the mirror with
`--workbench-scripts /path/to/coursecraft_workbench/scripts` or the
`BPK_WORKBENCH_SCRIPTS` environment variable, and every receipt and
verification report records which copy was used (`blueprint_packager/workbench.py`).

## Stages

| Stage | Command | Input | Output |
|---|---|---|---|
| 0. Blank | `bpk.py blank` | course number, title, term, weeks | a blank blueprint in the current convention that reads with no errors |
| A. Ingest | `bpk.py ingest` | blueprint DOCX | paragraph stream with stable ids |
| B. Normalize | `bpk.py normalize` | DOCX and a course map | normalized DOCX, ledger, fidelity proof |
| C. Read | `bpk.py read` | normalized DOCX | course model JSON with joins and diagnostics |
| D. Build | `bpk.py build` | course model and build settings | package folder, ZIP, pages-only refresh ZIP, receipts, object map |
| Verify | `bpk.py verify` | build folder and model | twelve read-back checks, including the Page Kit page gate |
| Re-sync | `bpk.py rebase-map` | two exports of one blueprint and a course map | the map carried to the later export, with a change report |

A blueprint that is already in the canonical layout skips stage B.

## Run it

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

python3 bpk.py blank out.docx --course-number "NEW 101" --course-title "Title" --term "Spring A 2027" --weeks 8
python3 bpk.py read BLUEPRINT.docx --output-dir OUT --label course
python3 bpk.py build OUT/course__course_model.json --settings build_settings.json --output-dir BUILD --force
python3 bpk.py verify BUILD --model OUT/course__course_model.json
python3 bpk.py rebase-map OLD.docx NEW.docx --map MAP.json --output NEW_MAP.json
pytest -q
```

Exit codes: 0 success; 1 the step ran and found errors; 2 usage or refusal;
130 interrupted. Build settings a course can use: `template`,
`fragment_styles`, `grade_item_names`, `points_determinations`, `calendar`,
`checklists`, `link_cleanup`, `link_restorations`, `carried_quizzes`,
`dropbox_defaults`, `discussion_defaults`, `package.course_label`.

## Where a course lives

A course build keeps its own course map, build settings, normalized
blueprint, and package in its own repository and names this tool by path or
version. MBA 620 Fall B 2026, the course this tool was built for, lives in
`MBA_620_Marketing_Major_Edit_Fall2026` (private), which also keeps the frozen
copy of the tool that built its package, the raw sandbox exports, and the
sandbox round records.

## What is in here

- `bpk.py` — command line
- `blueprint_packager/` — the stages, one module each; `workbench.py` decides where the Workbench scripts come from
- `blueprint_packager/templates/composite_navy/` — the default page template: a composite of BUMK 515, MBA 630, and BUMG 660 with the darker navy brand and no hero blocks; see `docs/TEMPLATE_COMPOSITE_NAVY.md`
- `blueprint_packager/templates/bumk515_classic/` — the page template lifted from the BUMK 515 export, selectable by name
- `vendor/coursecraft_workbench/` — the pinned mirror of the Workbench scripts and schemas; `scripts/check_vendor_drift.py` keeps it honest
- `CAPABILITIES.json` — every shape the tool builds, with its evidence level
- `docs/DESIGN.md` — the design, the structure vocabulary, and open directions
- `docs/AUTHORING_GUIDE.md` — for people writing or editing a blueprint
- `docs/IMPORT_RECEIPTS.md` — the sandbox receipts that set the evidence level
- `docs/records/` — the survey reports and work records behind the tool
- `docs/PROMOTION_MANIFEST.md` — what belongs upstream, and where things stand
- `tests/` — synthetic fixtures; `pytest -q`
- `AGENTS.md` — what the tool owns and what it must never do

## Conventions it follows

Those of the CourseCraft ecosystem's producers: a command line with explicit
inputs and outputs; a receipt for every run with the producer's identity and
the hashes of what it read and wrote; stable identities for the objects it
builds; evidence levels per shape, from local read-back (L1) to a confirmed
round trip (L4); raw exports treated as evidence and never edited; no wording
changes except as recorded, authorized entries; no AI attribution in commits
or bundles.

## Dependencies

Python 3.11 or later; `python-docx`, `lxml`, `openpyxl`, `jsonschema` (see
`requirements.txt`).
