# Annotation/composition prototype handoff

Status: Planned

## Goal

Build an isolated annotation/composition component that consumes shared canonical metadata plus `PlateLayout` and produces useful labeled/composite outputs without depending on the current Fiji/AHK/controller runtime. Prefer Pillow and mature existing image/graphics facilities; Fiji may be used where it is clearly the better mature tool, but do not recreate mature rendering/layout features from scratch unnecessarily.

This prototype may expose both a narrow callable API and a focused mini-app. The eventual main controller can launch/orchestrate it, but the current controller must not be refactored during prototype work.

## Intended role in the larger architecture

The main controller should remain responsible for project/file selection, validation, shared state, and launch buttons. Annotation/composition can be a focused subordinate tool that receives a canonical project/layout payload and returns/saves outputs.

The component must therefore be usable independently of the GUI. GUI code should wrap reusable rendering/composition functions rather than contain the core logic.

## Inputs

Use synthetic inputs only during this prototype. The component should consume normalized structures rather than workbook-specific tables.

Expected information includes:

- image/session identity;
- experiment/date/session labels;
- media/condition/set/replicate fields when requested for display;
- `PlateLayout` row/column dimensions;
- ordered strain bands and strain labels;
- ordered vertical labels;
- annotation options/preset;
- optional source image/canvas path for synthetic/public test images only.

The annotation renderer should not need to reopen V10 or parse filenames to rediscover metadata already supplied structurally.

## Required annotation behavior

Support at minimum:

- strain labels in logical column order;
- vertical labels in logical row order;
- date label;
- plate/experiment/set/media/condition labels where configured;
- optional session/replicate identifiers;
- configurable visibility of label classes;
- sensible margins/padding and deterministic placement;
- independent text/orientation handling where needed;
- preservation of user-facing label text exactly as supplied.

`other` labels remain out of scope initially.

## Strain bands and layout awareness

The renderer must understand that a plate may contain more than one ordered strain profile occupying different row bands.

Required cases:

### 8 x 12 single-band

- one strain profile spans rows 1-8;
- strain labels positions 1-12 align to the 12 logical columns;
- one vertical profile supplies 8 row labels.

### 8 x 10 two-band

- upper strain profile (`Order=1`) occupies rows 1-4;
- lower strain profile (`Order=2`) occupies rows 5-8;
- each may have its own strain-label set;
- overall grid width is 10.

### Unequal-width bands

If the overall grid is 10 columns but a lower band contains only 4 strain positions, keep the overall plate width while placing that band's labels according to its local logical positions. Do not collapse the full layout to four columns merely because one band is narrower.

The exact visual anchoring for narrower bands should be a configurable/deterministic layout choice rather than inferred from label text.

## Vertical labels

Use physical vertical `Pos` ordering. Repeated label text is valid and must render on separate rows. For example `0, -1, -2, -3, 0, -1, -2, -3` represents eight physical row positions, not four unique labels.

Current scope assumes one vertical profile per plate/layout.

## Rotation/orientation behavior

The tool should allow annotation orientation to remain visually readable when images/layouts are rotated. Text orientation and image/grid orientation do not have to be coupled if decoupling them produces a clearer output.

Do not embed assumptions from the current Fiji four-click implementation. Consume the logical layout and any later accepted image transform/rotation as inputs.

## Composition/matrix behavior

The component should be designed so it can support small image compositions/matrices in addition to whole-plate annotation. The user may sometimes want to create a few small composites without editing a large master workbook.

For the prototype, prove the rendering/composition boundary rather than implementing every future controller flow. Useful capabilities may include:

- arranging selected synthetic crops/images into a deterministic matrix;
- preserving supplied condition/strain ordering;
- adding row/column labels from structured metadata;
- exporting a composed image without requiring Photoshop;
- keeping source images unchanged and creating explicit derived outputs.

A later lightweight CSV controller may feed the same canonical request model, but that controller is out of scope for this prototype.

## Output expectations

Prefer explicit derived outputs. The renderer should be able to return enough information for callers to know what was produced, for example output path, dimensions, annotations used, and warnings.

Possible output formats may include PNG/TIFF/JPEG as appropriate. Do not force lossy conversion when a lossless output is preferable.

If a layered/editable intermediate representation is easy to obtain using mature software, it may be explored, but do not make editable layers a prerequisite if a reliable rendered output satisfies the workflow more efficiently.

## Mini-app behavior

A focused mini-app is allowed and encouraged if it materially reduces user effort. It should remain narrow, e.g.:

- choose/load a synthetic/canonical request;
- preview annotation/composition;
- toggle label classes/options;
- adjust a few layout/padding/orientation parameters;
- render/export.

Do not duplicate project/file discovery, V10 parsing, or global controller settings inside the applet. Those should eventually be passed in by the main controller/shared model.

## Shared contract

Use `contracts/project_model.schema.json`, `contracts/plate_layout.schema.json`, and `contracts/annotation_request.schema.json` as the intended boundary.

If the request contract lacks a necessary field, propose a narrow contract change in this HANDOFF rather than creating hidden controller-specific globals.

The eventual ideal boundary is conceptually:

`render_plate_annotation(image_or_canvas, image_record, plate_layout, options) -> AnnotationResult`

and/or a similarly narrow composition call.

## Mature-tool-first implementation posture

Before substantial custom rendering/layout code, check mature capabilities in Pillow, Fiji/ImageJ, and established Python imaging/layout packages. Use thin glue around proven primitives.

Do not recreate text measurement, image resizing, affine transforms, or common composition operations from first principles when mature libraries already provide them.

## Data/scientific safety

- Use synthetic/public images only during prototype development.
- Never alter source pixels in-place by default.
- Annotations and composites are derived outputs.
- Quantitative measurements must not be taken from annotation-rendered/visibility-enhanced outputs unless explicitly designed for that purpose later.
- Preserve original metadata text separately from rendered formatting choices.

## Out of scope

- current Fiji launcher/AHK/controller stabilization;
- V10 workbook parsing itself;
- live filesystem reconciliation;
- `other` labels;
- quantitative colony/stress scoring;
- automatic whole-plate physical rotation estimation;
- refactoring the existing main controller into mini-apps.

## Required synthetic proofs

At minimum demonstrate:

1. an 8x12 single-strain-profile plate annotation;
2. an 8x10 two-strain-band plate annotation;
3. repeated vertical labels placed by physical `Pos`;
4. deterministic strain ordering from `Pos`/band order;
5. a simple small composite/matrix from synthetic inputs with structured row/column labels;
6. configurable date/plate/media/condition labels;
7. source image remains unchanged and output is written separately;
8. callable renderer works without launching the mini-app GUI.

## Success criteria

The prototype is `Proven` when the renderer/compositor has a narrow reusable API, the required synthetic layouts render deterministically, a focused mini-app (if included) wraps rather than owns core logic, targeted tests pass, and downstream integration can occur through the shared model without importing current controller internals.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface(s):
- Mini-app entry point, if any:
- Tests:
- Dependencies:
- Proven layouts/compositions:
- Output formats:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
