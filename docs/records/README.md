# Blueprint packager records, 2026-10-06

A packet of the reports, findings, and work records behind the blueprint
packager. It travelled with the tool when the tool moved to this repository on
2026-10-08 (copied from the MBA 620 course repository, where it was written).
The course material it cites stays in that repository,
`MBA_620_Marketing_Major_Edit_Fall2026` (private); paths below marked "course
repo" are relative to it. The raw sandbox exports and their snapshots stay
there too.

## Survey reports, kept verbatim

Seven read-only survey passes were delegated during the working session, and an
eighth on 2026-10-07. Each report is preserved as it was returned.

| File | Question it answered |
|---|---|
| `survey_reports/01_upstream_packaging_tooling_survey.md` | What does the upstream Workbench have for turning authored content into a package, and how well is each piece proven? |
| `survey_reports/02_blueprint_wizard_survey.md` | What is Blueprint Wizard today, what format does it emit, and does anything run in reverse? |
| `survey_reports/03_ecosystem_ownership_and_governance_survey.md` | What do the hub's governance documents say about ownership, promotion, and hosting? |
| `survey_reports/04_sibling_course_build_packagers_survey.md` | Which course builds wrote their own packagers or parsers, and which were imported? |
| `survey_reports/05_coursecraft_catalog_exploration.md` | What in the Catalog should a blueprint parser and packager reuse or align with? |
| `survey_reports/06_producer_conventions_and_consolidation_thinking.md` | What does the ecosystem expect of a producer, and what did the earlier consolidation work conclude? |
| `survey_reports/07_mba_date_conventions_and_date_xml_survey.md` | What are the MBA due-day conventions, how did MBA 630 write dates into a package, and which dates survived its import? |
| `survey_reports/08_page_kit_borrowing_pass.md` | What in the Workbench's Page Kit can the packager borrow now, what waits for the template decision, and does anything in it conflict with the packager's rules? Asked for on 2026-10-07, response-sheet item 13. |

`PRODUCER_CONVENTIONS_SUMMARY.md` summarizes the sixth report, its reasoning,
and what the tool did with each point.

## How far to trust them

The reports quote files with paths and line numbers and separate evidence from
inference. These claims were re-read first-hand:

- the ownership split and the six promotion dispositions in `ECOSYSTEM.md`;
- the blueprint bundle's "extraction and review, not instructional-content generation" charter;
- the Course Foundry passage in the July 25 recommendation;
- the component builder's live-import milestone and Receipts 3, 5, and 9 in `docs/IMPORT_TEST_LOG.md`;
- the single-forum limit in `d2l_package_lib.py`;
- the DSW 821 parser, the MBA 630 assembler's use of the upstream library, and its recorded import and repairs;
- the reuse-audit rows for the whole-course object contract;
- the sibling-bundle decision and the standing constraints in the July 19 recommendation.
- promotion record PR-2026-918, including its `promote_new` disposition.

All matched. Everything else in the reports is as reported, not re-checked.

From the seventh report these were checked first-hand before use: the library's
date fields for assignment folders, checklist items, and content links; the
carried quiz's own due date in the template export; and the daylight-saving
offsets, which the packager's tests now assert. The report's central evidence,
that folder and checklist dates survived MBA 630's import and the flat quiz
date did not, is its author's own comparison of that build's files and was not
re-run.

Two corrections belong on the record. The second is in
`VERIFICATION_WITH_UPSTREAM_TOOLING.md`: the first upstream check left four
ignored bytecode cache files in the upstream checkout, since removed.

The first: an early working note blamed the wizard's
"Unplaced Activities" list on a letter-case difference in a link parameter.
Reading the code showed the real cause: placement is credited from week modules
only. The design document and notes carry the corrected finding.

## Other records for the same work

Locations: this repository unless marked "course repo".

| Record | Location |
|---|---|
| `BRIGHTSPACE_REIMPORT_BEHAVIOUR_2026-10-08.md` (here) | What a second import of the same package does in Brightspace, from sandbox round 2; placed in the Workbench's documentation with PR #5 |
| Plan and outcome | course repo `plans/2026-10-06_blueprint_normalization_and_packaging_tool.md` |
| Operator decisions | course repo `logs/DECISION_LOG.md`, five entries dated 2026-10-06 |
| Work log | course repo `logs/WORKLOG.md`, entry dated 2026-10-06 |
| Tooling choice, ownership, hosting, findings for upstream | course repo `docs/project/BLUEPRINT_PACKAGER_TOOLING_AND_OWNERSHIP_NOTES_2026-10-06.md` |
| Tool design and structure vocabulary | `docs/DESIGN.md` |
| Capability list with evidence levels | `CAPABILITIES.json` |
| Tool boundary, roadmap, changelog, tests | repository root |
| Source check and receipts | course repo `workspace/review/mba_620/blueprint_sync_2026-10-06/` |
| Course map with reasons | `workspace/design/mba_620/blueprint_normalization/build_course_map.py` |
| Normalized blueprint, course model, ledger, fidelity proof, run receipt | `workspace/design/mba_620/blueprint_normalization/normalized_2026-10-06/` |
| Reviewer results: issues, joins, change lists | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/` |
| Dropdown review, with the four reviewer passes | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/dropdown_review/` |
| Sandbox package, receipts, object map, verification, runbook | `workspace/generated/import-ready-components/bundles/mba_620_fall_b_2026__sandbox_2026-10-06/` |
| Package read by current upstream tooling | `VERIFICATION_WITH_UPSTREAM_TOOLING.md` |
| Fork drift against upstream, and what it affects | course repo `workspace/review/mba_620/fork_drift_2026-10-06/` |
| Where Blueprint Wizard loses structure: sixteen items, probe, proposed fixes | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/wizard_structure_losses/` |
| Reading links with a tracking tag | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/TAGGED_READING_LINKS.md` |
| What changed between the two exports of 2026-10-06 | `workspace/design/mba_620/blueprint_normalization/course_map__rebase_report.md` |
| Owner responses to the first report | `docs/project/BLUEPRINT_PACKAGER_TOOLING_AND_OWNERSHIP_NOTES_2026-10-06.md`, section 8 |
| The operator's review notes, and what was done with each | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/ISSUES.md` and `ISSUES_NOTES_DISPOSITION.md` |
| Handoff note and the list of build edits | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/HANDOFF_NOTE.md` and `BUILD_EDITS.md` |
| The operator's notes on the wizard losses, and the answers | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/wizard_structure_losses/WIZARD_STRUCTURE_LOSSES.md` and `WIZARD_FIXES_PLAN.md` |
| The wizard fix candidate, its build report, and the real-export comparison | `candidate/blueprint_wizard_structure/` and `wizard_structure_losses/candidate_run/` |
| Term Dates spreadsheet: verbatim extract, receipt, Fall B 2026 check, and a term-calendar proposal | `term_dates/` (`TERM_DATES_EXTRACT.md`, `TERM_CALENDAR_PROPOSAL.md`) |
| The late-afternoon report kept for responses | course repo `workspace/review/mba_620/blueprint_normalization_2026-10-06/REPORT_2026-10-06_FOR_RESPONSE.md` |

## What is not here yet

- A sandbox import receipt and a re-export comparison.
- A promotion record. None has been drafted.
- SME decisions on the issues list and the dropdown review.
