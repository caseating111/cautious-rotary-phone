# Reusable project asset contract

This document defines durable project state that later workflow components should reuse rather than recompute. It is intentionally shared across the current workflow-C integration work and future Gemini mini-app prototypes.

## Core principle

A successful manual or computational step should create a reusable project asset when its result is useful later. Do not force the user to repeat alignment, identity mapping, cropping, or presentation setup merely because a later action runs in a different mini-app or at a different time.

The current four-click grid registration is especially important: the measured grid/spot coordinates are not a disposable crop-export intermediate. They are a durable project asset.

## Canonical reusable assets

Per image/Image UID, preserve where applicable:

1. canonical metadata identity (`Image UID`, `sessionUID`, experiment, Set, condition/media, replicate, annotationSet);
2. raw-source relative path and optional working-copy relative path;
3. raw-to-working filename mapping and rename disposition;
4. whole-plate orientation transform/angle and whether it was accepted or skipped;
5. whole-plate crop geometry and source->cropped transform;
6. logical `PlateLayout` (rows, columns, profile bands, labels);
7. measured grid transform and individual culture/spot coordinates from the accepted four-click registration;
8. visibility-adjustment method/preset/result plus manual-review state;
9. processed whole-plate output path;
10. annotation preset/result and annotated output path;
11. culture-crop output metadata (raw/unprocessed and processed variants kept distinct);
12. matrix/composition request/output metadata when created.

## Grid coordinate asset

The accepted four-click grid result should expose enough information to reconstruct every culture position without asking for alignment again. At minimum preserve:

- Image UID/reference;
- image coordinate space/dimensions the grid was measured on;
- four authoritative reference points or equivalent accepted grid transform;
- row/column counts;
- row/column basis vectors or equivalent affine/bilinear representation;
- calculated center coordinate for every logical culture spot;
- local strain-band/row mapping where relevant;
- timestamp/version/method identifier;
- accepted/reset status;
- source transform chain needed to map between cropped/processed/annotated derivatives where dimensions remain geometrically compatible.

Do not bind the coordinate asset only to immediate crop export.

## Reuse requirements

Once an accepted coordinate asset exists, later operations should be able to use it independently:

- export unprocessed/raw culture crops;
- derive whole-grid ROI for visibility statistics;
- export processed culture crops after processed whole plates exist;
- place strain and vertical annotations automatically;
- provide crop locations to matrix/composition tools;
- draw QC overlays/previews;
- support later selected-strain exports without rerunning alignment.

A later action should check for the state it actually needs rather than require all previous workflow steps to be rerun in order.

## Transform discipline

Orientation correction and whole-plate cropping change coordinate spaces. Persist explicit transforms or enough deterministic geometry to map coordinates forward/backward where later reuse needs it.

Prefer one canonical working coordinate space for grid registration. Derived processed/annotated images should normally preserve that geometry so the same grid coordinates remain valid. If a later operation changes geometry, it must either compose/update the transform or declare the old coordinates incompatible rather than silently using them.

Display-only intensity/contrast/CLAHE/levels operations do not change geometry and therefore should not invalidate grid coordinates.

## Reset/version behavior

Rerunning an earlier geometric step should not silently leave downstream state looking current.

Examples:

- changing whole-plate orientation/crop may invalidate a grid measured in the previous coordinate space;
- resetting/re-registering a grid should create/replace the coordinate asset for that image and mark dependent derived outputs stale where relevant;
- rerendering annotation with a different font preset should not invalidate grid geometry;
- recomputing visibility adjustment should not invalidate grid geometry.

Use lightweight dependency/version markers rather than requiring a complex workflow engine.

## File-system independence

Identity is not filename identity. `Image UID` is canonical when V10 is available. Generic raw names such as `image1.jpg` remain valid inputs when project metadata resolves them.

Renaming working copies is optional. Reusable project assets should continue to refer to canonical image identity plus relative paths, not assume a human-readable filename is the primary key.

## UI/mini-app integration

The eventual overall controller may launch focused mini-apps. Each mini-app should consume the reusable state it needs and return/update only its own result state.

Examples:

- orientation app -> `OrientationResult`;
- whole-plate crop app -> `CropResult`;
- grid registration -> `GridCoordinateAsset`;
- visibility app -> `AdjustmentResult`;
- annotation app -> `AnnotationResult`;
- matrix app -> composition result.

The controller should orchestrate these without absorbing all implementation details.

## Compatibility with current CSV mode

The working basic CSV route is intentionally simpler and does not need V10 `Set`/annotationSet/profile-order semantics retrofitted into it. It may still save the same reusable geometric assets. V10 later enriches identity/layout metadata around those assets rather than requiring a second image-processing architecture.
