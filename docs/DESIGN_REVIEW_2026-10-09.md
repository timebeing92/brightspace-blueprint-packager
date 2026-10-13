# SME and ID authoring design review

## Assessment

The Packager has useful structural and fidelity checks, but its initial blank
asked authors to understand too much of the packaging system while drafting a
course. The most consequential design issue is the division of work: subject
expertise, instructional planning, document syntax, and package configuration
are presented together without enough explanation of who handles each decision.

This review inspected the generator, rendered blank, authoring guide, reader,
readiness checks, joins, relationship report and guided runner. Separate SME and
ID reviews informed the findings. These are expert-review observations and
design recommendations; they are not evidence from a study with new users.

## Findings addressed in the current revision


| Observed issue                                                                        | Consequence for an author                                                                       | Current change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Writing prompts use the same bracket convention as functional commands.               | A reasonable interpretation is that all writing belongs inside the brackets.                    | Ordinary prompt sentences; explicit whole-sentence replacement instructions and a before/after example. Brackets remain for functional features.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Several panel forms share one paragraph separated by vertical bars.                   | Copying the displayed example produces an invalid or confusing combined block.                  | A reference section with one complete example at a time, actual separate paragraphs, purpose, copy boundaries and follow-up instructions.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| The opening introduces syntax and reciprocal relationships before a writing workflow. | SMEs encounter configuration decisions before understanding the task.                           | A draft-one-week, repeat, save and return-for-review sequence. Optional feature syntax moves to the end. Erik Note: this goes a bit too far into telling SME's what to do. I agree that we should distinguish between guidance for designers filling out the blueprint and makig design choices, linking items, etc, and SME interaction and drafting, but I am not sure what that looks like. for now, get rid of the "SME do this" language at the top, and leave the functional (how this works for the ID) but I agree that we need to figure out a balance - ultimatley a doc does not work for this, but a seperate interface is annother undertaking, and still the SME word/google blueprint will always be the intake/ working surface, at least initialy, to some degree. |
| Course-level reference fields resemble fields that become student pages.              | An author may assume the course description or course outcomes have been published.             | Explicit adjacent disclosure that these fields remain document-only unless placed in a course page.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Writing prompts identify a location without explaining the task.                      | Content may omit submission requirements, response expectations or resource purpose.            | Short author notes address overview purpose, observable objectives, task/submission/success criteria, discussion participation and required/optional resources. Erik Note: This goes a bit too far as well (overview and objectives are fine, but some of the discussion and "how it will be judged" in assignments is a bit much.                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Multiple activity blocks run together.                                                | Selecting a complete activity for copying or deletion is difficult.                             | Additional space before each subsequent activity, distinct settings labels, and an explicit copy/delete boundary.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Optional fields and appendices look equally obligatory.                               | Authors may retain sample content or struggle to represent an empty area.                       | Specific omit/remove directions while keeping required structural labels.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Optional design syntax and automatic connections can feel mandatory.                  | Authors may spend drafting time learning features they would prefer to complete in Brightspace. | Welcome optional tokens and shortcuts while explicitly allowing manual styling and connections after import; document how the ID removes unused declarations and tracks deferred work.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| A derived checklist looks like a complete learning-work checklist.                    | Readings, viewing and practice can be omitted from students' plan.                              | Explain its activity-only coverage and how to add other tasks.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| The runner says Ready before it has read the document.                                | Review of run settings can be mistaken for content validation.                                  | Rename that card Review run settings.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

The revision preserves the existing calm palette, ordinary black writing text,
native objective bullets, weekly navigation and exact structural joins. It adds
an explicit Authoring reference section and readable Author note paragraphs;
these remain separately accounted for and never become learner content. Older
bracketed guidance and prompts remain supported.

## Important remaining design decisions

### 1. Reduce repeated relationship information

An activity title can appear in the declaration, Gradebook item, grading plan,
rubric Used by list and internal links. Points also occur more than once. Exact
matching protects fidelity, but every manual change creates coordination work.

Near-term: keep the existing rename preview and provide a readable impact report
organized by week and activity. Longer term: consider a stable activity identity
and one authoritative place for its title and points. That requires an explicit
migration and reconciliation design; visual editing alone will not solve it.

### 2. Distinguish pending assessment decisions from intentional zero

The minimal blank starts with 0 points. A genuine zero-point activity is possible,
and current readiness cannot determine whether a remaining zero is intentional
once the other prompts have been replaced. The template now explicitly asks the
ID to confirm points, but that is a human review instruction.

A future authoring model should distinguish pending, intentionally ungraded and
graded states. Do not reject every zero or silently convert it to ungraded.
Also consider an accepted Graded activity column label alongside the legacy
Assignment label, which currently includes discussion rows.

The broader review also found inconsistent stage messaging: the read-time join
warning said the build would use activity points, while the builder already
requires an explicit determination when values disagree. The warning now asks
for reconciliation or a recorded determination. The capability registry also
clarifies that missing points on a grade-linked activity are an error; there is
no automatic grading-plan fallback. The existing build gate is unchanged.

### 3. Make alignment review a first-class authoring task

Course outcomes, weekly objectives, resources and assessments exist, but explicit
relationships among them are not recorded. A manual review can ask which
objective each activity assesses and whether resources prepare students for it.
Automated coverage claims need stable outcome identifiers, explicit mappings and
an agreed coverage policy. The tool must not infer pedagogical alignment from
similar wording.

### 4. Separate technical and instructional review states

Technical readiness covers supported structural checks and recognized unfinished
fields. It cannot establish appropriate difficulty, accurate subject content,
student workload, accessibility, SME approval or release authorization.

Use a clear human handoff: SME content review, ID design/setup review, learner
preview, and release decision. If these become recorded states, agree the owner
and evidence for each instead of adding generic checkboxes that imply approval.

### 5. Improve recovery and navigation

An ID-facing report should say what to change, where and why in course language:
for example, Week 3 discussion has a title mismatch with its grading row. JSON
reports and paragraph identifiers should remain available as supporting detail.
A single list of unresolved author decisions and a compact activity/points/rubric
summary would support review better than a large count of raw findings.

Avoid using colour alone to communicate a role. Keep explanatory labels and
semantic headings. A more substantial future interface could manage structural
fields separately while retaining DOCX as the SME writing and review surface.
That should preserve explicit author decisions and a reviewable export.

## Suggested division of work


| SME focus                                                   | ID focus                                                         | Tool responsibility                                             |
| ----------------------------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------- |
| Subject accuracy, explanations, examples and learning tasks | Outcome alignment, sequencing, workload and assessment design    | Preserve and account for authored content                       |
| Student-facing instructions and useful resource context     | Points, rubric relationships, placement and calendar decisions   | Validate exact relationships and supported shapes               |
| Review the content as students will see it                  | Review accessibility, media choices and complete package preview | Report technical readiness and verification evidence accurately |

These are suggested responsibilities; one person may perform both roles.

## Next validation

Observe an SME and an ID who have not used the tool perform a short synthetic
walkthrough: write an overview and two objectives; add a second activity; insert
a video placeholder; request a title change; export from Google Docs and resolve
one deliberate error. Record what they select, what they hesitate over and how
they recover. Successful parsing and attractive pages do not establish that the
workflow is intuitive without this observation.

The revised document and parser have local validation. The earlier UNE Google
round-trip evidence remains attached to its earlier template version; this
readable-prompt revision has not had a fresh live Google or tenant test.
