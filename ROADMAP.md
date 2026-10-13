# Roadmap

Updated 2026-10-13. The candidate below was released as **0.3.0** on
2026-10-13 together with the Blueprint Wizard compatibility work and the
release-readiness work (installer revalidation, verified-tag builds, the CI
matrix, the published-asset smoke test); see `CHANGELOG.md`. The approved
scope and implementation decisions are recorded in
[the plan](docs/IMPLEMENTATION_PLAN_2026-10-09.md) and
[the implementation log](docs/IMPLEMENTATION_LOG_2026-10-09.md).

## Implemented in 0.3.0

- Blocking source accounting, input-contract checks, accurate missing-evidence
  handling, internal-link verification, and corrected reader provenance.
- Protected blank generation, configurable weekly activity counts, minimal and
  worked-example forms, clearer writing areas, and revised table pagination.
- Guidance/placeholders, draft readiness, video embeds/placeholders, and
  deliberate retention/link-fallback choices.
- Relationship reports and previewable, authorized structural activity renames.
- Calendar review and editing in the guided runner.
- Explicit Wizard JSON-bundle to authoring DOCX conversion, with source hashes,
  a ledger, and refusal of unsupported shapes.
- Synthetic boundary and complete-cycle regressions. Consult the log for the
  current rendered-document and Google round-trip evidence.

## Next evidence and handoff

1. Tenant validation of the shapes new since 0.2.2: the operator imports a
   representative synthetic package built by 0.3.0 into an empty sandbox,
   checks media and multiple activities, re-exports it, and records a new
   receipt in `docs/IMPORT_RECEIPTS.md`. Until then those shapes are supported
   locally and not tenant-verified. The tool itself does not access a live
   tenant.
2. Promote borrowed-behaviour fixes upstream when a concrete Workbench issue is
   established, then review the diff before re-pinning the vendor.

## Follow-on work requiring its own evidence

- Expand Wizard conversion beyond its documented subset. The retained backlog,
  with what each family needs before it can be supported, is
  [`docs/CONVERSION_BACKLOG_2026-10-13.md`](docs/CONVERSION_BACKLOG_2026-10-13.md):
  dates and term settings, post-first discussions and quiz carry-forward first
  (the demonstrated sandbox blockers), then front matter, media, nested
  modules, grade and rubric variants, checklists, release conditions, and
  rich-text breadth.
- Add institutional video providers using representative URLs, an embedding
  contract, and tenant playback evidence.
- Broaden native Windows interaction evidence beyond path parsing tests.
- Align page design with an upstream Page Kit compiler when its contract is
  settled; two current templates already demonstrate template selection.
- Evaluate structured progress events and receipt evolution against current
  CourseCraft contracts before adopting a new shape.

## Historical work already evidenced

The initial MBA 620 sandbox import, re-export comparison, repeated-import
experiment, and pages-only refresh are in
[Import receipts 10–13](docs/IMPORT_RECEIPTS.md). These are completed historical
rounds, applying to their named packages and shapes. Dates on assignment
folders, checklist items, and a carried quiz have named evidence there too.

## Separate ownership

Quiz authoring remains in the quiz lane. Catalog intake of an authored model,
broader page-design surfaces, and live course operations require their own
scope. Extracted contracts and vendored Workbench files remain immutable here.
