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

Standalone mini-apps and the eventual main controller need a small persistent interoperability layer. Use a machine-readable project manifest/state area that maps canonical image identity to relevant assets/results.

The exact representation can remain lightweight, but it should satisfy these rules:

- project state persists when no controller/app is open;
- applets can launch directly with a project root/state reference;
- one applet can discover needed assets without parsing another applet's human-readable logs;
- paths are project-relative where practical;
- Image UID remains canonical identity when V10 is available;
- state includes format/method/version information sufficient to reject incompatible stale assets;
- independent applets update only their owned result records rather than rewriting unrelated project state unnecessarily.

Human-readable conversion maps, summaries and logs are QC aids, not the machine API.

## Geometry has distinct reusable layers

### Per-image orientation

Preferred first orientation interaction is one straight-line drag along a clear top or bottom plate edge. Persist line endpoints, observed/correction angle and resulting transform.

### Reusable crop-size calibration

A representative plate can provide four boundary references (left/right/top/bottom) from which reusable crop size is calibrated. Default square size rounds down to nearest 50 px, with configurable rounding.

### Per-image crop placement

Crop position is not reusable merely because size is reusable. For each image:

- click somewhere on the left plate edge -> x anchor;
- click somewhere on the top plate edge -> y anchor;
- place current calibrated-size crop from those anchors;
- preview/accept/retry.

Do not require exact-corner clicking and do not silently reuse another image's crop center.

### Accepted culture-grid coordinates

The four-click culture-grid result is measured in an explicit working coordinate space after accepted geometric preprocessing and becomes the reusable source for culture positions.

## Grid coordinate asset

Preserve enough information to reconstruct every culture position without alignment again, including:

- Image UID/reference;
- coordinate space/dimensions;
- four authoritative reference points or equivalent transform;
- row/column counts;
- basis vectors/affine or equivalent geometry;
- center coordinate for every logical culture spot;
- local strain-band/row mapping where relevant;
- timestamp/version/method;
- accepted/reset status;
- transform chain needed between compatible derivatives.

## Grid reuse requirements

Once accepted, later operations should independently be able to use the grid asset for unprocessed crop export, whole-grid ROI statistics, processed crop export, automatic annotation placement, matrix crop resolution, QC overlays and selected-strain export without rerunning alignment.

## Applet prerequisite contract

Standalone applets are prerequisite-driven, not wizard-driven. Examples:

- orientation: compatible source/working image;
- plate crop placement: compatible image + crop-size calibration or permission to calibrate one;
- grid registration: compatible image + logical layout/grid dimensions;
- visibility adjustment: compatible image + accepted grid asset;
- processed crop export: grid asset + compatible processed image;
- annotation: metadata/layout + grid asset + compatible source derivative;
- matrix/composition: requested crop assets.

If a prerequisite is absent, report that missing prerequisite rather than forcing unrelated earlier stages.

## Standalone + controller parity

Every future mini-app should run independently of the main controller. The overall controller is a convenience/orchestration layer, not a runtime dependency.

Where practical, one callable/core implementation should serve standalone single-image use, standalone selected-batch use, main-controller launch, and automated tests/CLI-style invocation.

Do not maintain separate controller-only and standalone processing implementations.

Grid registration should eventually follow the same rule: the proven four-click route can later be divested into a focused grid-registration applet whose principal output is `GridCoordinateAsset`; it should not own crop export, visibility, annotation or matrix workflows.

## Transform discipline

Orientation and whole-plate cropping change coordinate spaces. Persist transforms or enough deterministic geometry to map coordinates. Derived processed/annotated images should normally preserve registered geometry so saved grid coordinates remain valid.

Geometry-changing operations must update/compose transforms or mark dependent assets stale. Display-only intensity/contrast/CLAHE/levels operations do not invalidate grid coordinates.

## Dependency/staleness behavior

- changing orientation may invalidate crop/grid state downstream;
- changing crop placement/size invalidates a grid measured in the previous cropped space unless transformed;
- recalibrating crop size alone does not alter already accepted per-image crops until reapplied;
- resetting/re-registering grid replaces/versions coordinate state and can mark dependent outputs stale;
- annotation style or visibility adjustment changes do not invalidate grid geometry.

Use lightweight version/dependency markers rather than a large workflow engine.

## File-system independence

Identity is not filename identity. Image UID is canonical when V10 is available. Generic raw names remain valid when project metadata resolves them. Working-copy renaming is optional.

## Compatibility with current CSV mode

The basic CSV route remains intentionally simpler and does not need V10 Set/annotationSet/profile-order semantics retrofitted into it. It may still save the same reusable geometric assets; V10 later enriches identity/layout metadata around them.
