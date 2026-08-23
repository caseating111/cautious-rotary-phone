# Plate crop preprocessing handoff

Status: Planned

## Goal

Build a focused preprocessing mini-app that replaces manual Photoshop whole-plate cropping before the current four-click culture-grid registration.

The key rule is to separate **reusable crop-size calibration** from **per-image crop placement**. Plates may share the same imaged dimensions while appearing at different x/y offsets, so crop size can be reused but crop center/translation generally cannot.

See `docs/gemini/FUTURE_WORKFLOW.md` and `docs/development/PROJECT_ASSET_CONTRACT.md`.

## Do not use the colony ROI-box plugin

The ROI 1-click 108x108 rotated-rectangle colony tool is not appropriate here. Whole-plate cropping needs simple boundary/edge references, not a fixed-size colony ROI.

Use crosshair/point clicks plus a visible crop overlay.

## A. Reusable crop-size calibration

Calibration is required for the first representative plate of a compatible group and again only when the plate/image scale materially changes or the user explicitly chooses recalibration.

Calibration flow:

1. Display the orientation-corrected working plate.
2. User clicks four forgiving boundary references: leftmost useful plate edge, rightmost useful plate edge, topmost useful plate edge, bottommost useful plate edge.
3. Exact corners are not required.
4. Derive measured width and height from those four coordinates.
5. Default crop shape is square.
6. Use a conservative side-length basis that avoids adding blank background; slight loss of nonessential plate edge is acceptable.
7. Round the proposed square side **down to the nearest 50 px by default**.
8. Rounding increment/behavior is configurable.
9. Save the accepted size as a reusable `CropSizeCalibration`/preset.
10. Use that calibration immediately for the current image's placement step.

Recommended first rule:

`side = floor(min(measured_width, measured_height) / increment) * increment`

with `increment = 50` by default, unless practical testing shows a better equally simple conservative rule.

## B. Per-image placement is always separate

A reusable crop size does **not** imply a reusable crop center. Another plate may have identical dimensions but be shifted in the camera frame.

For each image:

1. Reuse the current calibrated crop width/height.
2. User clicks **somewhere on the left physical plate edge**. Only the x coordinate is authoritative for horizontal placement.
3. User clicks **somewhere on the top physical plate edge**. Only the y coordinate is authoritative for vertical placement.
4. Place the calibrated crop rectangle from those independent x/y anchors using the configured inset/offset rule.
5. Show the proposed crop overlay and/or cropped preview.
6. User chooses `Accept`, `Retry placement`, `Recalibrate size`, or `Skip/Cancel` as appropriate.
7. On Accept, persist this image's crop rectangle/translation and write the derived working crop.

This deliberately avoids exact-corner clicking. Finding a precise top-left corner can be difficult; identifying any clear point on the left edge and any clear point on the top edge is easier and more robust.

Do not silently reuse the previous plate's x/y placement.

## Routine interaction cost

When a valid crop-size calibration already exists, the normal path should be:

`left-edge click -> top-edge click -> preview -> Accept`

Only recalibration adds the four boundary clicks.

The UI should remember the current size calibration until changed rather than asking the user to choose a scope every image. A simple `Reuse current crop size` / `Recalibrate crop size` control is sufficient initially.

Future optional scope controls (selected images / experiment / Set / image only) are acceptable if they reduce effort, but are not required for first proof.

## Relationship to orientation preprocessing

The plate-orientation app normally runs first using one straight-line drag along a top or bottom plate edge. Crop placement then operates in that orientation-corrected coordinate space.

If small residual tilt remains, use the saved transform mathematically only when useful. Do not add extra routine interactions merely to chase tiny residual tilt.

Skipping orientation must not make crop or four-click grid registration unavailable.

## Preview / verification

Preview is required before the final working crop is written. It should make it obvious whether:

- blank background has entered the crop;
- useful plate area was removed excessively;
- the reused size no longer fits this plate;
- x/y placement is wrong.

Fast/hotkeyable actions are desirable: accept, retry placement, recalibrate size.

Retrying placement should **not** require recalibrating size.

## Source/output behavior

- raw source remains untouched;
- operate on the working/orientation-corrected derivative;
- preview is non-destructive;
- accepted crop writes an explicit working derivative;
- preserve Image UID/canonical identity;
- persist crop-size calibration separately from per-image crop placement;
- rerun/reset/recalibrate remains possible.

## State contract

Conceptually keep two layers of state.

### `CropSizeCalibration`

- calibrated square side / width / height;
- measured calibration extents;
- rounding increment/rule;
- scale/context where needed;
- calibration method/version;
- optional future reuse scope.

### Per-image `CropResult`

- image UID/reference;
- calibration ID/version used;
- left-edge x anchor;
- top-edge y anchor;
- final crop rectangle;
- source/output dimensions;
- accepted/skipped state;
- output path;
- source->crop transform/version.

Do not collapse crop size and crop translation into one supposedly reusable rectangle.

## Relationship to four-click grid registration

The existing four-click culture-grid route receives the accepted cropped working image.

Changing crop geometry after grid registration must mark that coordinate asset stale/incompatible or explicitly transform it. Never silently reuse old grid coordinates in a new crop coordinate space.

Do not derive culture coordinates here.

## Mini-app boundary

The applet may:

- show the current crop-size calibration;
- perform four-boundary calibration/recalibration;
- collect per-image left/top placement anchors;
- show crop overlay/preview;
- accept/retry/recalibrate;
- save crop state and derived working image.

It should not parse V10, perform culture-grid registration, adjust visibility, export culture crops, or annotate.

## Required synthetic proofs

1. four boundary points derive the expected reusable square size;
2. square side rounds down to nearest 50 by default;
3. configurable rounding increment works;
4. a second image with the same plate size but different x/y offset reuses the size while producing a different crop rectangle from left/top anchors;
5. exact corner clicking is unnecessary;
6. preview writes nothing;
7. accept writes derived output while raw source remains unchanged;
8. retry placement does not require recalibration;
9. recalibration cleanly replaces/versions the current size calibration;
10. crop-size state and per-image translation state remain distinct;
11. changing crop geometry correctly invalidates downstream grid state when applicable;
12. skipping crop preprocessing does not block the four-click route.

## Success criteria

`Proven` means one crop-size calibration can be reused across compatible plates while every image is independently positioned with only a left-edge and top-edge click, with fast preview/accept/retry/recalibrate behavior and explicit reusable state.

## Completion record

- Branch:
- Commit:
- Interface(s):
- Tests:
- Dependencies:
- Crop-size calibration behavior:
- Per-image placement behavior:
- Rounding behavior:
- Preview/accept behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
