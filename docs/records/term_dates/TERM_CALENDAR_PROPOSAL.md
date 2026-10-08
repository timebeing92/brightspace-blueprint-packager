# Term calendars for the packager: a proposal from the Term Dates spreadsheet

Date: 2026-10-07. Status: proposal, nothing implemented. Written in answer to the
owner's note on response-sheet item 15: dates stay out of the blueprint, day-of-week
conventions are typed in the body text, and the packager could take a program
selection plus the three due-day conventions (first week, middle weeks, last week)
and compute the rest. Evidence is the extract beside this file; inference is marked.

## What the spreadsheet is

`Term Dates Spreadsheet.xlsx` (SHA-256 `94d730f4…`, 892,661 bytes) is the
institution's term-dates workbook as of Fall 2026. 28 sheets, one per term from
Spring 2020 to Spring 2027 plus two day-of-week pattern sheets. Thirteen old sheets
are hidden. The four current-layout sheets (Spring 2026, Summer 2026, Fall 2026,
Spring 2027) share one shape:

- Row 1 names the terms across three column bands: the A term, the B term, and
  the AB (full-length) term.
- Each band holds one block per program group. A merged label cell names the
  programs and the week count ("EDU / SSWO / MBA / 8 week", "MBS CCL / 7 week",
  "GPH / HCA / HIN", "APN / DCN"), the row above names the schedule ("Monday to
  Sunday Schedule", "Weds to Weds Schedule", "Wednesday to Tuesday Schedule"),
  and the rows to the right read "Week N: start – end".
- Every block has exactly one typed date, the Week 1 start, and every other date
  is a formula from it: Week 1 end is `start+4`, each later start is the previous
  end `+1`, each end is `start+6`, and the last week's end is `start+4`. The
  cached values are present, so the extract needed no recomputation.
- Undergraduate and PBPH blocks, SSWO block seminars, and summer sessions have
  their own patterns further down each sheet. AB terms in spring carry a Spring
  Break row.
- The `Term days` sheet states the same patterns as weekday names with no dates.
  That sheet is the conventions; the term sheets are the conventions applied to
  one seed date.

## Fall B 2026 against the dates the owner supplied

They match, week for week.

| Week | Spreadsheet | Supplied |
|---|---|---|
| 1 | 2026-10-28 to 2026-11-01 | same |
| 2 | 2026-11-02 to 2026-11-08 | same |
| 3 | 2026-11-09 to 2026-11-15 | same |
| 4 | 2026-11-16 to 2026-11-22 | same |
| 5 | 2026-11-23 to 2026-11-29 | same |
| 6 | 2026-11-30 to 2026-12-06 | same |
| 7 | 2026-12-07 to 2026-12-13 | same |
| 8 | 2026-12-14 to 2026-12-18 | same |

The MBA 8-week pattern (Week 1 Wednesday to Sunday, middle weeks Monday to
Sunday, last week Monday to Friday, weeks contiguous) holds for all eight MBA
A and B terms in the 2026 and 2027 sheets. Checked mechanically; the script is
`analyze.py` in the session scratchpad and its output is summarized here.

## The design

Three layers, each owning one thing.

1. **A term registry**, data, keyed by program group and term. It holds week
   tables and nothing about any course. It is generated from the workbook by a
   small script each time the workbook changes, never typed by hand, and the
   receipt records the workbook's hash. Suggested home: the Workbench, as
   institution-level reference data beside the other schemas, because the
   syllabus, the bulk date tool, and the packager all want the same table.
   Inference: the workbook is maintained by academic operations for the online
   programs; the comments in it show two colleagues agreeing dates. Who signs
   off on a registry refresh should be settled with them.

2. **Program conventions**, data, keyed by program group. The due-day rules
   for first week, middle weeks, and last week, for initial posts, responses,
   and assignments, plus the due time and the time zone. For MBA, from the
   owner on 2026-10-06: initial posts Friday (Thursday in the last week),
   responses and assignments on the week's last day (Sunday, Friday in the last
   week), 11:59 p.m. Eastern. These are stable across terms, so they live beside
   the registry, and a build can override any of them.

3. **The build**, which names a program group and a term and gets a calendar.
   The blueprint carries no dates. Its body text says "due Sunday" or "initial
   post due Friday" in words, as the owner wants, and the packager checks that
   prose against the computed day and warns on a mismatch, as it does today.

### Registry entry, as derived for MBA Fall B 2026

```json
{
  "term": "Fall B 2026",
  "programs": ["EDU", "SSWO", "MBA"],
  "schedule": "Monday to Sunday",
  "week_count": 8,
  "start": "2026-10-28",
  "end": "2026-12-18",
  "weeks": {"1": ["2026-10-28", "2026-11-01"], "2": ["2026-11-02", "2026-11-08"],
            "3": ["2026-11-09", "2026-11-15"], "4": ["2026-11-16", "2026-11-22"],
            "5": ["2026-11-23", "2026-11-29"], "6": ["2026-11-30", "2026-12-06"],
            "7": ["2026-12-07", "2026-12-13"], "8": ["2026-12-14", "2026-12-18"]},
  "breaks": [],
  "source": {"workbook_sha256": "94d730f4…", "sheet": "Fall 2026 (with dates)", "block": "row 3, B term band"}
}
```

### Program conventions, MBA

```json
{
  "program": "MBA",
  "timezone": "America/New_York",
  "due_time": "23:59",
  "rules": {
    "assignment":          {"first_week": "last_day", "middle_weeks": "last_day", "last_week": "last_day"},
    "discussion_initial":  {"first_week": "Friday",   "middle_weeks": "Friday",   "last_week": "Thursday"},
    "discussion_response": {"first_week": "last_day", "middle_weeks": "last_day", "last_week": "last_day"}
  },
  "source": "operator, 2026-10-06"
}
```

The three-phase form is the owner's own framing. It matters most in Week 1,
which starts on a Wednesday: a Monday rule would have no date there, and today
the calendar module raises an error for that case. A first-week slot gives the
rule somewhere to say what happens instead.

### Build settings fragment

```json
"calendar": {
  "program": "MBA",
  "term": "Fall B 2026",
  "registry": "workspace/reference/schemas/calendar/term_calendars.json",
  "conventions": "workspace/reference/schemas/calendar/program_conventions.json",
  "overrides": {
    "Week 8 Discussion : The Executive Review": {"discussion_initial": {"day": "Wednesday"}, "discussion_response": {"day": "Friday"}}
  }
}
```

The current form, an explicit `weeks` table in the build settings, stays valid.
Naming a program and term is a second way to fill the same table. The receipt
records which way was used, the registry hash, the resolved week table, and
every rule after overrides, so a reader of the package never needs the registry
to know what was built.

### What changes in `calendar.py`

Small. A constructor that takes a registry entry and a conventions record and
produces today's spec (`timezone`, `weeks`, `due_time`, `rules`, `overrides`).
Rules gain the three-phase form; `last_week_day` keeps working as the old
spelling of `last_week`. `due()` picks the phase from the week number: 1, the
maximum, or anything between. Everything downstream, the dropbox, checklist,
quiz, and manifest dates, is untouched. Inference: a day's work including tests.

### Deriving weeks without the workbook

Not recommended as the primary route, but the patterns are simple enough to
state. Given a schedule pattern, a week count, and the Week 1 start:

- Monday to Sunday (EDU, SSWO, MBA, MBS, CCL): Week 1 is start to start+4;
  each later week is the next day through +6; the last week ends on start+4.
- Wednesday to Wednesday (GPH, HCA, HIN): each week is start+7(k−1) to
  start+7k, ends overlap by design; the last week ends on the Friday.
- Wednesday to Tuesday (APN, DCN): each week is start+7(k−1) through +6; the
  last week is Wednesday to Friday.

A build could name `pattern`, `weeks`, and `start` for a term the registry
lacks, and the receipt would say the table was derived rather than registered.
Spring Break only appears in AB terms, which the 8-week programs do not use.

## What does not change for MBA 620

The sandbox package keeps the Fall B 2026 dates already in it, which this
workbook confirms. The build settings keep the explicit `weeks` table. The
blueprint keeps weekday words, not dates, in its text.

## Draft registry

A draft registry generated from the four current-layout sheets is in the
session scratchpad at `term_registry_draft/term_calendars.draft.json`: 43
entries, 8 of them MBA A and B terms from Spring 2026 to Spring 2027. It was
derived by `registry.py` in the scratchpad from the CSV extract, not from the
workbook directly. It is a draft because three program labels came out
imperfectly ("APN/DCN//end date" absorbed a neighboring label; the summer
12-week undergraduate block has no program label of its own). A registry worth
checking in should be regenerated with those two label rules fixed and the
result read against the workbook once by a person.

## Open points for the owner

- Who owns the registry refresh, and whether the workbook's owner would rather
  export it than have it read.
- Whether Week 1's shortened span changes any MBA convention, or Friday simply
  stands.
- Whether the syllabus, which the workbook says should carry week dates, should
  be generated from the same registry.
