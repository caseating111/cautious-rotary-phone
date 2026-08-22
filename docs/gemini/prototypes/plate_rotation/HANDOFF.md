# Whole-plate orientation prototype handoff

Status: Planned

## Goal

Build an optional **preprocessing** component that straightens the overall plate/image orientation before the current four-click grid-registration step.

This is separate from grid/colony alignment. Its purpose is visual normalization of the plate as a physical object so later cropping/annotation/processing starts from a less crooked image.

The working four-click route remains authoritative for actual culture/grid coordinates. Failure or uncertainty in this preprocessing step must **never block** that route.

See `docs/gemini/FUTURE_WORKFLOW.md` and `docs/development/PROJECT_ASSET_CONTRACT.md`.

## Do not use the colony ROI-box plugin

The ROI 1-click rotated-rectangle tool is useful for the current fixed-size colony-center workflow but adds no value here. Whole-plate orientation only needs a reliable reference angle.

Do **not** reuse/adapt the 108x108 ROI-box interaction for plate straightening.

## Preferred first route: two crosshair point clicks

The first practical prototype should favor a reliable two-click route over a large automatic CV system.

Preferred interaction:

1. display one working image;
2. switch to a precise crosshair/point cursor;
3. instruct the user to click **two well-separated points along one long trustworthy straight plate edge**;
4. first click places visible marker A;
5. second click places visible marker B and a line between A/B;
6. calculate the edge angle from those coordinates;
7. convert that to the correction angle needed to make the chosen edge horizontal (or another explicitly selected reference convention);
8. show a non-destructive corrected preview;
9. provide fast `Accept`, `Retry`, and `Skip/Cancel` actions;
10. on Accept, write/update a derived working image and persist the result/transform.

A native straight-line drag may be offered as an equivalent alternative if Fiji/ImageJ makes that route materially simpler, but the default should remain conceptually **two precise points defining one line**.

The markers/line should stay visible until accept/retry so the user can see exactly what was measured.

Primary conceptual interface:

`capture_plate_orientation(points, image_geometry, options) -> RotationResult`

## Why this route

- only angle is needed;
- two distant points along a plate edge average out small local irregularities better than clicking a tiny ROI;
- crosshair placement is fast and easy to retry;
- no colony or grid assumptions are required;
- no automatic detector needs to be trusted before the preprocessing app is useful.

## Angle/result semantics

Choose one deterministic convention and test it explicitly:

- define clockwise/counter-clockwise sign;
- define whether the stored value is observed tilt or correction-to-apply;
- save the original two reference points as evidence;
- store method/version so downstream transforms are reproducible.

`RotationResult` should contain at least:

- image UID/reference;
- selected points A/B;
- observed edge angle;
- correction angle;
- angle convention;
- method (`two_point`, future automatic method name, etc.);
- accepted/skipped/manual-review state;
- source/output dimensions/path reference;
- enough transform information for later plate-crop/grid coordinate-space handling.

## Source/output behavior

- raw source images remain untouched;
- operate on/create a working derivative;
- preview is non-destructive;
- accepted orientation becomes reusable project state so later crop/grid steps do not request the same clicks;
- rerun/reset remains possible;
- changing an accepted orientation after downstream geometric work exists should mark dependent crop/grid state stale rather than silently applying mismatched coordinates.

## Optional automatic estimator later

Automatic physical-plate orientation remains useful as a later convenience, but do not let it delay the reliable two-point route.

Before custom CV, compare a bounded set of mature routes such as Fiji/ImageJ edge/deskew/shape tools, OpenCV minimum-area rectangle/Hough/contour facilities, and scikit-image edge/Hough methods.

A good-enough automatic suggestion plus immediate manual confirmation/fallback is preferable to a complex brittle detector. Stop when the practical route is fast and reliable enough; do not spend disproportionate effort eliminating two easy clicks.

Automatic failure/low confidence must fall back to the point-based route and **must never make four-click grid registration unavailable**.

## Mini-app role

The focused mini-app may:

- display one working image;
- collect the two crosshair points;
- show markers/reference line;
- preview corrected orientation;
- accept/retry/skip;
- optionally offer automatic estimate later;
- save `RotationResult` and derived working output.

It should not implement V10 parsing, whole-plate crop selection, culture/grid registration, visibility adjustment or annotation.

## Privacy/test data

Use synthetic/public images only for Gemini development. Do not inspect confidential plate pixels.

## Required proofs

1. modest clockwise synthetic tilt -> correct opposite correction;
2. modest counter-clockwise tilt -> correct opposite correction;
3. near-zero tilt;
4. visible two-point markers/reference line;
5. preview/accept/retry without modifying raw source;
6. saved result can be consumed by later crop step;
7. skip leaves downstream grid route valid;
8. optional straight-line-drag implementation, if included, matches the same sign convention.

## Success criteria

The prototype is `Proven` once a small two-point crosshair app/API reliably captures and applies orientation to derived working images, persists a clear transform/result, remains optional/non-blocking for four-click grid registration, and has targeted synthetic tests. Automatic estimation is future/bonus work, not required for first proof.

## Completion record

- Branch:
- Commit:
- Interface:
- Interaction implemented:
- Angle convention:
- Preview/accept behavior:
- Tests:
- Dependencies:
- Optional automatic methods researched:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
