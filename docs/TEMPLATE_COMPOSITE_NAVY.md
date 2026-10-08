# Template: composite-navy

Date: 2026-10-07. Status: built and rendered; not the default until the owner
says so. Owner's direction, verbatim: "look at mba 630, bumg 660 in my
projects for styling inspiration - take the best of 515 and those 2 and create
a composite - with the darker navy branding, but minimizing some of the
ostentation (large hero callouts) for the generic builder - we can add
template layer choices later to the packager."

Page surface only. Editor fields (assignment and discussion descriptions) are
plain semantic HTML by default since the same day, by the build setting
`fragment_styles`; this template's optional fragment styles are inert.

## Where each part comes from

| Part | Taken from | Reference |
|---|---|---|
| Single-column skeleton, `header.wrapper` and `main.wrapper`, section rhythm, `hr` separators | BUMK 515 classic | `templates/bumk515_classic/page.css:43-46` |
| Video wrap (16:9), transcript size, back-to-top block, external-link arrow | BUMK 515 classic | `page.css:52-65, 99-124` |
| Timeline markup (`.timeline`, `.stage`, `.label`, `.purpose`) | BUMK 515 classic; the renderer emits these classes | `page.css:126-133`; `html_render.py:374-380` |
| Palette: brand `#174b5c`, brand dark `#103945`, link `#075f7a`, soft `#edf4f6`, strong soft `#e2edf0`, border `#c7d8dc`, soft border `#d9e4e6`, muted `#4b626b` | MBA 630 approved course style contract, "Core course chrome" | `docs/project/MBA630_STYLESHEET_ARCHITECTURE_AND_DIVERGENCE.md:68-79`; `mba630-course.css:14-28` |
| Body text `#1d2935`, Lato stack | MBA 630 | `mba630-course.css:30-37` |
| Top bar above the page header, rule under h2 | MBA 630 page header and h2 | `mba630-course.css:131-139, 184-191` |
| Table header row white on brand, tinted row headers, zebra rows | MBA 630 table wrap | `mba630-course.css:1022-1056` |
| Link weight 600 and underline offset; focus ring `#a55b16` at 3px | MBA 630 | `mba630-course.css:873-905` |
| Headings in brand dark, weight 600, line-height 1.2 | BUMG 660 Week 1 overview | `workspace/Overview Pages-Complete/BUMG_660_Week_1_Overview.html`, style block lines 51-71 |
| `+` / `−` summary marker on dropdowns | BUMG 660 Week 1 overview | same file, style block lines 292-314 |
| Callout as left border plus light tint | all three agree; BUMG 660 lesson template uses a 5px border | `BUMG_660_Lesson_Page_Template.html` style block line 101-104 |

Neither source names a colour "navy". MBA 630's "dark blue" pair is the
darkest blue in the three and is what the owner's phrase was taken to mean;
`#103945` carries headings and `#174b5c` carries bars, borders, markers and
the table header. If a different navy is wanted, the two tokens at the top of
`page.css` are the only place to change it.

## Deliberately left out

- MBA 630's overview hero and resources hero cards (`mba630-course.css:321-357,
  375-431`), their accent bar, the evidence-folder buttons with shadows
  (`:907-937`), `0.65rem` to `0.8rem` radii, and the table-wrap shadow.
- BUMG 660's shadowed 14px-radius dropdown panels and details grid, and its
  eyebrow / subtitle / lede page header.
- BUMK 515's 19px root size and 1.65 line-height, which the owner called out
  ("the line spacing is odd"). This template sets 18px and 1.5, 17px on small
  screens.
- The gradient on the timeline spine and the gradient-free but shadowed stage
  dots; stages are flat.
- Any Page Kit borrowing (see the last section).

## Palette and contrast

Ratios computed with the WCAG relative-luminance formula.

| Pair | Ratio |
|---|---|
| Headings `#103945` on white | 12.40 |
| Body text `#1d2935` on white | 14.78 |
| Body text on soft tint `#edf4f6` (callouts) | 13.28 |
| Links `#075f7a` on white | 7.17 |
| Links on soft tint | 6.45 |
| Visited links `#0f4c61` on white | 9.43 |
| Muted text `#4b626b` on white | 6.44 |
| Muted text on soft tint | 5.79 |
| Table header, white on `#174b5c` | 9.56 |
| Focus ring `#a55b16` on white (non-text, needs 3:1) | 5.11 |

Every text pair clears 4.5:1; the muted-on-tint pair is the closest at 5.79.

## How a course selects it

Build settings: `"template": "composite-navy"`. Nothing else changes. The
renderer's `heading_map` is identity for both templates, so pages keep the
one-to-one heading convention. Rendering the MBA 620 course model with it on
2026-10-07 gave 12 of 12 verification checks and a clean Page Kit gate (12
pages, 0 errors, 0 warnings); the package differs from the classic one only in
the embedded CSS, which is why the ZIP is larger by about 12 KB.

Preview for the owner: `workspace/review/mba_620/sandbox_2026-10/composite_navy_preview/`
in the MBA 620 repository (Week 1 overview, Week 3 overview, Student and Course
Resources, the CSS, and screenshots where the headless browser produced them).

## Waiting on the owner's Page Kit answers

Items 13a to 13e on the response sheet were not baked in. Which would touch
this template, and how:

| Item | Would change here | If taken |
|---|---|---|
| 13a Gate rules as early diagnostics, table header row, link text | Nothing in the CSS; the reader and renderer | No template change |
| 13b Skip link, visible focus outline, print rules, lazy video | `page.css` and the shell: a skip link needs the shell to emit one before the header; print rules are a `@media print` block; lazy loading is an `iframe` attribute in the renderer | The focus outline is already present in the MBA 630 colour; the rest is additive and small |
| 13c Per-page external links in the receipt, provenance comment in each page | The shell's `<head>` would gain an HTML comment; the receipt gains a list | No CSS change |
| 13d Classic template's colours as a Page Kit theme token set | The `:root` block here would be expressed in Page Kit's token names, or generated from a token file | Palette unchanged; naming only |
| 13e The compiler itself | Would replace this template's shell with a Page Kit kit reproducing the same look | Deferred to the template decision |

## Pass 2, 2026-10-08, on the owner's notes after seeing round 1

- A course label above the page title (`package.course_label` in the build
  settings, e.g. "MBA 620 · Marketing"), set in the manner of MBA 630's kicker:
  small capitals, brand colour, letter-spaced. The bar is no longer alone.
- Air under the header rule: the main column starts 1.4rem below it (MBA 630
  uses 1.75rem; a hair less, as asked).
- Type: root 18.5px and line-height 1.6 (MBA 630: 19px and 1.65; a hair under).
  Paragraph spacing 1.1rem.
- Dropdowns: a summary row tinted with the soft brand colour, darker on hover,
  a touch larger (1.06rem, more padding), the arrow marker in line with the
  heading, and the open panel's content indented to the summary's text.
Preview: `workspace/review/mba_620/sandbox_2026-10/style_pass_2_preview/` in the MBA 620 repository.

## Pass 3, 2026-10-08, after the owner saw pass 2 in the sandbox

- Dropdowns are white cards with a soft shadow in the manner of BUMG 660, so
  they read as clickable; no left bar (it ran down the open panel); the summary
  surface is distinct from the callout tint; hover deepens the shadow and the
  summary. Bullets inside a panel sit under the panel's text.
- The focus ring shows only for keyboard focus and sits inside the card; a
  mouse click no longer leaves the orange line Brightspace was drawing under
  the summary.
- "Back to top" is not bold, in this template and the classic one.

