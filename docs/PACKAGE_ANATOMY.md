# Anatomy of a Brightspace package

Part of [The big picture](BIG_PICTURE.md). A course export and a course import
package are the same kind of ZIP: an IMS Content Packaging manifest with D2L
extensions, plus one payload file per tool area, plus the course's files. What
follows is the whole of that shape, then what each tool here does with each
part ([Who does what](WHO_DOES_WHAT.md) has the tools themselves).

## 1. The ZIP

File names below are the ones the Packager writes and the engine reads; a
real export keeps the course's own folder layout and may number or name
payloads differently. The manifest's `href` is always the authority.

```
course package .zip
│
├── imsmanifest.xml ············· THE INDEX: the content tree and every resource (section 2)
├── orgunitconfig/
│   └── orgunitconfig.xml ······· the course offering: code, name, dates, image
│
│   ── content ──────────────────────────────────────────────────────────────────
├── <folders>/*.html ············ the pages, one file per content topic
├── <folders>/* ················· the course files the pages use: images, PDFs,
│                                 media, stylesheets; any path, referenced relatively
│
│   ── activities ───────────────────────────────────────────────────────────────
├── dropbox_d2l.xml ············· assignment folders ("dropbox" is D2L's old name):
│                                 categories, instructions, dates, grade link, rubric link
├── discussion_d2l*.xml ········· discussion forums and their topics: instructions,
│                                 dates, grade link, rubric link
├── checklist_d2l.xml ··········· checklists, their categories and items, each item's due date
├── questiondb.xml ·············· THE QUESTION LIBRARY: every question, its answers,
│                                 feedback, points, in sections
├── quiz_d2l_<id>.xml ··········· one per quiz: settings, instructions, attempts, dates,
│                                 and which library questions (or random pools) it draws on
├── survey_d2l_<id>.xml ········· surveys, same shape as quizzes without grades
├── selfassess_d2l_<id>.xml ····· self assessments, likewise
│
│   ── assessment plumbing ──────────────────────────────────────────────────────
├── grades_d2l.xml ·············· grade categories, grade items, the gradebook configuration
├── rubrics_d2l.xml ············· rubrics: criteria, levels, points, feedback
│
│   ── course operations ────────────────────────────────────────────────────────
├── syllabus_d2l.xml ············ the syllabus entry
├── news_d2l.xml ················ announcements
├── calendar_d2l.xml ············ calendar events
├── conditionalrelease_d2l.xml ·· release conditions (show X when Y is done)
├── intelligentagents_d2l.xml ··· intelligent agents (if a learner does X, do Y)
├── groups_d2l.xml ·············· group categories and groups
├── lti_link_d2l.xml / lti_tp ··· external learning tool links and providers
├── competencies / outcomes ····· learning outcomes and their alignments
└── awards, attendance, glossary, FAQ, links …  other tool areas D2L can export
```

## 2. The manifest's two trees

`imsmanifest.xml` is two trees. `organizations` is what a learner sees in the
Content tool; `resources` says where each thing lives and what kind of thing
it is. Every item in the first tree points at a resource in the second by
`identifierref`, and the resource's `material_type` attribute (a D2L
extension) is what Brightspace acts on.

```
imsmanifest.xml
│
├── <organizations>                         the content tree, in order
│   └── <organization>
│       ├── <item> Getting Started ........................ ─► RES_CONTENT_M01     contentmodule
│       │   └── <item> Welcome to SYN 101 .................. ─► RES_CONTENT_M01_T01 content → course_pages/welcome-to-syn-101.html
│       ├── <item> Staff Notes ............................. ─► RES_CONTENT_M02     contentmodule
│       │   └── <item> Help Desk ........................... ─► RES_CONTENT_M02_T01 contentlink → https://example.org/help
│       └── <item> Week 1 - Sample Topic ................... ─► RES_CONTENT_M03     contentmodule
│           ├── <item> Week 1 Overview ..................... ─► …_T01 content → course_pages/week-1-overview.html
│           ├── <item> Week 1 Checklist .................... ─► …_T02 contentlink → quickLink?type=checklist&rCode=<base>-900006
│           ├── <item> Week 1 Discussion: Opening .......... ─► …_T03 contentlink → quickLink?type=discuss&rCode=<base>-900003
│           └── <item> Week 1 Assignment: Report ........... ─► …_T04 contentlink → quickLink?type=dropbox&rCode=<base>-900004
│
└── <resources>                             where each thing lives
    ├── res_orgunitconfig    material_type=orgunitconfig       href=orgunitconfig/orgunitconfig.xml
    ├── res_d2lgrades        material_type=d2lgrades           href=grades_d2l.xml
    ├── res_d2lrubrics       material_type=d2lrubrics          href=rubrics_d2l.xml
    ├── res_d2ldropbox       material_type=d2ldropbox          href=dropbox_d2l.xml
    ├── res_d2ldiscussion_1  material_type=d2ldiscussion       href=discussion_d2l_1.xml
    ├── res_d2lchecklist     material_type=d2lchecklist        href=checklist_d2l.xml
    ├── res_questionlibrary  material_type=d2lquestionlibrary  href=questiondb.xml          (when quizzes exist)
    ├── res_quiz_<id>        material_type=d2lquiz             href=quiz_d2l_<id>.xml       (one per quiz)
    ├── …                    d2lsyllabus · d2lnews · lti · d2lintelligentagents · d2lcourseimage · …
    └── RES_CONTENT_*        material_type=contentmodule | content | contentlink
```

The `material_type` values decide everything:

| material_type | Brightspace makes | from |
| --- | --- | --- |
| `contentmodule` | a module (a folder in Content) | the item itself; nested items are its contents |
| `content` | a page topic | the HTML file at `href`, plus whatever that page references |
| `contentlink` | a link topic | `href`: an outside URL, or a `quickLink` into an activity by resource code |
| `d2ldropbox`, `d2ldiscussion`, `d2lchecklist` | the activities | their payload files |
| `d2lquestionlibrary`, `d2lquiz` | the question library, then each quiz drawing on it | `questiondb.xml`, then `quiz_d2l_<id>.xml` |
| `d2lgrades`, `d2lrubrics` | the gradebook and the rubric list | their payload files |
| `orgunitconfig`, `d2lsyllabus`, `d2lnews`, `lti`, … | course settings and the operational areas | their payload files |

## 3. The joins

Nothing in a package is an island. Objects refer to each other by identities
that have to agree across files; a package whose identities disagree imports
with dangling links, silent duplicates, or nothing at all.

```
                        imsmanifest.xml  (organizations)
                                │ identifierref
                                ▼
                        imsmanifest.xml  (resources)
            ┌──────────────┬────┴────────┬──────────────┬────────────────┐
            │ href         │ href        │ quickLink    │ href           │
            ▼              ▼             │ rCode=…      ▼                ▼
     page HTML ─────► course files       │        payload XML      questiondb.xml
     (relative src/href)                 │              │                 ▲
                                         ▼              │  question ids   │
                                   resource code ◄──────┤◄────────────────┘ quiz_d2l_<id>.xml
                                  <base>-9000NN         │  (which questions, which pools)
                                         ▲              │
            grades_d2l.xml ──────────────┤              │
            grade item ◄── activity's grade link        │
                                         │              │
            rubrics_d2l.xml ─────────────┘              │
            rubric ◄── activity's rubric attachment     │
                                                        │
            checklist item ─────► quickLink to the activity it is about
            conditionalrelease ─► the object it gates and the condition it watches
            calendar / dates ───► the activity, the checklist item, the module
```

- **Resource codes** (`<base>-900004` and so on) are minted per object. The
  topic that opens an activity is a quick link carrying the object's code; the
  grade item, the rubric attachment, the checklist item and a release
  condition name the object the same way. Brightspace mints its own codes on
  import; nothing in these tools depends on them coming back.
- **Pages reference files relatively.** An `<img src="…">` or a link inside a
  page is a path inside the ZIP; a broken relative reference is a broken image
  or link in the course. The engine's page gate checks every one.
- **A quiz is two files.** The library holds the questions; the quiz holds
  settings and a list of question references or random-pool rules. They are
  read together or not at all.
- **A rubric is attached, not embedded.** It lives in `rubrics_d2l.xml` and
  the activity's payload names it. A rubric imported on its own (Rubric Loom's
  Weave package) is attached by hand afterwards.

## 4. How Brightspace treats a package on import

Established on the MBA 620 sandbox rounds for the packages named in
`IMPORT_RECEIPTS.md`; the behaviour is Brightspace's, not the tools'.

- **First import into an empty course:** every object arrives, in the order
  and nesting the manifest gives.
- **A second import of the same package duplicates every object** except the
  pages: modules, folders, forums, checklists, quizzes, rubrics and grade
  items all double, and the new activities arrive without grade items.
  Brightspace does not match objects by the package's identities. A built
  course is therefore updated by deleting the built content and importing
  again.
- **Pages are files and files overwrite by path.** Upload the folder inside
  `course_pages_refresh.zip` through Manage Files and every page updates with
  no new objects.
- **A reused course mints fresh resource codes** even after the old objects
  are deleted.

## 5. Who reads and who writes each part

The tools are described in [Who does what](WHO_DOES_WHAT.md). This is the
same ground from the package's side.

| Part of the package | Blueprint Wizard (export → blueprint) | Blueprint Packager (blueprint → package) | Rubric Loom | Quiz Binder | Catalog |
| --- | --- | --- | --- | --- | --- |
| manifest, content tree, modules | reads | **builds** (modules, order, hidden modules and topics) | | | consumes the blueprint JSON |
| pages (HTML) | reads into blocks and segments; QA on page chrome and breaks | **builds** from a template; page-to-page relative links; one page in two modules | | | |
| course files (images, PDFs, media) | reads references | **refuses** images (`IMAGE_UNSUPPORTED`, never silently dropped); video by player URL or visible placeholder; an asset-bearing authoring package is planned (backlog family E) | | Unbind keeps a quiz's image references and files | |
| assignment folders (`dropbox`) | reads | **builds**, joined to grade item and rubric; dates from the term calendar | | | consumes |
| discussions | reads | **builds** forums and graded topics; more than one forum per package | | | consumes |
| checklists | reads | **builds**, including a checklist derived from a week's activities; item due dates | | | consumes |
| grade items and categories | reads | **builds**; the points table must agree with the activities | | | consumes |
| rubrics | reads | **builds** analytic rubrics from the Rubric Appendix and attaches them | **Unravel** reads; **Weave** builds a rubric-only package | | consumes |
| question library + quizzes | reads instructions and settings into the blueprint | **carries** a quiz forward unchanged from a source export; **refuses** to author one | | **Unbind** reads; **Compose** authors; **Rebind** builds one quiz package | consumes |
| surveys, self assessments | outside the blueprint | refuses | | | |
| syllabus | discovers a linked syllabus | the blueprint's front matter names it | | | |
| announcements, calendar | outside the blueprint | dates come from build settings, not a calendar payload | | | |
| release conditions, intelligent agents, groups | outside the blueprint | **refuses** | | | |
| LTI links, Creator+ practices | outside the blueprint | **refuses** | | | |
| outcomes and competencies | outside the blueprint | refuses | | | |

"Refuses" means the build stops with a named diagnostic rather than writing
a package with the thing missing. "Outside the blueprint" means the Wizard
does not model it; the export still carries it.

Next: [Who does what](WHO_DOES_WHAT.md).
