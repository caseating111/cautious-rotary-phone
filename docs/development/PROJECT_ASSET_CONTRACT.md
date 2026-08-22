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
- matrix app -> composition result.

The controller should orchestrate state and prerequisites without absorbing all implementation details.

## Compatibility with current CSV mode

The working basic CSV route is intentionally simpler and does not need V10 `Set`/annotationSet/profile-order semantics retrofitted into it. It may still save the same reusable geometric assets. V10 later enriches identity/layout metadata around those assets instead of creating a second image-processing architecture.
