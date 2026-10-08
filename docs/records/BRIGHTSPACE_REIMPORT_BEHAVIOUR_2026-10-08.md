# Brightspace re-import behaviour: what a second import of the same package does

Evidence from the MBA 620 Fall B 2026 sandbox, 2026-10-08. Written to be
placed in the CourseCraft Workbench's project documentation at integration
(owner's instruction: "record as pure documentation in coursecraft upstream,
not just in packages and tooling"). The receipts are in the MBA 620
repository's `docs/IMPORT_TEST_LOG.md` (Receipts 10 and 11) and
`workspace/review/mba_620/sandbox_2026-10/`.

## The experiment

A whole-course package (10 modules, 37 topics, 7 assignment folders, 2 forums
with 8 topics, 8 checklists, 1 quiz, 10 rubrics, 14 grade items, 12 HTML
pages) was imported into an empty sandbox course, re-exported (Receipt 10),
and then a rebuilt package with the same resource codes for the same objects
was imported into the same course without deleting anything (Receipt 11).

## What Brightspace did

| Object class | Behaviour on the second import |
|---|---|
| Modules, topics | duplicated; a page placed in two modules appears four times |
| Course files (HTML pages) | overwritten in place by path; every module pointing at the path shows the new content |
| Assignment folders, discussion forums and topics, checklists, quizzes | duplicated |
| Rubrics | duplicated |
| Grade items | duplicated by name, and the new activities are left unlinked: "Cannot associate grade item to … as the grade item is already in use", one warning per graded activity |
| Resource codes | carried, not matched: the original codes appear once each, some duplicates get newly minted codes, the rest none |

## What follows

1. A package's resource codes do not let a second import update the first.
   Keep them for provenance and for reading a re-export back against the
   build; do not rely on them for identity in the tenant.
2. Page content can be refreshed in place by uploading the `course_pages/`
   folder through Manage Files at the same paths. No other object class can
   be refreshed by import.
3. A built course is updated by deleting the built content and importing
   again, or by an API path. The import log's "already in use" warnings are
   the signature of an accidental double import; a course showing them needs
   the duplicates removed before grading can work.
4. Date stamps come back without their `.000Z` suffix; curly quotes in grade
   item names come back straight. Readers that compare a re-export with a
   build should compare instants and straightened names (Receipt 10).
