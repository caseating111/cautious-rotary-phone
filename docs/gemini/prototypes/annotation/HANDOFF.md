# Annotation/composition prototype handoff

Status: INTEGRATED

Integrated on `workflow-integrated` at `c31d4f1`, with mixed-tier matrix composition added at `fdac0df`. Annotation uses embedded V10 layout plus accepted grid geometry for preview/final derivatives; matrix composition uses verified recorded crops and may mix Top/Low selections in one immutable run.

## Goal

Build an isolated annotation/composition component that consumes shared canonical metadata, saved grid coordinates and `PlateLayout` and produces useful labeled/composite outputs without depending on the current Fiji/AHK/controller runtime.

The key change from the old Photoshop workflow is that annotation placement should now be **primarily automatic**, because the working four-click grid route gives actual spot coordinates and V10 metadata gives the identity/order of strains and vertical labels. Manual repositioning should be an exception, not the normal workflow.

Prefer Pillow and mature existing image/graphics facilities; Fiji may be used where it is clearly better. Do not recreate mature rendering/layout features from scratch unnecessarily.

This prototype may expose both a narrow callable API and a focused mini-app. The eventual overall controller can launch/orchestrate it, but the current controller must not be refactored during prototype work.

## Inputs

Use synthetic inputs during this prototype. The component should consume normalized structures rather than workbook-specific tables.

Expected information includes:

- image/session identity;
- experiment/date/session labels;
- media/condition/set/replicate fields when requested for display;
- `PlateLayout` row/column dimensions and ordered strain bands;
- saved pixel grid/spot coordinates for the target image;
- ordered vertical labels;
- annotation options/preset;
- optional source image/canvas path for synthetic/public test images only.

The renderer should not reopen V10 or parse filenames to rediscover metadata already supplied structurally.

## Automatic placement from grid coordinates

The saved grid/spot coordinates are the placement authority for strain/vertical labels.

Required behavior:

- strain labels map automatically to known logical strain columns/bands and measured spot coordinates;
- vertical labels map automatically to physical row coordinates;
- repeated vertical label text remains separate because `Pos`/row identity is distinct;
- multiple strain-profile bands use their own row ranges and local widths;
- spacing is derived from the measured grid/spot geometry rather than a fixed Photoshop-style template;
- plate/date/description labels use configured anchor/offset rules relative to the image/grid/canvas.

The old template workflow existed largely to avoid Photoshop lag and manual layer overload. It is **not** a required architecture now. Pillow/ImageJ rendering should generate labels directly and cheaply.

Manual position overrides may exist as a fallback, but the default expected user experience is automatic placement with preview/accept rather than hand-moving every plate's labels.

## Label orientation

The historical strain-label convention should remain available as a preset/default option:

- strain labels rotated 90 degrees clockwise;
- top of strain text faces right;
- bottom faces left;
- vertical labels remain upright unless a preset explicitly changes them.

Text orientation should remain independently configurable from image/plate rotation so labels can stay readable after preprocessing.

## Reusable presentation presets

Support reusable presentation presets for parameters such as:

- font/family;
- font size;
- text color;
- offsets from grid/spot anchors;
- text orientation/rotation;
- label-class visibility;
- margins/padding;
- figure-description/date anchor positions;
- optional abbreviations/display formatting.

Scientific identity/order remains in canonical metadata. Presentation presets must not mutate `Image UID`, strain identity, `Pos`, `Order`, Set, Condition, etc.

Spacing of strain/vertical labels should normally come from the actual grid geometry, not from manually encoded per-template spacing.

## Preview mode is required

A preview function is required so the user can inspect fonts, sizes, labels, orientation, offsets and overall placement **without altering source files or committing an output**.

The mini-app/API should support a cheap preview path that:

- renders to memory or an explicit temporary/preview artifact;
- never overwrites the source image;
- does not require the user to create/process/delete a final file just to see layout changes;
- can be regenerated quickly when a preset option changes.

Final render/export is a separate explicit action.

## Whole-plate label behavior

Support at minimum:

- strain labels in logical column/band order;
- vertical labels in physical row order;
- date label;
- experiment/plate/Set/media/Condition labels where configured;
- optional session/replicate identifiers;
- overall figure-description text derived from structured metadata/preset rules;
- configurable visibility of label classes;
- deterministic placement from grid coordinates + preset offsets;
- preservation of supplied user-facing label text.

`other` labels remain out of scope initially.

## Strain bands and layout awareness

### 8 x 12 single-band

- one strain profile spans rows 1-8;
- strain labels positions 1-12 align to the measured 12-column grid;
- one vertical profile supplies 8 row labels.

### 8 x 10 two-band

- upper strain profile (`Order=1`) defaults to rows 1-4;
- lower strain profile (`Order=2`) defaults to rows 5-8;
- each has its own strain-label set;
- overall grid width is 10;
- an explicit row-band override from `PlateLayout` must be honored.

### Unequal-width bands

If the overall grid is 10 columns but one band contains only 4 strain positions, preserve the overall grid and use that band's local logical/pixel positions. Do not collapse the full layout to four columns.

## Composition/matrix behavior

The component may also provide lightweight composition/matrix rendering because it already has metadata/label/rendering primitives. This should remain separable from whole-plate annotation.

Useful capabilities include:

- arranging selected existing crops into a deterministic matrix;
- preserving supplied condition/strain ordering;
- adding row/column labels from structured metadata;
- exporting a composed image without Photoshop;
- keeping source images unchanged;
- allowing modest manual selection/order override for quick small compositions rather than requiring the master workbook to be edited first.

A later small CSV controller may feed the same canonical request model.

### Mixed crop-tier selection

Matrix selection must not assume every selected strain uses the same crop tier. The integrated mixed-tier request can choose, for example:

- WT1 -> `top` crop;
- STRAIN2 -> `low` crop;
- another strain -> another available tier;

within the same matrix.

Top/Low is recorded per selected candidate rather than imposed globally by the composition contract.

## Output expectations

- source images remain unchanged;
- final annotations/composites are explicit derived outputs;
- output path/dimensions/annotations/preset/warnings should be reportable;
- prefer lossless output where appropriate;
- layered/editable intermediates are optional conveniences, not requirements.

## Mini-app behavior

A focused mini-app is encouraged if it reduces user effort. It may:

- receive/select a canonical image/request;
- show fast annotation preview;
- choose/reuse a presentation preset;
- toggle label classes;
- tweak font/size/offset/orientation;
- optionally override a position only when needed;
- render/export final output;
- build a small composition/matrix with structured or manually selected crops.

Do not duplicate project discovery, V10 parsing or global controller settings inside the applet.

## Shared contract

Use `contracts/project_model.schema.json`, `contracts/plate_layout.schema.json`, `contracts/annotation_request.schema.json`, plus a narrowly defined saved-grid/coordinate input if needed.

Ideal boundary is conceptually:

`render_plate_annotation(image, image_record, plate_layout, grid_coordinates, preset) -> AnnotationResult`

and a similarly narrow composition call.

## Mature-tool-first implementation posture

Before substantial custom rendering/layout code, check mature capabilities in Pillow, Fiji/ImageJ and established Python imaging/layout packages. Use thin glue around proven primitives.

Do not recreate text measurement, image resizing, affine transforms or common composition operations from first principles when mature libraries already provide them.

## Data/scientific safety

- use synthetic/public images only during prototype development;
- never alter source pixels in place by default;
- annotations/composites are derived outputs;
- quantitative measurements must not be taken from annotation-rendered/visibility-enhanced outputs unless explicitly designed later;
- preserve original metadata separately from rendered formatting choices.

## Out of scope

- current Fiji launcher/AHK/controller stabilization;
- V10 workbook parsing itself;
- live filesystem reconciliation;
- `other` labels;
- quantitative colony/stress scoring;
- automatic whole-plate physical orientation/cropping;
- refactoring the existing main controller into mini-apps.

## Required synthetic proofs

At minimum demonstrate:

1. automatic 8x12 whole-plate annotation from saved grid coordinates;
2. automatic 8x10 two-strain-band annotation;
3. repeated vertical labels placed by physical row/`Pos`;
4. strain labels rotated 90 degrees clockwise with top facing right as a preset;
5. fast non-destructive preview with preset changes;
6. deterministic date/figure-description/plate labels from metadata + saved offsets;
7. a small composite/matrix with structured labels;
8. mixed crop-tier selection within one matrix;
9. source image remains unchanged and final output is separate;
10. callable renderer works without launching the GUI.

## Success criteria

The prototype is `Proven` when automatic grid-derived placement works for the required layouts, preview/presets work without modifying sources, the renderer/compositor has a narrow reusable API, targeted tests pass, and later integration can occur through shared contracts without importing current controller internals.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface(s):
- Mini-app entry point, if any:
- Tests:
- Dependencies:
- Proven layouts/compositions:
- Preview/preset behavior:
- Output formats:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
