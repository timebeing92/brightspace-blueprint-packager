# Blueprint Packager boundary

Its own repository since 2026-10-08 (split from the MBA 620 course build, where
it was born as a downstream proving ground). A producer beside the other
Brightspace bundles; not part of the Workbench, which it builds on.

## It owns

- reading a flat blueprint document into a paragraph stream with stable ids;
- structure-only normalization driven by a reviewable course map;
- the structure vocabulary a packager reads (`blueprint_packager/vocabulary.py`);
- the course model it derives and the joins it checks;
- planning a package from that model and a build-settings file.

## It must never

- edit or delete authored wording. Moves, paragraph styles, mapped removal
  of accidental block bold, heading merges, and carrying or copying a title
  into a structure line are the only operations on authored text, and each is
  recorded per paragraph;
- change wording of its own accord. Wording changes only through entries in
  the course map: an addition, an edit that drops paragraphs or replaces one
  exact stretch of text, or a cloned rubric. Each entry names who authorized it
  and why, and the fidelity proof lists it apart from authored text. An
  assistant must not write such an entry without the operator's explicit
  instruction for that passage, and must list every one for the operator;
- write bytecode or any other file into a Workbench checkout it only reads;
- guess a join. Titles match exactly or the join is an error;
- write into `coursecraft.blueprint/4` or any other extracted contract;
- author quizzes, dates, release conditions, or any object the blueprint does not state;
- import into Brightspace or touch a live tenant;
- claim a package is importable or verified without naming the evidence level;
- carry real course text in tests. Fixtures are synthetic.

## It borrows, and does not own

From the CourseCraft Workbench, vendored under `vendor/coursecraft_workbench/`
at the commit named in its `MANIFEST.json`:

- `scripts/d2l_package_lib.py` and `scripts/rubric_package_lib.py` for payload XML;
- `scripts/check_package_conformance.py`, `scripts/build_blueprint_bundle.py`, and the
  readers it runs, plus `scripts/check_page_conformance.py`, for read-back;
- identity, receipt, and diagnostic record shapes from `scripts/course_artifact_contracts.py`
  and the schema files they load.

Vendored files are never edited here. `python3 scripts/check_vendor_drift.py <workbench
checkout>` shows drift; `--commit <sha>` re-pins every file from upstream, and the
diff is reviewed before it is committed. A change to any borrowed behavior
belongs upstream first; the mirror follows it at the next pin. Which scripts a
run used (vendored, an explicit path, or a checkout) is recorded in every
build receipt and verification report (`blueprint_packager/workbench.py`).

## Checks before handing work back

```bash
.venv/bin/python -m pytest tools/blueprint-packager/tests -q
```
