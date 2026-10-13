# Wizard extraction to editable authoring blueprint

The Wizard's DOCX is a review document. To return an extracted course to the
Packager, use the explicit conversion of its JSON bundle:

```bash
.venv/bin/python bpk.py from-wizard path/to/course__blueprint_bundle \
  --output path/to/course__authoring.docx
```

The adapter reads the extracted contracts without changing them. It writes a
native Packager authoring DOCX and a sibling `course__authoring.conversion.json`
report. Keep the report with the document: it records source paths and SHA-256
hashes, the conversion dispositions, original extraction diagnostics, warnings,
and unresolved evidence. Output must be outside the extraction bundle.

An existing output or report is protected unless `--force` is explicit. A
blocked conversion writes a report and does not publish a new DOCX. With
`--force`, a previously existing DOCX remains untouched if conversion is blocked;
the new report clearly has `output_path: null` and `status: blocked`.

## Supported evidence

The bundle uses the following files, with exactly one per applicable role:

| Contract | Supported schema |
|---|---|
| `*__blueprint.json` | `coursecraft.blueprint/4` or `/5` |
| `*__course_activities.json` | `coursecraft.activities/1` |
| `*__course_structure.json` | `coursecraft.structure/1` |
| `*__rubrics.json` | `coursecraft.rubrics/1` |

Wizard omits the rubrics file for a course without rubric payloads. That absence
is accepted only when the activity contract has no rubric associations and one
`*__inventory.json` proves there is no rubric payload in the package. The
inventory is hashed and the rubric role is explicitly recorded as not
applicable. Missing rubric evidence for a package that contains or references
rubrics blocks conversion.

The supported course shape includes:

- Flat top-level modules, including hidden non-week modules and external links.
- Weeks with the `Week N - Topic` frame and an unambiguous extracted overview.
- Course pages with explicit page titles, page headings, and module placement.
- Zero or multiple assignments and discussions in each week, and course-wide
  activities. Resource identities join activities to their manifest placements.
- Numeric grade items, exact grade joins, analytic rubrics with stated criterion
  weights and percentage levels, and exact reciprocal rubric relationships.
- One checklist per week, with the extracted item wording made explicit. A
  previously derived checklist becomes a materialized item list because the
  extraction does not retain the original authoring rule.
- Paragraphs, headings, bullets, numbered items, supported tables, dropdowns,
  visual cues, rich-text runs, external links, and extracted video embeds.

The adapter translates package-local activity/page links back into explicit
authoring link markers when their resource identity or exact page address
resolves. Unresolved local addresses block conversion.

The output is read back by the Packager and its joins are checked before the
DOCX is published. This is local authoring evidence; it does not demonstrate a
new Brightspace import or video playback in a tenant.

## Missing and unsupported evidence

The adapter must not invent missing authored text. If the package did not
contain the document-only course description, required materials, or course
learning outcomes, their absence is recorded as a warning. Recover those fields
from the authoritative authoring source if they are needed. Settings absent
from the extraction cannot be reconstructed.

The following require a separate explicit representation and currently stop
conversion rather than disappearing from the returned document:

- Quiz carry-forward sources, release conditions, or extracted activity dates.
- Nested modules, module descriptions, hidden weekly modules/overviews, and
  unsupported manifest objects.
- Moderated/post-first discussion settings and forum descriptions.
- Nonstandard submission types, special grade types/categories/bonus settings,
  and multiple rubrics attached to one activity.
- Rubric scoring that cannot be represented by criterion weight × level
  percentage, and overall-level feedback or descriptions.
- Images, attached binary files, Creator+ practice blocks, unsupported embeds,
  and other blocks without an explicit conversion rule.
- Multiple checklists per week, unplaced checklists, and checklist categories
  beyond the supported item list.
- Ambiguous identities, inconsistent extraction runs, unresolved joins, or
  authored text present only in an inconsistent alternate Blueprint view.

Empty decorative dividers and the exact generated `↑ Back to top` navigation
are recorded separately because the page template recreates that presentation.
The document preserves the supported extracted semantics; extraction and
re-rendering may change typography, colour details, list representation, and
other presentation that is not retained by the extracted contracts.

Review all warnings and the retained extraction diagnostics before editing or
building the returned document. A successful conversion does not certify the
completeness of the original extraction.

## Regression evidence

`tests/test_wizard_authoring.py` exercises an actual synthetic closed cycle:

1. Build a course containing two assignments and two discussions in one week,
   two rubrics, 140 points, hidden resources, explicit checklist items, a video,
   rich text, and hyperlinks.
2. Run the pinned Wizard against the package.
3. Convert the immutable extraction bundle to authoring DOCX.
4. Read the DOCX, check joins, and compare course content and relationships.
5. Build a second package and run the Wizard again.
6. Compare the extracted content and rubric evidence between generations.

Other tests verify refusal of unsupported semantics, mismatched runs, missing
contracts, source-view discrepancies, invalid rubric scores, and overwrites.
The suite includes a rubric-free package cycle and concurrent output-file
conflicts; an unforced publication never overwrites another writer's file.
All fixtures are synthetic. No course-owned text or live tenant action is used.
