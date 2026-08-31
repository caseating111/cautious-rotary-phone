# Reusable project asset contract

This document defines durable project state that later workflow components should reuse rather than recompute. It is intentionally shared across current `workflow-C` integration work and future Gemini mini-app prototypes.

## Core principle

A successful manual or computational step should create a reusable project asset when its result is useful later. Do not force repeated alignment, identity mapping, calibration, cropping, or presentation setup merely because a later action runs in another mini-app or at another time.

The current accepted four-click grid registration is especially important: its measured grid/spot coordinates are not a disposable crop-export intermediate. They are a durable project asset.

## Canonical reusable assets

Per image/Image UID, preserve where applicable:

1. canonical metadata identity (`Image UID`, `sessionUID`, experiment, Set, condition/media, replicate, annotationSet);
2. raw-source relative path and optional working-copy relative path;
3. raw-to-working filename mapping and rename disposition;
4. whole-plate orientation reference line, correction angle/transform and accepted/skipped state;
5. per-image whole-plate crop rectangle/translation and source->cropped transform;
6. logical `PlateLayout` (rows, columns, profile bands, labels);
7. measured grid transform and individual culture/spot coordinates from accepted four-click registration;
8. visibility-adjustment method/preset/result plus manual-review state;
9. processed whole-plate output path;
10. annotation preset/result and annotated output path;
11. culture-crop output metadata, keeping raw/unprocessed and processed variants distinct;
12. matrix/composition request/output metadata.

Reusable group/project calibration state may additionally include a `CropSizeCalibration` that is **not tied to one image's x/y placement**.

## Shared machine-readable project state

Standalone mini-apps and the eventual main controller need a small persistent interoperability layer. Use a machine-readable project manifest/state area that maps canonical image identity to the relevant assets/results above.

The integrated store is `State/workflow_project.json`, validated by `contracts/workflow_project_state.schema.json`, plus versioned per-result sidecars/assets. It satisfies these rules:

- project state persists when no controller/app is open;
- applets can be launched directly with a project root/state reference;
- one applet can discover the assets it needs without parsing another applet's human-readable logs;
- paths should be project-relative where practical;
- Image UID remains the canonical identity when V10 is available;
- state records include format/method/version information sufficient to reject incompatible stale assets;
- concurrent/independent applets should update only their owned result records rather than rewriting unrelated project state unnecessarily.

Human-readable conversion maps, summaries and logs are QC aids, not the machine API.

## Geometry has distinct reusable layers

Do not collapse these into one generic alignment record.

### Per-image orientation

The preferred first orientation interaction is one straight-line drag along a clear top or bottom physical plate edge. Persist the line endpoints, observed/correction angle and resulting transform.

Orientation is per image. Similar plates can still have different tilt.

### Reusable crop-size calibration

A representative plate can provide four boundary references (left/right/top/bottom) from which a reusable crop side/width/height is calibrated. Default square size rounds **down to nearest 50 px**, with configurable rounding.

This size calibration may be reused across compatible images.

### Per-image crop placement

Crop translation/position is not reusable merely because size is reusable. Plates may have identical dimensions but different camera-frame offsets.

For each image, the intended fast placement route is:

- click somewhere on the left plate edge -> authoritative x anchor;
- click somewhere on the top plate edge -> authoritative y anchor;
- place the current calibrated-size crop from those anchors;
- preview/accept/retry.

Do not require exact-corner clicking and do not silently reuse another image's crop center.

### Accepted culture-grid coordinates

The four-click culture-grid result is measured in one explicit working coordinate space after any accepted geometric preprocessing. It becomes the reusable source for culture positions.

## Grid coordinate asset

The accepted four-click result should expose enough information to reconstruct every culture position without asking for alignment again. Preserve at minimum:

- Image UID/reference;
- image coordinate space/dimensions in which the grid was measured;
- four authoritative reference points or equivalent accepted grid transform;
- row/column counts;
- row/column basis vectors or equivalent affine/bilinear representation;
- calculated center coordinate for every logical culture spot;
- local strain-band/row mapping where relevant;
- timestamp/version/method identifier;
- accepted/reset status;
- source transform chain needed to map between raw/working/cropped/processed/annotated derivatives where geometrically compatible.

Do not bind this asset only to immediate crop export.

The integrated implementation is `tools/grid_coordinates.py` with schema `contracts/grid_coordinate_asset.schema.json`. Version 1 uses continuous pixel centres in `source_image_pixels`, with top-left origin, x increasing right, and y increasing down. The four accepted references are R1C1, R1C-last, R5C1, and R5C-last; the persisted asset contains deterministic row/column coordinates and every named `rNcM` spot. Numbered V10 projects store assets under `z. Metadata/State/GridCoordinates`; the runtime also discovers the older beside-CSV and project-level `GridCoordinates` locations. Assets retain an identity index and atomic replacement.

## Grid reuse requirements

Once an accepted coordinate asset exists, later operations should independently be able to use it to:

- export unprocessed culture crops immediately or later;
- derive the whole-grid ROI for visibility statistics;
- export processed culture crops after processed whole plates exist;
- place strain and vertical annotations automatically using actual measured spot coordinates;
- provide crop locations to matrix/composition tools;
- draw QC overlays/previews;
- support selected-strain exports without rerunning alignment.

A later action should check for the state it actually needs rather than require the full workflow to be replayed in order.

## Applet prerequisite contract

Standalone applets should be prerequisite-driven, not wizard-driven. Each applet declares the assets it genuinely needs and may run whenever those assets exist.

Examples:

- orientation: compatible source/working image only;
- plate crop placement: compatible image + crop-size calibration (or permission to calibrate one);
- grid registration: compatible image + logical layout/grid dimensions needed for registration;
- visibility adjustment: compatible image + accepted `GridCoordinateAsset`;
- processed crop export: accepted `GridCoordinateAsset` + compatible processed image;
- annotation: canonical metadata/layout + accepted grid asset + compatible source derivative;
- matrix/composition: requested crop assets.

If a prerequisite is absent, return a concise missing-prerequisite status. Do not force unrelated earlier stages to run merely because they precede it in the preferred full workflow.

## Standalone + controller parity

Every future mini-app should be runnable independently of the main controller. The overall controller is a convenience/orchestration layer, not a runtime dependency.

Where practical, one callable/core implementation should serve all of these entry routes:

- standalone single-image mini-app;
- standalone selected-batch mini-app;
- main-controller launch/action;
- targeted automated tests/CLI-style invocation.

Do not maintain separate controller-only and standalone processing implementations for the same operation.

The current proven four-click batch/single route is retained as the focused grid-registration endpoint. Its optional register-only mode publishes `GridCoordinateAsset` without crop output. Crop export, visibility, annotation, and matrix composition are separate project-state consumers, so registration no longer owns those later actions.

## Transform discipline

Orientation correction and whole-plate cropping change coordinate spaces. Persist explicit transforms or enough deterministic geometry to map coordinates when later reuse requires it.

Prefer one canonical working coordinate space for culture-grid registration. Derived processed/annotated images should normally preserve that geometry so the same grid coordinates remain valid.

If a later operation changes geometry, it must compose/update the transform or declare dependent coordinates stale/incompatible. Never silently use coordinates measured in another geometry.

Display-only intensity/contrast/CLAHE/levels operations do not change geometry and therefore should not invalidate the grid asset.

## Dependency/staleness behavior

Rerunning an earlier geometric step must not leave downstream state falsely appearing current.

Examples:

- changing orientation may invalidate the per-image crop and any grid measured afterward;
- changing crop placement/size invalidates a grid measured in the prior cropped coordinate space unless explicitly transformed;
- recalibrating crop **size** does not by itself alter already accepted per-image crops until they are intentionally reapplied;
- resetting/re-registering the culture grid replaces/versions the coordinate asset and can mark dependent crop/annotation outputs stale;
- rerendering annotation with a different font preset does not invalidate grid geometry;
- recomputing visibility adjustment does not invalidate grid geometry.

Use lightweight dependency/version markers rather than building a large workflow engine.

## File-system independence

Identity is not filename identity. `Image UID` is canonical when V10 is available. Generic names such as `image1.jpg` remain valid when project metadata resolves them.

Renaming working copies is optional. Project assets should refer to canonical identity plus relative paths, not assume a descriptive filename is the primary key.

## Mini-app/controller integration

The eventual overall controller may launch focused mini-apps. Each should consume the reusable state it needs and return/update only its own result state.

Examples:

- orientation app -> `OrientationResult`;
- crop calibration/placement app -> `CropSizeCalibration` + per-image `CropResult`;
- grid registration -> `GridCoordinateAsset`;
- visibility app -> `AdjustmentResult`;
- annotation app -> `AnnotationResult`;
- culture-crop app -> immutable `CultureCropExport`;
- matrix app -> immutable mixed-tier composition result.

The controller should orchestrate state and prerequisites without absorbing all implementation details.

## Compatibility with current CSV mode

The working basic CSV route is intentionally simpler and does not need V10 `Set`/annotationSet/profile-order semantics retrofitted into it. It may still save the same reusable geometric assets. V10 later enriches identity/layout metadata around those assets instead of creating a second image-processing architecture.
