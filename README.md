# Blueprint Packager (working title)

Turns a flat course blueprint into a Brightspace import package, in four
inspectable stages. It was built inside the MBA 620 course build as an
independent tool. It uses Blueprint Wizard and the Workbench rubric and
component libraries as building blocks and is not tied to their releases.

Status: version 0.1, downstream proving ground. Evidence level L1. Nothing built
with it has been imported into Brightspace.

## Stages

| Stage | Command | Input | Output |
|---|---|---|---|
| A. Ingest | `bpk.py ingest` | blueprint DOCX | paragraph stream with stable ids |
| B. Normalize | `bpk.py normalize` | DOCX and a course map | normalized DOCX, ledger, fidelity proof |
| C. Read | `bpk.py read` | normalized DOCX | course model JSON with joins and diagnostics |
| D. Build | `bpk.py build` | course model and build settings | package folder, ZIP, receipts, object map |
| Verify | `bpk.py verify` | build folder and model | twelve read-back checks, including the Page Kit page gate |
| Re-sync | `bpk.py rebase-map` | two exports of one blueprint and a course map | the map carried to the later export, with a change report |

A blueprint that is already in the canonical layout skips stage B.

## Run it

From the repo root, with the repo's virtual environment:

```bash
# MBA 620: rebuild the course map, normalize, build, verify
.venv/bin/python workspace/design/mba_620/blueprint_normalization/build_course_map.py
.venv/bin/python tools/blueprint-packager/bpk.py normalize \
  workspace/reference/blueprints/mba_620/2026-10-06__mba_620_fall_b_2026__google_doc_api_export__1839z.docx \
  --map workspace/design/mba_620/blueprint_normalization/course_map.json \
  --output-dir workspace/design/mba_620/blueprint_normalization/normalized_2026-10-06 \
  --label mba_620_fall_b_2026__blueprint
.venv/bin/python tools/blueprint-packager/bpk.py build \
  workspace/design/mba_620/blueprint_normalization/normalized_2026-10-06/mba_620_fall_b_2026__blueprint__course_model.json \
  --settings workspace/design/mba_620/blueprint_normalization/build_settings.sandbox.json \
  --output-dir workspace/generated/import-ready-components/bundles/mba_620_fall_b_2026__sandbox_2026-10-06 --force
.venv/bin/python tools/blueprint-packager/bpk.py verify \
  workspace/generated/import-ready-components/bundles/mba_620_fall_b_2026__sandbox_2026-10-06 \
  --model workspace/design/mba_620/blueprint_normalization/normalized_2026-10-06/mba_620_fall_b_2026__blueprint__course_model.json
```

Exit codes: 0 success; 1 the step ran and found errors; 2 usage or refusal; 130 interrupted.

A second opinion from another Workbench checkout, which leaves nothing behind there:

```bash
.venv/bin/python -B tools/blueprint-packager/bpk.py verify BUILD_DIR --model MODEL.json \
  --workbench-scripts "/path/to/coursecraft_workbench/scripts" --label upstream
```

Build settings a course can use: `grade_item_names`, `points_determinations`, `calendar`, `checklists`, `link_cleanup`, `link_restorations`, `carried_quizzes`, `dropbox_defaults`, `discussion_defaults`. MBA 620's settings file shows each with its source.

When the source document changes, carry the course map to the new export:

```bash
.venv/bin/python tools/blueprint-packager/bpk.py rebase-map OLD.docx NEW.docx --map MAP.json --output NEW_MAP.json
```

For people writing or editing a blueprint, read `docs/AUTHORING_GUIDE.md`.
For moving the tool out of this repository, read `docs/PROMOTION_MANIFEST.md`.

## What is in here

- `bpk.py` — command line
- `blueprint_packager/` — the stages, one module each
- `blueprint_packager/templates/composite_navy/` — the default page template (2026-10-07): a composite of BUMK 515, MBA 630, and BUMG 660 with the darker navy brand and no hero blocks; see `docs/TEMPLATE_COMPOSITE_NAVY.md`
- `blueprint_packager/templates/bumk515_classic/` — the page template lifted from the BUMK 515 export, selectable by name
- `CAPABILITIES.json` — every shape the tool builds, with its evidence level
- `docs/DESIGN.md` — the design, the structure vocabulary, and open directions
- `tests/` — synthetic fixtures; `pytest tools/blueprint-packager/tests -q`
- `AGENTS.md` — what the tool owns and what it must never do

## Dependencies

Python 3.11 or later, `lxml`, and `python-docx` for test fixtures. Stage D and
verification need the Workbench scripts in the repo's `scripts/` folder.
