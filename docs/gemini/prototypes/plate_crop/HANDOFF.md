# Plate crop preprocessing handoff

Status: Planned

## Goal

Build a focused preprocessing step that derives a consistent whole-plate crop from an already orientation-corrected working image before the current four-click grid-registration step.

This is intended to replace manual Photoshop whole-plate cropping while keeping a quick visual verification/retry path.

## Intended interaction

The currently desired practical route is interactive and lightweight rather than fully automatic:

1. establish approximate overall plate size from four side/extreme clicks or equivalent boundary points;
2. derive a default square crop size from that extent;
3. round the crop size **down to the nearest 50 pixels by default**;
4. allow the rounding increment/behavior to be changed in options;
5. collect a simple left-edge/top-edge reference (conceptually two clicks: somewhere on the left edge and somewhere along the top) to anchor/place the square;
6. account mathematically for any small residual tilt using the saved orientation transform where useful;
7. preview the resulting crop;
8. accept/save to the working output or retry.

Cropping slightly into nonessential plate edges is preferable to introducing extra blank space, which is why round-down is the default.

## Square default, not hard limitation

A square crop is the default for the first useful implementation. Keep the result/options extensible enough that another aspect/box shape can be selected later without rebuilding the whole component.

Do not add complexity for arbitrary shapes before the square workflow is proven.

## Source/output behavior

- raw source remains untouched;
- operate on the working/orientation-corrected image;
- preview is non-destructive;
- accepted crop writes an explicit working/derived image;
- preserve project image identity/UID across the transformation;
- persist crop geometry/transform as reusable project state where practical;
- rerun/reset must be possible.

## Quick verification/hotkey behavior

The production integration should support a very fast visual gate between crop proposal and save, ideally hotkeyable:

- accept/save crop;
- retry/reselect crop.

Do not require a multi-dialog workflow for every plate if a compact preview + two actions is sufficient.

## Relationship to later grid registration

This preprocessing happens before the existing four-click culture-grid route.

The four-click route should receive the accepted cropped working image. Crop/orientation preprocessing remains optional enough that failure must not require redesigning grid registration.

Do not derive culture coordinates here.

## Result contract

Conceptually:

`derive_plate_crop(image, orientation_result, points, options) -> CropResult`

The result should include:

- image UID/reference;
- crop rectangle/shape;
- default/actual rounding increment;
- source dimensions;
- accepted/review state;
- output path when saved;
- enough transform information for later coordinate mapping if needed.

## Mini-app

A focused applet may:

- load one working image;
- show the orientation-corrected plate;
- collect side/boundary and anchor clicks;
- show proposed square/box overlay;
- preview crop;
- accept/retry;
- save result/project state.

Keep it independent of V10 parsing and four-click grid logic.

## Privacy/testing

Gemini development uses synthetic/public images only. Required tests should include known image extents/tilts so crop math can be proven without confidential images.

## Required proofs

1. derive square from known synthetic plate extent;
2. round down to nearest 50 by default;
3. configurable alternative rounding increment;
4. place crop using left/top references;
5. consume a small residual orientation transform correctly;
6. preview without file modification;
7. accept writes derived working output while raw/source remains unchanged;
8. retry/reset works;
9. crop geometry persists in a small result/state object.

## Out of scope

- automatic colony/grid detection;
- visibility/levels adjustment;
- strain/culture crop export;
- annotation rendering;
- V10 parsing itself;
- replacing the four-click grid route.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface:
- Tests:
- Dependencies:
- Crop/rounding behavior:
- Preview/accept behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
