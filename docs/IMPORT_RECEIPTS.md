# Import receipts

The receipts that set this tool's evidence level, copied from the MBA 620
course repository's `docs/IMPORT_TEST_LOG.md` (Receipts 10 to 13), where the
ladder is defined: L1 local read-back, L2 shape matches a real export, L3
imports, L4 survives import and re-export. "Course repo" paths are relative to
that repository, `MBA_620_Marketing_Major_Edit_Fall2026` (private). Later
receipts are added here as rounds happen.

### Receipt 13 — 2026-10-08 — Clean import after emptying the sandbox, with the composite template — L4

- **Level:** L4
- **Package / artifact:** round-3 package, SHA-256 `66d6b4cfb0c2d4434ad646e6c2fba7595f458f98d2decc13993a46474bf3b4e1`, 132,884 bytes
- **Built by:** the Blueprint Packager (then `tools/blueprint-packager` in the course repository); composite-navy template (passes 2 and 3), template styles in editor fields, provenance comment, title split
- **Target:** sandbox course 52145, emptied of the earlier rounds' content first
- **Result:** pass, 12 of 12 against the model (re-export `D2LExport_52145_Test2_202610805.zip`, SHA-256 `ad526459…`): 10 modules, 37 topics, 16 activities linked to 14 grade items totalling 100, 10 rubrics cell for cell, 8 checklists, 21 dates, 1,063 paragraphs, 12 pages with the provenance comment. Leftover round-1 and round-2 rubrics and checklists were still in the course and did not interfere. The manifest carried 15 Brightspace-minted codes and none of the package's: in a reused course the codes are reserved by the deleted objects.
- **Evidence:** course repo `workspace/review/mba_620/sandbox_2026-10/SANDBOX_ROUND_3.md`, `REEXPORT_3_VERIFICATION.md`, raw snapshot course repo `workspace/exports/raw/20261008-122602__mba_620_sandbox_reexport_3.zip`
- **Follow-up:** the composite template and the styled editor fields are now L4; the MBA 620 package is ready for the real shell once the SME items and the syllabus are settled.

### Receipt 12 — 2026-10-08 — Pages-only refresh through Manage Files — L4 (operator-reported, pages inspected)

- **Level:** L4 for page content: the operator uploaded the `course_pages` folder from `course_pages_refresh.zip` through Manage Files and reports every HTML page updated in place with no new objects. Re-export comparison for this step not taken; the round-2 re-export already showed files overwrite by path.
- **Package / artifact:** `course_pages_refresh.zip` written beside the round-3 package by the Blueprint Packager (then `tools/blueprint-packager` in the course repository)
- **Target:** sandbox course 52145
- **Result:** pass (operator: "the pure page package was accepted and did update all html pages")
- **Evidence:** course repo `workspace/review/mba_620/sandbox_2026-10/SANDBOX_ROUND_2.md`
- **Follow-up:** the in-place update path for pages; everything else is delete-first.

### Receipt 11 — 2026-10-08 — Re-import over existing content (the overwrite experiment) — L4, negative result

- **Level:** L4 (import, inspection, re-export, read back)
- **Package / artifact:** the round-2 package, SHA-256 `40e4e920a6aca24aec7f96c402a439e0688c2ee5af5e680f3b2dd081c33ba956`, 127,854 bytes, imported OVER the round-1 content of sandbox course 52145
- **Built by:** the Blueprint Packager (then `tools/blueprint-packager` in the course repository), same resource codes as round 1 by design
- **Target:** sandbox course 52145
- **Result:** completed with 14 warnings ("Cannot associate grade item … already in use"). Re-export `D2LExport_52145_Test2_202610809.zip` (SHA-256 `7fc98c80…`): modules 10 → 20, topics 37 → 74, assignment folders 7 → 14, discussion forums 2 → 4 and topics 8 → 16, checklists 8 → 16, quizzes 1 → 2, rubrics 10 → 20, grade items 14 → 28 with 14 unlinked; course files 12 → 12, every one overwritten in place (round-2 provenance comment present) and shown by both module copies. Resource codes: the 47 round-1 codes once each, 15 new codes minted, the rest of the duplicates without one. Resource codes are carried, not matched; files match by path.
- **Evidence:** course repo `workspace/review/mba_620/sandbox_2026-10/SANDBOX_ROUND_2.md`, `round_2__import_log.txt`, `REEXPORT_2_VERIFICATION.md`, raw snapshot course repo `workspace/exports/raw/20261008-111127__mba_620_sandbox_reexport_2.zip`
- **Follow-up:** "import over" is not an update path except for pages. The packager now writes `course_pages_refresh.zip` for a Manage Files refresh of page content (untested). A built course is otherwise updated by deleting first. To be recorded upstream as documentation.

### Receipt 10 — 2026-10-07 — MBA 620 Fall B 2026 whole-course package, sandbox round 1 — L4

- **Level:** L4
- **Package / artifact:** `workspace/generated/import-ready-components/bundles/mba_620_fall_b_2026__sandbox_2026-10-06/mba_620_fall_b_2026__sandbox_package.zip` as built at 13:46 (SHA-256 `2365d99b2b5830909ba3fbf0176aeb60cb166d98799d4b5b187c1b47d3654a95`); the folder has since been rebuilt with the round's fixes
- **Built by:** the Blueprint Packager (then `tools/blueprint-packager` in the course repository) (`bpk.py build`) from the normalized MBA 620 blueprint of 2026-10-06 and `build_settings.sandbox.json`
- **Target:** sandbox course 52145 (operator's tenant)
- **Result:** pass. Re-export `D2LExport_52145_Test2_202610705.zip` (105,924 bytes, SHA-256 `045bfe2c4c6a4632935c245c8dd54b87e719db7b0d3c1b974bbec7289b199233`) read back by `bpk.py verify` in place of the build: 12 of 12 checks. 10 modules and 37 topics, 50 join edges, 16 activities with points and rubrics, 10 rubrics (216 cells), 1,063 authored paragraphs, 8 checklists, 21 dates including the quiz's nested-form due date, 47 resource codes unchanged. Brightspace rewrote two forms: date stamps lose `.000Z`; curly quotes in a grade item name become straight. The verifier now tolerates both and reports the second as a note.
- **Evidence:** course repo `workspace/review/mba_620/sandbox_2026-10/` (`SANDBOX_ROUND_1.md`, `REEXPORT_1_VERIFICATION.md`, `reexport_1__snapshot_receipt.json`); raw snapshot course repo `workspace/exports/raw/20261007-135502__mba_620_sandbox_reexport_1.zip`
- **Follow-up:** operator's visual findings fixed for round 2 (Week 1 objectives as bullets, heading sublines, plain editor fields, composite page template). The re-import-over-existing-content experiment remains open.

