# Page Kit: a borrowing pass for the blueprint packager

Date: 2026-10-07. Asked for by the owner on response-sheet item 13: "you can do
a pass through for use now, and for possible future use."

Roots (read-only; nothing in `U` was written, run from inside, or compiled;
the one probe used `-B` and `PYTHONDONTWRITEBYTECODE=1` and wrote to the
scratchpad):
- `U` = `/Users/ehanson8/Documents/D2l & Coursebuilding Tools /coursecraft_workbench` at `316039f` (`main`)
- `F` = `/Users/ehanson8/Documents/MBA_620_Marketing_Major_Edit_Fall2026`
- `P` = `F/tools/blueprint-packager/blueprint_packager`

**Bottom line:** Page Kit is a page compiler with a gate, a token theme, a
typed block vocabulary, and a lifecycle. The gate is already borrowed. Four
more things are cheap to take now because they are rules or CSS, not
architecture: the skip link and focus outline, a print rule, the gate's
remaining checks turned into packager diagnostics where the packager has the
information earlier, and the receipt's per-page `external_links` list. The
rest is the kit model itself, which only matters once page design is taken up.
Nothing in Page Kit contradicts the one-to-one heading convention adopted
today; the gate accepts it.

## 1. What Page Kit is

Page Kit is an experimental Workbench capability
(`U/docs/project/PAGE_KIT_MODULE_ASSEMBLY_METHOD.md:3-5`): a compiler that
reads a kit (`coursecraft.page_kit/1`), page instances (`coursecraft.page/1`),
and a module composition (`coursecraft.module_composition/1`) and emits
Brightspace HTML topics in two modes, `review` and `learner`
(`U/scripts/page_kit.py:42`, `:783-851`). It owns the page-level contracts, a
scoped stylesheet (`U/workspace/reference/templates/brightspace-course-pages/page-kit.css`,
276 lines), a conformance gate (`page_kit.py:374-416`, CLI
`U/scripts/check_page_conformance.py`, 62 lines), a build receipt
(`coursecraft.page_build/1`) and an adapter into the component package builder
(`U/scripts/build_page_package.py`, 185 lines). It does not author native
objects (`METHOD.md:125-129`). Its code last changed in `272c7b1` on
2026-09-02; the capability landed in `67054e3`. It generalizes the RCORP
module-page candidate of 2026-08-17 and has one operator-reported import at
L3 with the L4 re-export comparison still open
(`U/docs/project/PAGE_KIT_ROUND_TRIP_HANDOFF_2026-08-17.md:5-11`). Tests: 13 in
`U/tests/test_page_kit.py`. This fork carries the same three scripts; only
`page_kit.py` differs, by one Creator+ path rule (18 diff lines; the fork drift
report already records it).

## 2. Borrow now

What the packager renders today, for comparison: a page shell with `lang`,
viewport, inlined CSS, one `<h1>`, `<main role="main">`, and a back-to-top
link (`P/html_render.py:389-405`); external links open in a new window with an
arrow marker (`P/html_render.py:252`, `P/templates/bumk515_classic/page.css:116`);
dropdowns as `details`/`summary`; tables as `td` only
(`P/html_render.py:379-386`); fragments with inline styles
(`P/templates/bumk515_classic/template.json:39-52`).

| Item | In Page Kit | What it adds or replaces in the packager | Surface | Shape | Cost |
|---|---|---|---|---|---|
| Skip link to main content | `page_kit.py:833-834`; CSS `page-kit.css:15-26` | The shell has `<main>` but no skip link. Add one line to `_shell` and the two CSS rules to the template | page | copy a rule | minutes |
| Visible keyboard focus | `page-kit.css:45-53` (3px outline, offset, on links and `summary`) | The template has only `a:focus { text-decoration: underline }` (`page.css:110`), and nothing for `summary` | page | copy a rule, with the template's colors | minutes |
| Print rules | `page-kit.css:262-276` (hide chrome, force `details` open, avoid breaks inside callouts) | None today. Students print week pages; dropdowns print closed | page | copy a rule | minutes |
| Gate checks as early diagnostics | `page_kit.py:386-414`: `H1_COUNT`, `HEADING_LEVEL_JUMP` (warning), `DUPLICATE_HTML_ID`, `IMAGE_ALT_MISSING`, `IFRAME_TITLE_MISSING`, `LINK_HREF_MISSING`, `UNSAFE_HTML_TAG`, `INLINE_EVENT_HANDLER`, `JAVASCRIPT_URL`, `DISCLOSURE_SUMMARY_MISMATCH`, `PLACEHOLDER_LEAK` | The gate runs after the build, on pages only. The packager knows the same facts before rendering, for fragments too: an image run without a description, a dropdown without a title, a heading jump, an empty link. Raise them in the reader or renderer with the paragraph id, so the author sees where. Keep the gate as the independent check | page and editor field | copy the rule set, not the code | half a day, with tests |
| Per-page `external_links` in the receipt | `page_kit.py:418-422`; recorded per page at `:878+` (`"external_links": external_links(raw)`) | The object map lists link cleanups but not every outbound address per page. A per-page list gives the link check before import one place to read | page and editor field | adopt a receipt field | an hour |
| Determinism marker | `page_kit.py:817-821`: a generated-by comment with schema, page id, mode, and source hashes | The packager's pages carry no provenance line; its receipt does. A one-line HTML comment with the page id and the source blueprint hash makes a re-exported page traceable to its build without the receipt | page | copy a convention | minutes |
| Video shell | `page_kit.py:734-744`, `page-kit.css:139-154` (`loading="lazy"`, 16:9 shell) | The packager already has an equivalent (`P/html_render.py:362-377`). Only `loading="lazy"` is missing | page | copy an attribute | minutes |
| The two-mode idea | `page_kit.py:42-43`, `REVIEW_ONLY_KINDS` | A review build that shows per-block origin (`page_kit.py:706-713`) next to the content. The packager has the readable companion and ledgers instead. Not needed now; see section 3 | page | none now | none |

Not in Page Kit, so not borrowable: link-text checks ("click here" passes the
gate; probed), table semantics (`th`, `scope`, `caption`; the gate has no
table rule and the kit renders tables only through `raw_html`,
`page_kit.py:776-777`), and color contrast (tokens are free hex strings,
`page_kit.schema.json:132`). The packager's `td`-only tables are therefore
unchecked on both sides. Inference: a header-row rule belongs in the
packager's own diagnostics, since the blueprint knows which row is the header.

## 3. For later

The three shapes recorded in `P/../docs/DESIGN.md` ("Open direction: template
selection") and what each would take from Page Kit.

| Shape | What Page Kit supplies | What it would require |
|---|---|---|
| One choice, applied broadly (BUMK 515 classic now) | The theme token set as a contract: eleven named colors, `#rrggbb`, validated (`page_kit.schema.json:93-131`); applied as CSS custom properties on the page root (`page_kit.py:701-703`) | Express the classic template's five variables (`page.css:10-16`) as a kit theme, so a second course changes colors without forking CSS. Layout stays. Small |
| A Page Kit-compiled template | The whole compiler: typed blocks (`prose`, `outcomes`, `video`, `disclosure`, `route_list`, `resources`, `callout`, `raw_html`; `page_kit.schema.json:69-83`), page types with required slots and admitted blocks (`:133-152`), lifecycle policy (`:43-65`), transactional output (`page_kit.py:857-877`), the `page_build/1` receipt | An adapter from the packager's course model to `coursecraft.page/1` pages and a `module_composition/1`, plus a kit that reproduces the BUMK 515 design. The block vocabulary lines up almost one for one (DESIGN.md table), except tables and timelines, which would be `raw_html` under a `warn` policy. Each page needs `eyebrow`, `title`, `lede`, slots, and per-block `origin`, `review_state`, `source_refs` (`module-overview.ready.json:7-9`, `:21-27`). The packager has the source refs (paragraph ids) and the origin (source-derived, or edited by recorded entry); `review_state` would be new. An effort of its own |
| A hybrid | The gate and tokens from Page Kit; the packager's renderer for the two surfaces Page Kit lacks: editor fields and bracketed structures | Page Kit's `delivery_surface` is a constant, `brightspace_html_topic` (`page_kit.schema.json:25`). It has no editor-field surface. The Workbench's only guidance there is the hand-authored snippet: "semantic tags only, NO `<style>`, NO classes" (`activity-description.snippet.html:7-9`). The packager's fragments use inline styles instead, as the old course did. The hybrid would need Page Kit to grow a fragment surface or the packager to keep it. Medium |

Also for later, from the neighbor templates rather than Page Kit itself: the
discussion-dates convention in `MODULE_LAYOUT_MENU.md:59-73` matches what the
packager now does (discussion deadlines on dated checklist items; checklist
under the overview), which is independent confirmation of the date design.
The `route_list` block (`page_kit.py:747-749`, CSS `:178-205`) is a numbered
"this week at a glance" the packager's checklist items could feed on the
overview page, if that is ever wanted.

## 4. Conflicts

- **Heading convention.** The gate requires exactly one `h1` (error) and warns,
  does not fail, on a level jump (`page_kit.py:386-389`). Probed with three
  synthetic pages in the scratchpad: `h1, h2, h3, h2` passes clean; `h1, h3`
  passes with one `HEADING_LEVEL_JUMP` warning; two `h1` fails. So one-to-one,
  with the page heading as the `h1` and content starting at Heading 2, passes
  the gate. If a blueprint's content starts at Heading 3 with no restyle, the
  build still passes with warnings. The Page Kit renderer writes the page title
  as `h1` and block headings as `h2` (`page_kit.py:731-733`, `:837`), so its own
  output follows the same rule.
- **Same-window internal links.** No conflict. The gate does not check
  `target`. Page Kit's renderer writes no `target` at all (`page_kit.py:735`,
  `:750-756`); the packager opens external links in a new window and internal ones
  in the same. The hand-authored CSS marks new-window links with an arrow
  (`course-page.css:145`), as the classic template does. Consistent.
- **Bracket forms.** Not visible to Page Kit; they are resolved before HTML.
  The gate's `PLACEHOLDER_LEAK` rule looks only for `REPLACE_WITH_`
  (`page_kit.py:411-412`). The packager's own full-width-bracket marker for an
  unknown link target (`LINK_TARGET_UNKNOWN`) would pass the gate silently, so
  the packager must keep treating it as its own error. It does.
- **Editor-field surface.** The real divergence. Page Kit has none; the
  Workbench snippet says no inline styles; the packager inlines the old
  course's styles in fragments by the owner's template choice. This is a
  template question, not a gate question, and belongs with the template
  decision.
- **Fixed markup.** Page Kit's blocks are fixed HTML shapes. The BUMK 515 page
  cannot be reproduced without a kit, as DESIGN.md already records. Not a
  conflict with any packager rule, but the reason the compiler is not called
  today.

## 5. Recommendation

In order:

1. **Turn the gate's rules into early packager diagnostics** with paragraph
   ids, for pages and fragments alike, and add the two checks the gate lacks
   that the blueprint can answer: a header row for tables, and link text that
   is not a bare address or "here". Reason: the gate reports after the build
   and only on pages; the author needs the line in the Word document.
2. **Skip link, focus outline, print rules** into the classic template's CSS,
   plus `loading="lazy"` on video frames. Reason: accessibility wins for the
   price of copying rules, and the hand-authored templates already converged
   on the focus style across reviewed courses (`MODULE_LAYOUT_MENU.md:90-91`).
3. **Per-page `external_links` and a provenance comment** in the page HTML and
   the receipt. Reason: the sandbox link check and the re-export comparison
   both get easier, and it matches Page Kit's receipt shape for later
   convergence.
4. **Express the classic template's colors as a Page Kit theme token set**
   (first row of section 3). Reason: it is the smallest step toward kits and
   costs nothing in behavior now.
5. **Leave the compiler itself for the template decision.** Reason: the owner
   deferred page design; the adapter is an effort of its own, and the
   editor-field surface has no home in Page Kit yet.

Probe artifacts: `scratchpad/pagekit_probe/` (three synthetic pages and
`gate.json`). The `page_kit.cpython-313.pyc` in `U/scripts/__pycache__/` is
dated 2026-09-02 and predates this pass.
