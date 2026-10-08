"""Blueprint Packager (working title).

An independent, downstream proving-ground tool that turns a flat course
blueprint (the layout Blueprint Wizard emits and SMEs edit) into a normalized,
machine-readable course model and then into a Brightspace import package.

It uses CourseCraft Workbench building blocks (component package serializers,
rubric XML builder, Blueprint Wizard extractors for read-back verification)
without being tied to their release cycles. See README.md and docs/DESIGN.md.
"""

__version__ = "0.1.1"
