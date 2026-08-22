# Whole-plate orientation prototype handoff

Status: Planned

## Goal

Build an optional **preprocessing** component that straightens the overall plate/image orientation before the current four-click grid registration step.

This is separate from grid/colony alignment. Its purpose is visual normalization of the plate as a physical object so later cropping/annotation/processing starts from a less crooked image.

The working four-click route remains authoritative for actual culture/grid coordinates. Failure or uncertainty in this preprocessing step must **never block** that route.

## Preferred first route: simple two-click orientation

The first practical prototype should favor a reliable interactive two-click route over a large automatic CV system.

Expected interaction:

1. user clicks two suitable points defining an intended horizontal or vertical plate reference edge/axis;
2. derive the plate tilt angle from those points;
3. rotate a **working copy/derived image**, not the raw source;
4. return/save the angle/transform for the following plate-crop step;
5. allow quick accept/retry if the result is visibly poor.

The exact reference convention should be made explicit in the mini-app/UI so the user knows what two points to click.

Primary conceptual interface:

`capture_plate_orientation(points, image_geometry, options) -> RotationResult`

A later automatic estimator may share the same `RotationResult` contract.

## Optional automatic estimator

Automatic physical-plate orientation remains useful as a later convenience, but do not let it delay the reliable two-click route.

Before writing custom CV, compare mature Fiji/ImageJ, OpenCV, scikit-image or other established rectangle/edge/deskew methods. Stop once a practical approach is found; perfect automation is not required.

Automatic behavior should:

- estimate plate/image orientation from outer plate/image structure rather than colony-grid assumptions where practical;
- provide confidence/manual-review information;
- fall back cleanly to the two-click interaction when uncertain;
- never silently override a user-accepted manual orientation.

## Critical separation from grid alignment

Keep these concepts separate:

- **whole-plate orientation preprocessing:** straighten the physical plate/image;
- **grid registration:** determine the culture spot/grid coordinates using the working four-click route.

Orientation preprocessing happens earlier. Grid registration must still work when preprocessing is skipped entirely.

Do not modify the production Fiji four-click ROI/grid logic from this branch.

## Result contract

`RotationResult` should represent at least:

- correction angle in degrees;
- angle convention/sign;
- method (`two_click`, automatic method name, etc.);
- source image identity/UID where applicable;
- accepted/needs-review state;
- optional confidence for automatic methods;
- non-pixel diagnostics;
- enough transform information for the plate-crop step to account for any known orientation correction.

Do not require the result itself to embed image pixels.

## Angle conventions

Choose one deterministic convention and test it explicitly:

- define clockwise/counter-clockwise sign;
- define whether the result is observed tilt or correction-to-apply;
- keep downstream crop/annotation consumers from reversing the sign accidentally.

## Source/output behavior

- raw source images remain untouched;
- preprocessing operates on/creates a working image;
- optional preview should be non-destructive;
- accepted orientation can be persisted as project state so later steps do not ask for the same points again;
- rerun/reset must remain possible.

## Mini-app role

A focused mini-app may:

- display one working/source image;
- collect the two clicks;
- preview corrected orientation;
- accept/retry/reset;
- optionally offer an automatic-estimate button later;
- save the `RotationResult`/working output for the crop step.

It should not implement V10 parsing, grid registration, visibility adjustment or annotation.

## Privacy/test data

Use synthetic/public images only for Gemini development. Do not inspect confidential plate pixels.

## Mature-tool-first automatic research

If/when automatic estimation is explored, compare only a bounded set of mature routes such as:

- Fiji/ImageJ edge/deskew/shape tools or established plugins;
- OpenCV contour/min-area rectangle/Hough facilities;
- scikit-image edge/Hough/region facilities;
- simple preprocessing plus those estimators.

A good-enough automatic suggestion plus immediate manual fallback is preferable to a complex brittle detector.

## Out of scope

- culture/grid-coordinate determination;
- replacing the four-click route;
- plate-size/crop-box selection (separate crop prototype);
- visibility adjustments;
- annotation rendering;
- V10 parsing.

## Required proofs

1. synthetic image with modest clockwise tilt -> correct two-click correction;
2. counter-clockwise tilt -> correct correction/sign;
3. near-zero tilt;
4. preview/accept/retry without modifying raw source;
5. saved result can be consumed by a later crop step;
6. skipping orientation leaves downstream grid route conceptually valid;
7. if automatic method is prototyped, weak case falls back/manual-review rather than blocking.

## Success criteria

The prototype is `Proven` once a small two-click app/API reliably captures and applies orientation to derived working images, persists a clear transform/result, remains optional/non-blocking for four-click grid registration, and has targeted synthetic tests. Automatic estimation is bonus/future work, not required for first proof.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface:
- Angle convention:
- Preview/accept behavior:
- Tests:
- Dependencies:
- Optional automatic methods researched:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
