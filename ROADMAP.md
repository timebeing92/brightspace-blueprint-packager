# Roadmap

Ordered by what unblocks the next piece of evidence.

## Next

1. **Sandbox import of the MBA 620 package.** Follow `LIVE_RUNBOOK.md` in the build folder. Record the result as an L3 receipt.
2. **Re-export and compare.** Run the wizard on the sandbox re-export and compare it with the course model. That is the L4 evidence for the six local extensions.
3. **Feed results back.** Each extension that survives becomes a promotion candidate for `d2l_package_lib`; each that fails is fixed or dropped.

## Then

4. **Re-base the decisions themselves.** `rebase-map` translates a map to a later export, but the script that authors MBA 620's map still speaks in the first export's ids. Once edits pile up, rewrite the decisions against a new base using the translation table.
5. **Structure fixes in Blueprint Wizard's Word writer.** Real heading styles, explicit dropdown and callout endings, module names before Week 1, forum and submission type on activity lines. These five let a Word blueprint say enough by itself. They are Workbench changes, proposed in the MBA 620 review lane, and need the owner's determination first.
6. **Automatic course map for wizard-fresh blueprints.** A blueprint straight from Blueprint Wizard has regular wizard lines. Its map can be generated instead of written by hand.
7. **`--preflight` and progress events.** A plan-only run that writes nothing, and `coursecraft.progress/1` events without new `run_end.outputs` keys.
8. **Dates, next step.** A calendar and due-day rules now set dates on assignment folders, checklist items, and a carried quiz. Still to do: confirm the quiz date form on import, and decide whether a due rule gets a line in the blueprint.
9. **A second page template.** Proves template selection. The natural candidate is a Page Kit kit, so page rendering converges on the upstream compiler.

10. **Receipts in the second run-receipt shape.** Upstream's blueprint pipeline now writes `coursecraft.run/2`, whose lineage key joins the org unit number and the manifest identifier. A package built from a blueprint has no org unit until it is imported, so lineage needs its own answer here first.
11. **Course-settings section for a blank blueprint.** Tool defaults, conditional release of modules or items, and the term calendar, asked once and applied by the packager. Owner note of 2026-10-06.
12. **Authorized edits, paste-back list.** A list of the build's wording changes in a form a person can apply to the source document, so the two can be brought back together.

13. **Page links from inside activity descriptions.** Needs the page topic's resource code before the manifest is written: mint topic codes at plan time.
14. **Decide the shared form for panel ends and internal links** with the owner, then have the wizard write it. The packager already reads both forms.

## Later, and not this tool's call

- How page design enters the packager: one template applied broadly, granular choices, or a separate building surface. Deferred by the owner on 2026-10-06; it needs its own consolidation effort. Page Kit is the likely home.

- Promotion upstream as a sibling producer with Blueprint Wizard as the front door.
- Catalog intake of the course model as an authored layer.
- Quiz authoring from a blueprint. That belongs to the quiz lane.
