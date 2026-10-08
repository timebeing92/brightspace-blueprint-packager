# Blueprint Wizard survey (read-only; nothing run or modified)

Abbreviations: `TOOLS` = `/Users/ehanson8/Documents/D2l & Coursebuilding Tools ` (trailing space); `BUNDLE` = `TOOLS/brightspace-blueprint-bundle`; `RUNNER` = `TOOLS/brightspace-blueprint-runner`; `OUT` = `/Users/ehanson8/Downloads/BUMK_515_Wizard_Test_Now_blueprint__blueprint_bundle`.

**Headline:** Blueprint Wizard is strictly one-way (export → blueprint). No reverse or round-trip code exists in the runner or bundle, and the planning docs explicitly exclude whole-course round-trip authoring from current scope.

## 1. What Blueprint Wizard is

**Two repos, one product (evidence).**
- `RUNNER/README.md:235-238`: "This repository owns the one-download experience: launchers, environment setup, release pairing, update verification, activation, rollback... It does not parse Brightspace XML or define extraction semantics."
- `RUNNER/README.md:248-254`: the bundle "is the pinned engine. It owns the extraction pipeline, emitted artifacts, JSON contracts, progress events... This runner... does not re-implement extraction logic."
- So the wizard is the runner (terminal UI and installer) wrapped around the bundle (engine). The runner is not the engine.

**Packaging and launch.**
- It is a terminal (TUI) program, Python 3.11+, with no AI (`RUNNER/README.md:14-24`).
- Managed ZIP layout in `/Users/ehanson8/Downloads/blueprint-wizard-managed-v2.8.1/`:
  - `Blueprint Wizard.command` / `.bat` / `blueprint_wizard_launcher.sh` call `launcher/stable_launcher.py`.
  - `current.json` selects `versions/2.8.1/{brightspace-blueprint-runner,brightspace-blueprint-bundle}`.
  - `user-data/` holds settings, logs and outputs.
- `receipts/launches.jsonl` shows the actual command: `python3.13 …/versions/2.8.1/brightspace-blueprint-runner/scripts/blueprint_wizard.py --bundle-dir …/versions/2.8.1/brightspace-blueprint-bundle`.
- Other install paths are a portable ZIP, a git clone of both repos, and a curl installer (`RUNNER/README.md:86-145`).
- Non-interactive use is `blueprint_wizard.sh --yes --export …` (`README.md:267-276`).
- Bundle dependencies are `openpyxl`, `python-docx` and `jsonschema` (`BUNDLE/requirements.txt`); LibreOffice is not needed.
- There is a hosted peer: `TOOLS/coursecraft-workshop-space` (Gradio on a Hugging Face Space, `BUNDLE/ROADMAP.md:38-47`), pinned to bundle v1.3.2 (`coursecraft-workshop-space/bundle_pin.json`).

**Versions.**
- Runner tags run v2.1 to v2.8.1; bundle tags run v1.0.0 to v1.3.2.
- v2.8.1 managed is runner `e5a94b8` plus bundle `f346ee7` (1.3.2), with six contract hashes (`versions/2.8.1/RELEASE_MANIFEST.json`, `RUNNER/installer-compatibility.lock`).
- `RUNNER/CHANGELOG.md:8-31`: v2.8.1 (2026-07-19) "adopted its producer-owned delivery verdict"; v2.8.0 (07-17) "Added the stable managed launcher."

**The UNRELEASED c5b60a6 kit is older than v2.8.1, not newer.**
- `READ_ME_FIRST.txt:13-15`: "Wizard version: v2.7.0 (review build; not the published v2.7.0 ZIP)", runner `c5b60a6`, bundle `ec0ba6a` (VERSION 1.2.0).
- It is the pre-release test kit for the stable launcher that shipped in v2.8.0; `c5b60a6` is "Add reproducible unreleased launcher review kit", 2026-07-16.
- Differences from v2.8.1:
  - three contracts instead of six (no activities, structure or run schemas);
  - no `course_artifact_contracts.py`;
  - `launcher/install_state.py` lacks runtime-file checksum validation;
  - older `blueprint_wizard.py`.
- `blueprint_schema.json` is identical in both (sha `419a6ba4…`).

**Other copies.** `/Users/ehanson8/Downloads/brightspace-blueprint-runner-main` and `…-main 2` are 14 July source ZIPs of the runner only (no bundle). `RUNNER/dist/` holds v2.1 to v2.7.0 ZIPs.

## 2. Pipeline

- The wizard builds one command (`RUNNER/scripts/blueprint_wizard.py:776-794`): `build_blueprint_bundle.py <export> --label … --progress-events [--course-title/--course-number/--term] [--skip-qa] [--check-external-links] [--no-docx] [--docx-section-layout top|left]`.
- Input is an export ZIP or an unpacked folder with `imsmanifest.xml`.
- Steps, per `BUNDLE/README.md:94-109`:
  1. `export_inventory.py`
  2. `manifest_probe.py`
  3. `reconstruct_course_structure.py --extract-html`
  4. `extract_course_activities.py`
  5. `extract_rubrics_to_workbook.py` (if `rubrics_d2l.xml` is present)
  6. `course_qa_report.py`
  7. model assembly to `coursecraft.blueprint/4` JSON, plus Markdown
  8. `blueprint_to_docx.py`
  9. `rubrics_to_docx.py`
  10. `docx_structure_qa.py`
  11. optional `render_blueprint_docx.py`
- Markdown and DOCX both render from the same JSON model.

**BUMK 515 bundle files (bytes), all prefixed `BUMK_515_Wizard_Test_Now_blueprint__` unless noted:**

| File | Bytes |
| --- | --- |
| `blueprint.docx` | 84,882 |
| `blueprint.json` | 374,989 |
| `blueprint.md` | 121,010 |
| `cps_blueprint.md` (byte-identical legacy alias) | 121,010 |
| `course_activities.json` | 309,928 |
| `course_activities.md` | 1,166 |
| `course_activities.xlsx` | 40,457 |
| `course_qa.json` | 4,407 |
| `course_qa.md` | 4,215 |
| `course_structure.json` | 351,063 |
| `course_structure.md` | 5,191 |
| `docx_structure.json` | 571 |
| `docx_structure.md` | 434 |
| `D2LExport_102529_BUMK-515-TEMPLATE_20267753__inventory.json` | 3,864 |
| `D2LExport_…__inventory.md` | 2,412 |
| `D2LExport_…__manifest_probe.json` | 24,237 |
| `D2LExport_…__manifest_probe.md` | 14,659 |
| `README.md` | 783 |

- **This bundle is not v2.8.1 output.** `OUT/README.md:3` gives the source as `/tmp/gradio/…`, dated 14 July. My inference is that it came from the hosted Workshop Space at bundle v1.0.0.
- Current output adds `__rubrics.{json,xlsx,docx}`, `__pipeline_status.{md,json}`, `__run_identity.json` and a Rubric Appendix in the DOCX. A current example is `BUNDLE/workspace/review/MBA_620_Fall_B_2026__blueprint_bundle/` (13 Aug, local runner).

## 3. Blueprint format

**Schema.** `BUNDLE/schemas/blueprint_schema.json`, `$id` `coursecraft.blueprint/4`, `additionalProperties: false`.

**JSON top-level keys (`OUT/…__blueprint.json`):**
- `schema`, `template_reference`, `course_number`, `course_title`, `term`
- `front_matter` {`course_description`, `required_materials`, `course_learning_outcomes`, `course_introduction`}
- `before_week_1[]`
- `weeks[]` {`title`, `overview`, `learning_objectives`, `resources`, `assignments`, `discussions`, `checklist`, `other_sections`}
- `unplaced_activities` {`assignments`, `discussions`}
- `diagnostics[]`

**Blocks and sections.**
- `overview` and `learning_objectives` are flat block arrays.
- The other week fields are `labeled_section` objects: {`label`, `blocks`, optional `source_page`, `level`}.
- A block is {`kind`, `level`, `runs`:[{`text`,`href`}], optional `meta`, optional nested `blocks`}.
- The kind enum is `p, li, label, practice, visual, dropdown, embed, image, file, hidden, divider`.
- BUMK counts: li 373, p 372, label 111, dropdown 52, visual 25, divider 23, embed 9, hidden 6, image 1.

**Markdown shape (220 lines; each week is a one-column table whose cells are `<br>`-joined):**
- H1 is the course title, followed by an evidence-mode blockquote.
- Three one-cell tables follow: `COURSE DESCRIPTION (…)`, `TEXTBOOK/S OR REQUIRED MATERIALS`, `COURSE LEARNING OUTCOMES`. All three read "Needs review: not found in export extraction." here.
- Then `### Course Introduction`, `### Before Week 1: Additional Resources and Information`, `Course Content:`, `### Week N - …` ×8 separated by `---`, `## Unplaced Activities` (`### Assignments`, `### Discussions`), and `## Extraction Notes`.
- The label strings are hard-coded in `BUNDLE/scripts/build_blueprint_bundle.py:1716-1771`.

**Week 1 skeleton (`OUT/…__blueprint.md:37-52`, bodies truncated):**
```
### Week 1 - Foundations Marketing Innovation
| Section |
| --- |
| **Overview: (add an introduction to the week's topic and activities here, with references as needed)** |
| **Week 1 Overview and Learning Materials:**<br><br>Week 1 – Foundations of Marketing Innovation<br><br>**Week 1 – Foundations of Marketing Innovation:**<br><br><hr><br><br>Welcome to Week 1…<br><br>**Course Introduction & Week‑1 “Level‑Set” Lecture:**<br><br>**Video embed:** [Week 1 Lecture](https://player.vimeo.com/…)<br><br>[Transcript](…) \| [Slides](…) \| Time […]<br><br><hr>…<br><br>**Dropdown / expandable section: The Three C’s – Company, Customers, Competition**<br><br>The Three C’s provide…<br>• Company : …<br>• Customers : …<br><br>**Dropdown / expandable section: STP – Segmentation, Targeting, Positioning**<br><br>…<br><br>**Dropdown / expandable section: The Four P’s – Product, Price, Place, Promotion**<br><br>…<br><br><hr><br><br>**Visual cue: Callout**<br><br>**Comprehensive Marketing Plan – Your Summative Course Project (Due Week 8):**<br><br>… |
| **Learning Objectives: Must follow the guidelines in this Learning Objectives Guide.<br><br>Students will be able to:** |
| By the end of this week, students will be able to:<br><br>Define key marketing concepts… |
| **Assigned Reading and Multimedia: (add links, articles, textbook readings, videos). Include style-correct citations.** |
| **Required Resources:**<br>• Levitt, T. (1975). [Marketing Myopia](…) …<br>• Drucker, P. F. (2006). […](…) … |
| **Assignment(s) and Instructions:** |
| **Group Contract Assignment:**<br>**Points: 3 pts**<br>**Gradebook item: Group Contract**<br>**Rubric: 1: Week 1 / 2— Group Contract Assignment**<br><br>…instructions…<br><hr><br>**Quiz: Week 1 Leveling Quiz:**<br>**Points: 3 pts**<br>**Gradebook item: Week 1 Leveling Quiz**<br>**Attempts allowed: 3**<br>**Time limit: No time limit**<br>**Questions: 25 drawn from 80 candidates**<br>**Sections: 10**<br><br>…quiz instructions… |
| **Discussion Board Prompts:** |
| **Week 1 Discussion: Marketing Confessions and Introductions:**<br>**Points: 1 pts**<br>**Rubric: 11: Week 1 Discussion— Marketing Confessions & Introductions**<br><br>…<div style="background-color:#f2f6fa; border-left:4px solid #9bb3c9; …">**Visual cue: Styled section (background: #f5fafa)**<br><br>…</div>… |
| **Checklist (mirrored from the export)** |
| **Week 1 Checklist:**<br>**Week 1 Checklist:**<br><br>• Complete the Introduction Discussion (Initial Post)<br>• … |
```

**Accordions and dropdowns.**
- An HTML `<summary>` becomes a `dropdown` block holding only the panel title (`BUNDLE/scripts/reconstruct_course_structure.py:599-602`).
- It renders as `**Dropdown / expandable section: <title>**` (`build_blueprint_bundle.py:1645`).
- The panel body follows as ordinary sibling `p`/`li` blocks with no end marker and no nesting.
- A class containing `accordion` becomes a `visual` cue "Accordion" (`reconstruct_course_structure.py:333`).
- `visual` blocks can nest children and render as a tinted `<div>`.

**Other elements.**
- **Rubrics:** in the blueprint they appear only as the `Rubric: <n>: <name>` label; the grids live in the separate `coursecraft.rubrics/1` files.
- **Points and grading:** per-activity `Points:` and `Gradebook item:` labels only. There is no grading table; grade items live in `course_activities.json` and the xlsx.
- **Section routing:** done by heading-alias substrings (`BUNDLE/knowledge/HOW_EXTRACTION_MAPS_TO_BLUEPRINT.md:65-100`).

**Facts relevant to reversal (the implications are my inference).**
- `blueprint.json` has no D2L identifiers: zero `resource_code`, `identifier` or `identifierref` keys. Those live in `course_structure.json` (58 nodes) and `course_activities.json`.
- `course_activities.json` also keeps verbatim `description_html` (14) and `instructions_html` (11).
- Documented losses (`HOW_EXTRACTION_MAPS_TO_BLUEPRINT.md:167-222`):
  - "Numeric due dates are deliberately not encoded"
  - "Question-bank contents are not blueprint content"
  - "Visual styling is translated into cues, not recreated"
  - "Fine inline styling (bold/italic, fonts, colors) and images are not embedded"
  - "The blueprint is a **review surface**"
- I did not open the DOCX. `OUT/…__docx_structure.md` reports 12 tables, 8 week sections, 'top' layout and 86 hyperlinks.

## 4. Reverse direction (blueprint → Brightspace)

**Nothing exists in the runner or the bundle.**
- `RUNNER/README.md:59-61`: "The Wizard reads and reports. It does not: import anything into Brightspace or change the source export".
- `BUNDLE/AGENTS.md:32`: "This is extraction and review, not instructional-content generation."
- A grep of `BUNDLE/scripts` found no `imsmanifest` writer and no `from_blueprint`, `build_course_component_package` or conformance code.
- The only "reverse" hit is `BUNDLE/CHANGELOG.md:637`, "custom `build_blueprint_bundle.py` (reverse: export → flat blueprint)", which treats extraction as the reverse of an earlier blueprint → course direction.
- The only code that reads a blueprint DOCX is `docx_structure_qa.py`, a QA check against the model, not an ingest.
- `BUNDLE/knowledge/BRIGHTSPACE_PACKAGE_STRUCTURE_AND_IMPORT_NOTES.md` (~lines 97-165) is a localized Workbench note: it mentions `workspace/generated/import-ready-components/` and "favor small importable bundles over early full-course package assembly", with no code behind it in the bundle.

**Not on the bundle roadmap.** `BUNDLE/ROADMAP.md` covers output/UX, packaging, delivery, catalog contracts and extraction quality only.

**Reverse-direction precedent in sibling products (`TOOLS/README.md:56-73`).**
- Rubric Loom is "Unravel" extraction plus "Weave" authoring and package generation, with "exact Word/Markdown intake templates".
- Weave emits `import_zip`, `rubrics_xml`, `normalized_authoring_json`, `mapping_report` and `review_report` (`BUNDLE/knowledge/PROGRESS_EVENTS_CONTRACT.md:86-99`).
- Quiz Bundle is Unbind / Compose / Rebind.
- Both use a separate authoring contract. `TOOLS/PLAN_2026-09-14_COURSECRAFT_DESKTOP.md:73` says extracted `coursecraft.rubrics/1` and authored `coursecraft.rubric_authoring/1` "remain distinct".

**Explicit scope statements in `PLAN_2026-09-14_COURSECRAFT_DESKTOP.md`.**
- Line 72: "Blueprint, activities, and structure models | Course outline and review display. | Extracted review models do not establish lossless whole-course authoring."
- Line 79: "A review archive, Manage Files bundle, and Brightspace import package have different contracts."
- Line 214: "The initial product scope excludes whole-course round-trip authoring, direct live LMS publishing…"

**Workbench side (outside the wizard).**
- `TOOLS/coursecraft_workbench/scripts/` has `build_course_component_package.py`, `build_page_package.py`, `d2l_package_lib.py` and `check_package_conformance.py`.
- `docs/project/BLUEPRINT_TO_BRIGHTSPACE_PROTOTYPING.md` treats a blueprint as "a **design source**, not automatically as package truth", for prototyping.
- I did not find a parser there for the wizard's flat blueprint, but I did not survey the Workbench exhaustively.

## 5. Boundaries and upstream relationship

- **Flow:** `coursecraft_workbench -> brightspace-blueprint-bundle -> brightspace-blueprint-runner | coursecraft-workshop-space | coursecraft-catalog` (`TOOLS/ECOSYSTEM.md:63-68`).
- **Promotion steps (`ECOSYSTEM.md:110-123`):** "Discover or refine extraction behavior in `coursecraft_workbench`", then "Promote stable, portable behavior into `brightspace-blueprint-bundle`".
- **Ownership (`ECOSYSTEM.md:125-134`):** the Workbench owns "reusable extraction meaning, schemas, evidence rules"; downstream repos own "product experience, release mechanics".
- **Design rule:** "extraction engines emit facts; user-facing tools make those facts understandable… without silently creating new truth" (ECOSYSTEM "UX Surface Strategy").
- **Drift tracking is from the Workbench side:**
  - `coursecraft_workbench/scripts/check_bundle_drift.py` uses `docs/project/share_bundles/brightspace-blueprint-bundle.map.json`: 19 mirror, 8 diverged-by-design and 22 bundle-only entries.
  - `build_blueprint_bundle.py`, `blueprint_to_docx.py` and `common_xml.py` are diverged-by-design.
  - Targets are the sibling repo and the staged `workspace/generated/shareable-brightspace-blueprint-bundle`.
  - Unlike the quiz, rubric, frontend and interactives bundles, the blueprint bundle has no `upstream/workbench_pin.json` (`TOOLS/ecosystem.json` pins list).
- **Contract copies:** `coursecraft.blueprint/4` exists in four places (Workbench reference, staged share, bundle, catalog), per `ecosystem.json`.
- **Release pairing:** `RUNNER/installer-compatibility.lock`, per-version `RELEASE_MANIFEST.json`, `PROVENANCE.json` (review kit) and `MANAGED_INSTALL_MANIFEST.json`.
- **Future branches (`ECOSYSTEM.md:959-981`):** Package Graph Visualizer/Diff, Creator+ Practice Composer, Design Space, and a Launcher/Hub. There is no blueprint-to-package item.
- **Licence:** AGPL-3.0-or-later plus commercial terms (`BUNDLE/COMMERCIAL.md`).
- **Stale doc:** `BUNDLE/README.md:3` says "Current release: 1.3.0" while `VERSION` says 1.3.2.

## 6. Git state

| Repo | Branch | State |
| --- | --- | --- |
| `BUNDLE` | `main` @ `4fee609` | Clean, level with origin/main. Three commits past tag v1.3.2 are an unreleased local run/2 promotion. |
| Worktree `TOOLS/.worktrees/brightspace-blueprint-bundle/codex-run2-promotion` | `codex/promote-run2` @ `4100d88` | Clean; already contained in main. |
| `RUNNER` | `agent/install-and-troubleshoot-guide` @ `85cef27` | Clean. Diverged 1/1 from origin/main `a59a431` ("Add Blueprint install and troubleshooting guide (#2)"), which looks like a squash merge. Local `main` (`90c8e69`) is 2 behind origin. |
| `TOOLS` control repo | `main` @ `69ed288` | Clean. |

**`BUNDLE` last 10 commits:**
- `4fee609` docs: record reviewed run2 publication boundary
- `4100d88` test: refresh synthetic sample for run2 producer
- `f969962` feat: promote reviewed run2 identity and title semantics
- `e8084b9` docs(progress): record deferred Weave convergence
- `d3482df` Record v1.3.2 release deployment
- `f346ee7` (v1.3.2) Keep delivery language coherent across every surface
- `6b26e84` Record v1.3.1 release deployment
- `be0ef5c` (v1.3.1) Report delivery usability in progress events
- `1fb8735` Record v1.3.0 release deployment
- `0b197d9` (v1.3.0) Preserve Bundle identity inside Wizard releases

**`RUNNER` last 10 commits:**
- `85cef27` Add Blueprint install help
- `521f51c` Refresh the Blueprint Wizard README (#1)
- `90c8e69` Record v2.8.1 release compatibility
- `e5a94b8` (v2.8.1) Merge remote-tracking branch 'origin/main' into feature/stable-launcher
- `40ec0c6` Consume Bundle delivery verdicts
- `b330c8b` Update README to clarify software logic
- `e55df9b` Clarify README operation
- `7a15385` Clarify Blueprint Wizard's systematic offline processing
- `23cf44a` Explain Blueprint Wizard's local parsing model
- `09e08cd` Refocus Runner README on Blueprint Wizard

**Not git repos:** both Downloads/Desktop wizard folders, `OUT`, and the two `brightspace-blueprint-runner-main*` folders.
