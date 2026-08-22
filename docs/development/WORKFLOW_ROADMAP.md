# workflow-C implementation roadmap

This roadmap is intentionally outcome-first and staged. Do not jump ahead merely because later work is interesting. Get each earlier stage reliable before expanding scope.

## Priority 1 — get the current workflow reliably running

Before adding major new functionality, stabilize the current Windows + Python 3.14 + Fiji + AHK v2 route and remove the known blockers that prevent dependable end-to-end use.

Continue to obey the image-blind private-test contract and manual-validation backlog. Exhaust static/generated-artifact/telemetry checks before asking for desktop input.

The first practical success target is deliberately narrow: process and composite/select strain matrices from the 14.08.26 and 15.08.26 sample sessions together. Both use annotationSet 1, one 12-column strain-label band, and an 8-row vertical layout. Do not let the more complex 16.08.26 layout delay this first working route.

## Priority 2 — V10 workbook integration

Make V10 the preferred rich metadata input for full experiments.

Implement, in bounded slices:

1. read-only `.xlsm` adapter using the actual workbook without conversion;
2. canonical internal records using V10 terminology;
3. `sessionUID` / `Image UID` identity;
4. local session-folder mapping;
5. raw/working/known-derivative filename reconciliation;
6. incomplete-dataset validation and READY / EXPECTED_NOT_PRESENT / AMBIGUOUS / UNMAPPED_FILE states;
7. local provenance keyed by Image UID;
8. annotation-derived grid metadata using the current one-vertical-profile scope;
9. first prove multi-session 8 x 12 operation for 14.08.26 + 15.08.26 with annotationSet 1;
10. then add the 16.08.26 8 x 10 two-strain-band layout from annotationSet 2;
11. generated compatibility handoffs only where existing Fiji/Pillow code still needs them.

See `V10_WORKBOOK_CONTRACT.md` for the detailed contract. In particular, ignore the vertical-profile table's `Set` values; they remain in the workbook only because removing them currently disrupts the workbook.

Do not mix this stage with unrelated image-processing feature expansion.

## Priority 3 — metadata-driven annotations

Once V10 ingestion and basic processing are reliable, use the same canonical metadata to generate annotations rather than creating another metadata system.

Initial annotation scope should focus on useful current labels such as:

- strain labels;
- vertical labels;
- plate/condition labels;
- date/session/figure labels where useful.

Prefer mature capabilities such as Pillow text/composition and Fiji overlays/ROI Manager where appropriate. Preserve editability where it provides practical value. Ignore `other` labels until explicitly needed.

## Priority 4 — automated visibility adjustment

After annotation basics are stable, improve automatic visual standardization while keeping quantitative pixels separate from display enhancement.

Use existing Fiji/ImageJ/scientific-image functionality first. Build on the existing global/background-aware visibility work; keep CLAHE/local enhancement optional where consistency matters.

## Priority 5 — automatic overall plate rotation/alignment

After the current grid-based/manual alignment path is dependable, investigate automatic orientation of the physical plate itself, independent of colony-grid detection.

Prefer mature Fiji/ImageJ registration/geometry tools or established scientific-image packages before custom detection. Manual grid alignment remains a fallback/authoritative route unless the user changes that requirement.

## Priority 6 — lightweight CSV mini-project input

This is a required future function, but defer implementation until the preceding basics are working.

Goal: allow quick small comparisons without editing a large V10 workbook.

Do **not** create a second processing architecture. Implement a lightweight CSV/folder-discovery adapter that produces the same canonical workflow-C project model as V10.

Desired conveniences may include:

- explicit filename or unique filename-stem matching;
- selected-folder filename discovery;
- a small confirmation/mapping table;
- optional reuse of a saved layout/annotation preset;
- generated temporary UID when no V10 Image UID exists;
- the same READY / missing / ambiguous / unmapped validation model;
- the same image-blind privacy rules.

This input route is for quick comping/small jobs; V10 remains the richer metadata route for full experiments.

## General implementation rule

At every stage, first check whether Fiji/ImageJ, Pillow, scikit-image, OpenCV, CellProfiler, ilastik, pandas/Polars, SQLite or another mature tool already covers the required function. Add only the smallest glue needed to connect stable components.
