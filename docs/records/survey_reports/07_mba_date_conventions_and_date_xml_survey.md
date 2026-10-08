# MBA date conventions and Brightspace date XML: findings from MBA 630 and related exports

Only one sibling MBA build exists: `/Users/ehanson8/Documents/MBA_630_Financial_Management_Course_Build` (the other "MBA" entries in `/Users/ehanson8/Documents` are loose media and notes files). Short paths below are relative to that root, abbreviated `M630/`. The MBA 620 template export you pointed to is abbreviated `M620-export/`.

**Headline:** dropbox due dates and checklist item dates survived the real import. Quiz due dates did not, and were re-entered in the tenant. Discussions carry no native dates in any MBA export.

## A. Due-day conventions

**MBA 630 (documented rule).** Time is 11:59 p.m. Eastern (`America/New_York`) for everything.
- `M630/workspace/design/faculty_guide/mba_630_faculty_course_guide_2026-08-27.md:132`: "Week 1 begins Wednesday and Week 8 ends Friday. All deadlines are 11:59 p.m. ET." Lines 136–143 give the week table.
- `M630/plans/2026-08-25-integrated-creatorplus-course-package.md:42-43`: "All instructional deadlines are Eastern time. Week 8 uses its supplied Friday endpoint, October 23, for end-of-course deadlines."
- **Assignments:** Sunday of the week; Week 8 is Friday (`mba630_full_course_object_contract.json:152-179`, `week_2_sunday_2359_et` … `week_8_friday_2359_et`).
- **Quizzes:** Sunday (same file, lines 95–131).
- **Week 1 intro discussion:** initial post Friday, responses Sunday (`…/engagement_01_health/student_experience/native_brightspace_object_copy.md:21-22`).
- **Two-week roundtables:** initial post Sunday of the odd week, responses Sunday of the even week, Week 8 responses Friday (contract lines 198–203).
- **Health roundtable exception:** initial Wednesday of Week 2, responses Friday of Week 2 (`M630/plans/2026-08-24-full-course-regeneration-and-package-contract.md:37-39`).
- **Checklists:** the checklist object has no due date; only discussion-milestone items are dated.

**Other MBA shells (observable in data only; no written rule found).** I converted the UTC values to Eastern.

| Activity | BUMK 515 Fall B 2025 (`M620-export/checklist_d2l.xml`, `dropbox_d2l.xml`) | Legacy BUFI 510 (`M630/workspace/archive/repo-curation/2026-07-27/legacy_bufi_510/D2LExport_102527_BUFI-510-TEMPLATE_202661635.zip`) |
|---|---|---|
| Week 1 initial post / responses | Fri / Sun | Fri / Sun |
| Mid-term initial post / responses | Thu / Sun (Weeks 2–7) | Fri / Sun |
| Week 8 initial post / responses | Wed / Fri | none dated |
| Assignments | Sun 23:59:59 | Sun 23:59:59 |
| Week 8 assignments | final presentation Thu; "Course Check In" Fri | Fri |
| Quizzes | Week 1 quiz Sun 23:59:59 | not checked |

BUMK 515 anomalies: Group Contract is due Monday Oct 27; the Week 3 response item is `2025-11-09T18:21:00`; Week 5 has no response item.

**Inference:** the stable rule across MBA builds is Sunday 11:59 PM ET, Friday in Week 8, and a Friday initial post in Week 1. The mid-week initial-post day varies by course (Thu, Fri, or course-specific), so confirm it with the designer.

## B. Term calendar

File: `M630/workspace/design/brightspace_packages/mba_630_full_course/mba630_fall_a_2026_package_spec.json:10-43`.
```json
"calendar": {
  "timezone": "America/New_York",
  "weeks": { "1": ["2026-09-02", "2026-09-06"], … "8": ["2026-10-19", "2026-10-23"] },
  "milestones": {
    "intro_initial": "2026-09-04T23:59:00-04:00",
    "quiz_1": "2026-09-06T23:59:00-04:00",
    "assignment_northpoint": "2026-10-23T23:59:00-04:00"
```
- Objects point to a milestone key, e.g. `"due": "assignment_health"`; checklists use `"dates": {"1": "intro_initial", "2": "intro_responses"}` (item index to milestone, lines 94–101).
- There is no code that maps "Week N + weekday" to a date. The builder reads only `spec["calendar"]["milestones"]` (`M630/scripts/build_mba630_fall_a_2026_package.py:612`, `886`); `weeks` and `timezone` are never read.
- The contract's symbolic refs such as `week_2_sunday_2359_et` are not resolved by any script. **Inference:** the absolute milestones were written by hand from the operator-supplied calendar.

## C. XML representation

**Conversion** (`build_mba630_fall_a_2026_package.py:288-292`):
```python
def utc_value(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp has no UTC offset: {value}")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
```
- The package format is UTC, `2026-09-14T03:59:00.000Z`. Brightspace re-exports it as `2026-09-14T03:59:00` (still UTC, no `Z` or milliseconds).
- The offset comes from the hand-typed string. Fall A was entirely EDT, so every value is `03:59Z` the next day.
- Fall B 2026 crosses the daylight-saving change on Sunday Nov 1: Sat Oct 31 23:59 becomes `2026-11-01T03:59:00.000Z`, and Sun Nov 1 23:59 becomes `2026-11-02T04:59:00.000Z` (I computed these with `zoneinfo`).
- BUMK 515 shows both forms in one term: `2025-10-31T03:59:00` and `2025-11-03T04:59:00`.

**Literals from the generated package** (`M630/workspace/generated/import-ready/mba_630_fall_a_2026_2026-08-25_creatorplus/package/`):
- **Dropbox** (child of `<folder>`, after `<instructions>`): `<date_due>2026-09-14T03:59:00.000Z</date_due>`. No start or end was written.
- **Checklist item:** `<item sort_order="1" in_schedule="true" resource_code="MBA630-FALLA-2026-20260825-900034">` … `<date_end>2026-09-05T03:59:00.000Z</date_end>`. Undated items get `in_schedule="false"`. The checklist object itself has no date.
- **Quiz:** `<d2l_2p0:date_start />`, `<d2l_2p0:date_end />`, `<d2l_2p0:date_due>2026-09-07T03:59:00.000Z</d2l_2p0:date_due>`, `<d2l_2p0:has_schedule_event>yes</d2l_2p0:has_schedule_event>`.
- **Content topic** (attribute on the manifest `<item>`; quiz and dropbox links only): `date_due="2026-09-14T03:59:00.000Z" resource_type_key="D2L.LE.Dropbox.Dropbox"`.
- **Modules:** no dates.
- **Grade items:** `<item id="401" identifier="700001" dates_in_calendar="false" …>`, with no date elements.
- **Discussion forum and topic:** no date, lock, or calendar fields at all.

**Not found in any export reviewed:** dropbox start/end, quiz start/end values, discussion start/end/lock/due, or module/topic start/end. I checked the three MBA 630 live exports, the final zip, `M620-export/`, and the legacy BUFI 510 zip.

**Native quiz shape in real exports** (`M620-export/quiz_d2l_144006.xml`):
```xml
<d2l_2p0:date_due><d2l_2p0:timestamp><d2l_2p0:month>10</d2l_2p0:month><d2l_2p0:day>27</d2l_2p0:day><d2l_2p0:year>2025</d2l_2p0:year><d2l_2p0:hour>3</d2l_2p0:hour><d2l_2p0:minutes>59</d2l_2p0:minutes><d2l_2p0:seconds>59</d2l_2p0:seconds></d2l_2p0:timestamp></d2l_2p0:date_due><d2l_2p0:has_schedule_event>no</d2l_2p0:has_schedule_event>
```

## D. Library support

File: `/Users/ehanson8/Documents/MBA_620_Marketing_Major_Edit_Fall2026/scripts/d2l_package_lib.py`. It is byte-identical to the upstream copy MBA 630 imported from `/Users/ehanson8/Documents/D2l & Coursebuilding Tools /coursecraft_workbench/scripts/`.

| Function | Date keys read | Lines |
|---|---|---|
| `build_dropbox_xml` | `folder["date_due"]` | 305–306: `if folder.get("date_due"): ET.SubElement(folder_el, "date_due").text = folder["date_due"]` |
| `build_checklists_xml` | `item["date_end"]` | 375: `"in_schedule": "true" if item.get("date_end") else "false"`; 382–383 write `<date_end>` |
| `build_manifest_xml` | `entry["date_due"]` on any module entry | 460–461: `extra["date_due"] = entry["date_due"]` |
| `build_grades_xml` | none | 179 hard-codes `"dates_in_calendar": "false"` |
| `build_discussion_xml` | none | 310–351 |

- **No date support in the library:** discussions, grade items, modules, start/end on anything, and quizzes (there is no quiz serializer, only `quiz_link`).
- **What MBA 630 wrote itself:** only the quiz dates, in `build_mba630_fall_a_2026_package.py:881-895`:
```python
            if name == "date_due":
                node.text = milestones[quiz["due"]]
            elif name == "has_schedule_event":
                node.text = "yes"
```
- The builder passed library keys at line 686 (`"date_due": milestones[row["due"]]`), 693–702 (checklist `date_end`), and 729–735 and 746 (manifest `date_due` for quiz and assignment links).
- It wrote no discussion dates.

## E. Import evidence

**Not found:** any import log or repair note about dates, calendar, or time zones. I searched `M630/plans/`, `logs/DECISION_LOG.md`, `COURSE_BUILD.md`, `REUSE_RESIDUE_ROSTER.md`, `docs/`, and `workspace/review/mba_630/`. The validation report still lists the gate as open: "Import into the target Brightspace shell and re-export to verify native joins and dates."

What follows is my own comparison of the package against the re-exports, matched by resource code.

First post-import export, `M630/workspace/exports/unpacked/mba_630_live_2026-08-26_202682631/`:
- **Dropbox survived:** `<date_due>2026-09-14T03:59:00</date_due>`, and the manifest item kept `date_due="2026-09-14T03:59:00"`.
- **Checklist survived:** `in_schedule="true"` … `<date_end>2026-09-05T03:59:00</date_end>`.
- **Quiz due dates were lost on all five:** `<d2l_2p0:date_due /><d2l_2p0:has_schedule_event>no</d2l_2p0:has_schedule_event>` (`quiz_d2l_171592.xml`, same resource code `ce720c92-…`). The manifest quiz item has no `date_due`.

Later exports (`mba_630_live_2026-08-27_202682743`, `…202682845`, and `M630/workspace/exports/raw/D2LExport_102527_BUFI-510-TEMPLATE_20269120 (1).zip`):
- Quiz dates are present in the nested-timestamp form. Four have seconds 59; Quiz 3 has seconds 0.
- Dropbox dates changed from `03:59:00` to `03:59:59`.
- The shell's pre-existing Academic Integrity quiz moved from `2025-09-01T03:59:59` to 2026-09-07 03:59:00.
- `has_schedule_event` stayed `no`.
- **Inference:** these were manual tenant edits. No note records it.

Whether the nested `<d2l_2p0:timestamp>` form imports correctly is untested here.

## F. Other things to know

- **Discussion deadlines live in checklist items and prose, not on topics.** Plan `2026-08-25-integrated-creatorplus-course-package.md:123-126`: "The ten discussion milestones remain scheduled because the discussion topics do not carry separate native due dates. Quiz and assignment checklist items remain unscheduled so they do not duplicate the dates on their native activities in Calendar."
- **Only due dates were used, never start or end.** Quizzes are "always available"; `mba_630_native_quiz_package_build_2026-08-24.md:93-94`: "A due date should not close or hide an otherwise always-available quiz."
- **A planned availability date was never emitted.** The contract has `"availability_start_ref": "week_1_sunday_0000_et"` (line 52) for the Health roundtable, but nothing wrote it and no export shows it.
- **No date-based release conditions.** The contract has `"release_conditions": []`; the final export's conditions are Academic Integrity quiz gates.
- **Student-facing text uses relative wording**, e.g. "Due: Sunday of Week 2 by 11:59 p.m. ET". The validator rejects hard-coded dates in checklist labels and descriptions (`M630/scripts/validate_mba630_fall_a_2026_package.py:491-492`, `508`).
- **Seconds differ by source.** The package wrote `:00`; UI-entered dropbox and quiz dates are `:59`; checklist items are `:00` everywhere.
- **Objects kept from the shell hold stale prior-term dates** (the Academic Integrity quiz) and need manual updating.
- **Turnitin:** imported dropboxes export with "Dropbox was imported from course package, and is deactivated until manually enabled."
- **MBA 630's milestones hard-code `-04:00`.** For Fall B, derive the offset per date with `zoneinfo` instead.
