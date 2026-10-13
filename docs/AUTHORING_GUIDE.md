# Writing and editing a Packager blueprint

Updated 2026-10-09 for the unreleased candidate based on v0.2.2.

The blueprint carries structure in native headings, tables, and explicit text
markers so it can be edited in Word or Google Docs. Colour is a reading aid.
Unknown or unplaced authored content is reported as an error.

## 1. Start with a minimal blank or worked example

```bash
python3 bpk.py blank course.docx --course-number "NEW 101" \
  --course-title "Course Title" --term "Spring A 2027" --weeks 8 \
  --assignments-per-week 1 --discussions-per-week 1 \
  --week-count 2:2:1 --week-count 4:0:2
```

`--week-count W:A:D` overrides a week's assignment and discussion counts. This
example gives Week 2 two assignments and one discussion, and Week 4 no
assignments and two discussions. Repeat the flag as needed. Zero counts are
valid; common counts default to one of each.

The minimal blank has visible overview and learning-objective writing areas,
front matter, a grading plan, course pages, six rows per week, and checklists.
Its starter prompts and zero-point entries need author decisions. Fill in
titles, points, content, and relationships before a normal build. Zero itself
is a valid numeric value; the tool cannot infer whether it was intentional.

Add `--worked-example` for a separate example with sample panels and rubric
grids. Sample rubric levels and weights are illustrative choices to review,
not an institutional standard. See the latest
[eight-week UX review copy](examples/blank_blueprint__8_weeks__ux_review.docx).
The [earlier example](examples/blank_blueprint__8_weeks.docx) is retained separately.

Generation refuses to overwrite an existing document. An explicit
`blank --force` backs it up before replacement. Prefer a new filename for a
new offering.

Starting from Blueprint Wizard requires its JSON bundle and the
[`from-wizard` conversion](WIZARD_AUTHORING_CONVERSION.md). The Wizard's review
DOCX is not directly interchangeable with the authoring DOCX.

## 2. Guidance and writing areas

| Visible text | Meaning |
|---|---|
| `Author note: Instructions for the author` | Guidance recorded in source accounting and omitted from learner output. |
| `Write the week introduction here.` | An exact generated writing prompt; replace the entire sentence with ordinary text and add as many paragraphs as needed. |
| `[video placeholder: Week 1 introduction]` | An intentionally pending video location. |
| `Authoring reference` | A reserved frame section containing copyable examples; the whole section stays out of learner output. |

Under **Overview**, keep the `Page:` and `Page heading:` declarations and replace
the placeholder with normal paragraphs. Under **Learning Objectives**, replace
the starter text and use native bullets for each objective. Additional
introductory wording in that area is preserved.

Writing paragraphs use normal text formatting. Put guidance in its own
`Author note: ...` paragraph. Only the exact registered writing-prompt sentences
are marked unfinished; similar authored prose is preserved. Older
`[authoring: ...]` and `[placeholder: ...]` forms remain supported. Ordinary
parenthetical prose is authored content.

The generated first page shows a replacement example and a draft-to-review
sequence. The final reference section groups activity examples, expandable
sections/callouts, and videos/links. Copy only the indicated example lines into
the relevant weekly cell; the examples have actual separate paragraphs.
Instructions for students belong in the body following the activity settings.

### Optional features and manual completion in Brightspace

Designers and SMEs are welcome to use the optional design tokens (dropdowns,
callouts, videos) and shortcuts that connect assignments, grade items, rubrics
and other course objects. Use the features that help you. If you are more
comfortable, write ordinary content and leave styling or connections for manual
completion in Brightspace after import. Record deferred work in **Extraction
Notes** and review it with your designer.

Your designer should remove unused connection declarations and their matching
references before packaging:

- To configure grading later, omit the activity's `Points:` and `Gradebook item:`
  lines and its matching grading-plan row, then update `Total Points`. The
  packaged activity is ungraded until grading is configured in Brightspace.
- To attach a rubric later, omit the activity's `Rubric:` line and remove that
  activity from the rubric's `Used by:` list. An unattached rubric may remain;
  the tool reports it for review.
- Omit optional internal-link tokens if you will add those links in Brightspace.
  Ordinary content does not need dropdown or callout tokens.

Required document structure still applies. Connections explicitly left in the
blueprint must match their targets exactly; a broken reference does not mean
“complete this later.” The Packager does not perform the manual Brightspace work.

Keep weekly label cells to their exact short labels, in this order:
`Overview:`, `Learning Objectives:`, `Assigned Reading and Multimedia:`,
`Assignment(s) and Instructions:`, `Discussion Board Prompts:`, `Checklist`.
The unchanged longer labels in previously generated blueprints are also
accepted. The optional `Students will be able to:` sublabel is accepted in the
learning-objectives label cell. Put authored text in the following content row;
extra prose in a label cell is an error.

Document-only front matter is retained in the model and accounting but does
not automatically become learner-facing pages. Create an explicit `Page:` if
that text belongs in the package.

## 3. Headings, lists, tables, and styling

| In the blueprint | Meaning |
|---|---|
| Title | Document title. |
| Heading 1 | Frame: Course Introduction, Before Week 1, each `Week N - Topic`, Rubric Appendix, Authoring reference. |
| `Page heading:` | The generated page's h1. |
| Heading 2–6 inside content | The corresponding h2–h6. |
| Heading 2 under Rubric Appendix | A rubric name. |

An `Assignment:` or `Discussion:` line declares an object; its instructions may
use Heading 2–6. Do not style activity declarations as top-level frame headings.
A legacy Heading 2 frame is read with an explicitly reported offset.

Use real bullets and numbered lists, real tables for tabular content, and
native bold, italic, and underline. Line breaks remain line breaks. Do not
replace list semantics with typed bullet characters. Tables need meaningful
header rows. Long content rows can span pages; generated grading and rubric
tables repeat their column headers.

Assignment and discussion editor fields use a modest inline style set from
the selected page template. Set `fragment_styles: "plain"` in build settings
when plain semantic HTML is preferred.

## 4. Multiple activities in one week

Duplicate a **complete activity block** inside the weekly assignments or
discussions writing cell:

```text
Assignment: Week 2 Assignment: First Analysis
Points: 20
Gradebook item: Week 2 Assignment: First Analysis
Rubric: Analysis Rubric

Instructions for the first analysis.

Assignment: Week 2 Assignment: Second Analysis
Points: 30
Gradebook item: Week 2 Assignment: Second Analysis
Rubric: Analysis Rubric

Instructions for the second analysis.
```

A new `Assignment:` or `Discussion:` line begins the next object. Put its
header attributes directly after that declaration. A discussion also has a
`Forum:` line. Write the complete desired title, including the week if it
should be displayed. Direct authoring does not infer a week prefix.

For each new graded activity:

1. Add its grading-plan row with matching points.
2. Set `Gradebook item:` to that exact row name.
3. If it uses a rubric, name it and add the reciprocal
   `Used by: Assignment: Exact activity title` or discussion equivalent.
4. Update explicit checklist wording and internal links that refer to it.

Removing an activity requires the corresponding relationship cleanup. The
`__relationships.json` report from `read` identifies declarations and references.
Points disagreements and unresolved exact titles stop a build.

Due days can be stated in prose. Numeric term dates come from the reviewed
build-settings calendar. The runner displays every week boundary so partial
weeks, breaks, and a shortened final week can be corrected.

### Renaming an activity

```bash
python3 bpk.py rename course.docx --kind assignment \
  --old "Week 2 Assignment: First Analysis" \
  --new "Week 2 Assignment: Initial Analysis" --output renamed.docx
```

This previews the rename and writes a ledger. Review it, then repeat with
`--apply --authorized-by "Operator name" --reason "Approved title change"`
to write a new DOCX.

The operation updates exact declarations, matching grade references when they
use the activity title, reciprocal rubric references, and internal-link targets.
A deliberately different grade-item name remains distinct. Narrative wording
and body headings remain authored text; review them yourself when needed.
Existing destinations are protected.

## 5. Panels

Each marker occupies its own paragraph. Every opener needs its closer.

| Block | Short form | Existing long form |
|---|---|---|
| Dropdown | `[dropdown: Title]` … `[/dropdown]` | `Dropdown / expandable section: Title` … `End of dropdown / expandable section` |
| Callout | `[callout]` … `[/callout]` | `Visual cue: Callout` … `End of visual cue` |
| Timeline | `[timeline]` … `[/timeline]` | `Visual cue: Timeline` … `End of visual cue` |
| Styled section | `[box]` … `[/box]` | `Visual cue: Styled section` … `End of visual cue` |

Callouts may use `[callout tone=gold]`, `[callout tone=grey]`, or a colour such
as `[callout color=#336699]`. Unknown tones are reported and use the template
default. Panel content may include paragraphs, headings, lists, and supported
media.

## 6. Links

External hyperlinks need complete web addresses with a hostname. For course
objects, use an explicit bracket:

```text
[link to assignment: Week 2 Assignment: First Analysis | the first analysis]
[link to discussion: Week 2 Discussion: Compare Ideas]
[link to checklist: Week 2 Checklist | this week's checklist]
[link to page: Welcome to NEW 101 | the welcome page]
```

`quiz` is also supported for explicitly carried quiz objects. Titles must
match exactly. Unknown targets are errors. Page links work between generated
course pages; a page link in an activity editor field is reported as an error
when its required resolution path is unavailable.

## 7. Video embeds and placeholders

Put the marker on its own paragraph wherever the video belongs:

```text
[video: Week 1 introduction | https://www.youtube.com/watch?v=VIDEO_ID_11]
[video placeholder: Week 2 demonstration]
```

Replace the example address with a real URL. The title becomes the responsive
iframe's accessible label. The existing `Video embed: Title` form with a native
hyperlink remains accepted; the bracket form accepts a plain pasted URL.

Supported addresses use HTTPS and exact provider hosts:

- YouTube `/embed/VIDEO_ID`, watch links, and `youtu.be` share links with an
  11-character video ID. Supported share-link `t=` values are converted to the
  player's `start=` seconds; other retained player parameters remain in the URL.
- Vimeo `player.vimeo.com/video/NUMBER` and ordinary `vimeo.com/NUMBER` links.
  Keep a required `h` privacy query parameter.

YouTube supports player parameters such as start/end times; Vimeo may require
a privacy hash for an unlisted video. Use the provider's complete player URL
when exact player parameters matter. See the
[YouTube player reference](https://developers.google.com/youtube/player_parameters)
and [Vimeo privacy-hash guidance](https://help.vimeo.com/hc/en-us/articles/12426470858001-Embedded-player-displays-This-video-does-not-exist-message).

A pending video produces a visible placeholder in preview. To retain it in a
normal package, pass `--retain-video-placeholder "Week 2 demonstration"` to
`build`. An unsupported but valid external URL can be explicitly retained as a
link with `--video-link-fallback "Exact video title"`. These choices are recorded
in readiness evidence. Missing or malformed URLs cannot become empty iframes.

Institutional/private providers beyond these URL forms do not yet have automatic
embed support. Provider permissions, domain restrictions, captions, availability,
and tenant playback require separate operator review; local packaging does not
prove playback.

## 8. Checklists and course-level objects

```text
Checklist: Week 3 Checklist
Items: From this week's activities
```

Derived checklists include all of the week's activities. With multiple
activities, generated items include their titles to distinguish them. Authored
items below the declaration are extras. Remove `Items:` and type the complete
list for a hand-authored checklist.

The Before Week 1 table contains labelled object groups. Its label must equal
the first declared object's exact title. Extra authored text in that label cell
is an error; place it in the content row under an appropriate object. A `Module:` declaration
can contain explicit pages, links, and activities. `Placement:` adds an explicit
module destination. A module or link is not a page body: authored text beneath
those declarations is an error. Use a `Page:` object or authoring guidance.

## 9. Rubrics

Each rubric has a Heading 2 name, one `Used by:` line per activity, an optional
description, and its grid. Use percentage level headings and criterion weights
totalling 100%. Keep names exact on both sides of every relationship.

```text
Used by: Assignment: Week 2 Assignment: First Analysis
Used by: Assignment: Week 2 Assignment: Second Analysis
```

The minimal blank does not assume a grading rubric. Worked-example rubrics
must be reviewed and completed before use.

## 10. Read, review readiness, and build

```bash
python3 bpk.py read course.docx --output-dir out --label course
python3 bpk.py build out/course__course_model.json \
  --settings build_settings.json --output-dir build
python3 bpk.py verify build --model out/course__course_model.json
```

`read` produces a model, source-accounting ledger, readiness report, relationship
report, and readable companion. Structural validity and readiness are separate:
an unfinished but structured document can read successfully and still require
content before a normal build.

`build --preview` makes a labelled draft with pending authoring fields. It does
not bypass broken joins, unknown sections, or unaccounted content. Replace
placeholders or record supported retention choices for a normal package.
Verification checks local package evidence, including link destinations and
Wizard QA findings; missing evidence cannot count as a pass.

Re-read existing DOCX files after updating the tool. Older cached models lack
the required source-accounting ledger. Re-reading preserves the source file.

Native image runs and `Embedded image:` markers currently raise
`IMAGE_UNSUPPORTED`; binary image packaging is not implemented. Unsupported
media and other unresolved content require an explicit decision before building.

## 11. Google Docs workflow

Upload the DOCX to Drive, convert it to a native Google Doc, and use pageless
mode if preferred. Preserve table cells, headings, activity declarations, and
bracket paragraphs. Download as Microsoft Word (`.docx`) and run `read` again.

The review exercised upload, pageless mode, native text/heading/list/link edits,
Word export, and local packaging in UNE My Drive. Layout and pagination can
change on export. The [Google authoring QA record](evidence/GOOGLE_AUTHORING_QA_2026-10-09.md)
records candidate comparisons, retained documents, results, and limitations. Review the readiness, accounting, and package reports after
each export.

The readable-prompt/reference revision has local parser, package and rendered
document checks. The preceding Google evidence applies to the earlier bracketed
prompt candidate; this later revision has not had a fresh Google cycle.

## 12. SME and instructional designer review

Technical readiness means that recognized unfinished fields and structural
errors have been addressed. It does not establish learning-outcome alignment,
reasonable workload, accessibility, SME approval, or release authorization.

Before handoff, review the relationship between course outcomes, weekly
objectives and assessed tasks. Check that each assignment explains the task,
submission and success criteria, and that discussions explain both the initial
contribution and interaction expectations. Identify required versus optional
resources, confirm points and rubrics, and inspect the learner preview.

Derived checklists list assignments, discussions and quizzes. Reading, viewing
and practice tasks need explicit extra items. A broader design assessment and
prioritized follow-on recommendations are recorded in
[SME and ID design review](DESIGN_REVIEW_2026-10-09.md).
