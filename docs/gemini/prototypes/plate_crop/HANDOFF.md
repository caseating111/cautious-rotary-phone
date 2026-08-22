# Plate crop preprocessing handoff

Status: Planned

## Goal

Build a focused preprocessing step that derives a consistent whole-plate crop from an already orientation-corrected working image before the current four-click culture-grid registration step.

This replaces manual Photoshop whole-plate cropping while keeping a fast preview/accept/retry path.

See `docs/gemini/FUTURE_WORKFLOW.md` and `docs/development/PROJECT_ASSET_CONTRACT.md`.

## Do not use the colony ROI-box plugin

The ROI 1-click rotated-rectangle colony tool is not appropriate here. This step needs plate-boundary coordinates, not a fixed-size 108x108 colony ROI.

Use precise crosshair/point clicks or equivalent native point events.

## Preferred interaction: four boundary points first

The default interaction should require **four crosshair clicks** on the already-straightened working plate:

1. leftmost useful plate boundary;
2. rightmost useful plate boundary;
3. topmost useful plate boundary;
4. bottommost useful plate boundary.

These points are intentionally forgiving: the user does not need to find corners. Each click supplies one useful extreme coordinate.

Display each marker and label it (`L`, `R`, `T`, `B`) so obvious misclicks are easy to spot.

## Crop proposal from four points

After the fourth click, calculate immediately:

- measured horizontal extent from L/R;
- measured vertical extent from T/B;
- estimated plate center;
- default square side;
- proposed crop rectangle.

A good first default is to use the smaller trustworthy plate extent as the square side basis so the crop does not expand into blank background, then round it **down to nearest 50 px**.

Conceptually:

`side = floor(min(measured_width, measured_height) / increment) * increment`

with `increment=50` by default.

The exact rule may be adjusted if synthetic/manual testing shows a better equally-simple conservative calculation, but round-down/no-added-blank-space is the governing intent.

Cropping slightly into nonessential plate edges is acceptable; introducing extra blank space is undesirable.

## Optional re-anchor rather than mandatory extra clicks

The originally requested left-edge + top-edge two-click placement should be retained, but as an **optional correction mode** rather than required on every plate.

Normal fast path:

`4 boundary clicks -> proposed crop -> Accept`

If crop size is right but placement is off:

1. choose `Re-anchor/Adjust position`;
2. click somewhere along the desired left edge (x anchor);
3. click somewhere along the desired top edge (y anchor);
4. reposition the existing square using those x/y anchors without remeasuring its size;
5. preview again.

This preserves manual control while reducing routine crop interaction from six clicks to four.

## Residual tilt handling

The orientation mini-app should already remove the meaningful plate tilt. Do not make crop logic another alignment system.

If a small known residual/orientation transform exists, use the saved transform mathematically where useful for coordinate conversion/overlay. Do not require another complex rotated ROI interaction merely to chase tiny residual tilt.

If the proposed axis-aligned crop is visibly poor, Retry/return to orientation is preferable to creating fragile crop-specific rotation logic.

## Square default, not hard limitation

Square is the default first implementation because it gives predictable dimensions and matches the intended plate presentation.

Keep options extensible enough for rectangular/aspect-ratio modes later, but do not implement arbitrary polygon cropping before the square route is proven.

## Step-by-step user function

1. Receive/open accepted orientation-corrected working image.
2. Crosshair cursor asks for L/R/T/B boundary clicks.
3. Show markers as clicked.
4. Calculate square side and round down using configured increment (50 default).
5. Draw proposed crop overlay and/or cropped preview.
6. User chooses:
   - `Accept/Save`;
   - `Retry boundaries`;
   - `Re-anchor` (optional L+T clicks);
   - `Cancel/Skip`.
7. Accept writes a derived working crop and persists `CropResult`/transform.
8. Later four-click grid registration receives that accepted working image.

The interaction should be hotkeyable where easy: e.g. Enter/A = accept, R = retry, optional P = reposition/re-anchor. Exact keys may follow existing controller conventions.

## Preview behavior

Preview must not require destructive save/delete cycles. The user should see the proposed boundary/overlay or derived preview before the working crop is committed.

No multi-dialog sequence is needed if one image window plus a compact status/action UI is sufficient.

## Source/output behavior

- raw source remains untouched;
- operate on the working/orientation-corrected derivative;
- preview is non-destructive;
- accepted crop writes an explicit working derivative;
- preserve Image UID/canonical identity;
- persist crop geometry and source->crop transform as reusable project state;
- rerun/reset must be possible;
- changing crop after downstream grid registration should mark that old grid state stale/incompatible rather than silently applying it to different geometry.

## Result contract

Conceptually:

`derive_plate_crop(image, orientation_result, boundary_points, options) -> CropResult`

Result should include:

- image UID/reference;
- L/R/T/B points;
- optional re-anchor points;
- measured width/height;
- crop rectangle/shape;
- rounding increment and pre/post-rounded size;
- source/output dimensions;
- accepted/skipped state;
- output path when saved;
- source->crop transform/version.

## Required synthetic proofs

1. four known boundary points produce expected center/extents;
2. square defaults from the conservative extent;
3. 50 px default round-down is correct;
4. configurable rounding increment works;
5. normal four-click proposal can be accepted with no extra anchor clicks;
6. optional left/top re-anchor moves crop without changing side size;
7. preview writes nothing;
8. accept writes derived working output while raw remains unchanged;
9. retry/reset works;
10. transform/result state persists;
11. skipped preprocessing does not block later four-click culture-grid registration.

## Out of scope

- culture/grid detection;
- visibility/levels adjustment;
- strain/culture crop export;
- annotation rendering;
- V10 parsing;
- adapting the colony ROI-box plugin;
- automatic arbitrary plate-boundary segmentation before the interactive route works.

## Completion record

- Branch:
- Commit:
- Interface:
- Point/cursor interaction:
- Tests:
- Dependencies:
- Crop/rounding rule:
- Re-anchor behavior:
- Preview/accept behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
