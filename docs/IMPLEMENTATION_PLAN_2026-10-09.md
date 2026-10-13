# Blueprint authoring reliability implementation plan

Status: approved by the operator on 2026-10-09; initial implementation and its
local/Google acceptance checks complete. The subsequent SME/ID authoring revision
has local tests and rendered-document review; its Google round trip remains
separate. See the [design review](DESIGN_REVIEW_2026-10-09.md) and latest log entry.

Baseline: Packager v0.2.2, commit `ecee5cd2eabff870ba7cf8c8205084561e715f5c`;
Workbench pin `2c967f914c352c64e77a1bfb3611bddfc0671d8f`.

## Intended outcome

Generate a blueprint, edit it in Word or UNE Google Docs (including pageless),
export DOCX, inspect, package, and verify without losing authored content.
Support zero, one, or several assignments and discussions per week; clear
overview and learning-objective writing areas; explicit video and placeholder
brackets. Preserve the repo's authored/extracted and upstream/downstream boundaries.

## Work sequence and acceptance

1. Baseline and synthetic reproductions. Record source state, tests, vendor drift,
   document renders, and deviations in the adjacent implementation log.
2. Fidelity, verification, and file protection. Every source paragraph has a
   disposition; excluded authored content blocks a build; missing QA evidence is
   never success; links and reader provenance are verified; malformed input is
   diagnosed; existing authoring files are not silently overwritten.
3. Multiple activities. Repeated complete activity blocks, configurable generation
   counts by week, correct grading/rubric/checklist relationships, clear editing
   guidance, and explicit relationship/rename previews.
4. Blank document UX. Separate guidance and normal-format entry areas, native LO
   bullets, compact reference, optional worked examples, repeat headers, sensible
   widths and long-row pagination; render blank and populated examples.
5. Video authoring. `[video: Title | URL]` and `[video placeholder: Title]` with
   responsive titled players, intentional visible placeholders, diagnostics,
   compatibility with long-form markers, and tested URL handling.
6. Readiness and runner. Draft/preview/ready outcomes, known scaffold and URL checks,
   explicit placeholder retention, course identity, editable calendar preview,
   accurate counts, useful diagnostics, and platform-safe paths.
7. Wizard interoperability. An explicit, source-grounded authoring conversion from
   immutable extracted artifacts; no writes into extracted contracts; semantic
   closed-cycle tests. Borrowed behavior changes belong upstream before re-pin.
8. Integrated evidence and docs. Full tests; synthetic complex course; Word rendering;
   live UNE Google upload/pageless/edit/export/read/build; refreshed guides,
   capability claims, roadmap, development command, and release notes.

## Course correction

Routine implementation decisions within this intent may proceed and are logged.
New findings get a minimal reproduction, affected requirement, decision and proof.
Material changes to syntax, authored meaning, breaking contracts or scope return
to the operator; unaffected work continues. Each phase records its actual evidence
and remaining gaps. Completion is based on acceptance, not task count.

## Boundaries

All fixtures are synthetic. No real course wording is revised. Vendored files
remain untouched. Local evidence is L1, distinct from tenant playback/import and
re-export. No commit, push, publication, release or Brightspace action is included
in this implementation handoff.

## Working ownership

- Primary agent: reader accounting, grammar/media, readiness/contracts, builder,
  CLI/runner, integration, live Google checks, documentation and log.
- Verification agent: verifier, Workbench identity helper, focused regressions.
- Template agent: blank generator, Word layout and multi-activity scaffolds.
- Wizard adapter agent: explicit conversion and closed-cycle regressions.

See [implementation log](IMPLEMENTATION_LOG_2026-10-09.md) for current evidence.
