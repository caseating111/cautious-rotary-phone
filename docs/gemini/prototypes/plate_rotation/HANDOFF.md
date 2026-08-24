# Whole-plate orientation prototype handoff

Status: INTEGRATED

Integrated on `workflow-integrated` at `c31d4f1`. The shared core and V10 applet GUI implement line-drag proposal, non-destructive preview, Accept/Retry/Skip, derivative output, transform provenance, and project-state persistence.

## Goal

Build an optional **preprocessing** mini-app that straightens the overall plate/image before whole-plate cropping and before the current four-click culture-grid registration.

This is physical plate straightening, not culture/grid alignment. The proven four-click route remains authoritative for culture coordinates, and orientation preprocessing must never block it.

See `docs/gemini/FUTURE_WORKFLOW.md` and `docs/development/PROJECT_ASSET_CONTRACT.md`.

## Required interaction: one straight-line drag

Do **not** use the ROI 1-click rotated-rectangle/108x108 colony plugin here. It solves a different problem.

The preferred first implementation is one ordinary straight-line drag along a long, visually trustworthy **top or bottom physical plate edge**.

Routine user flow:

1. Open the current working whole-plate image.
2. Activate a normal straight-line/crosshair line tool.
3. User drags one line along the top or bottom plate edge, choosing whichever is clearer.
4. The line remains visibly overlaid so the measured reference is obvious.
5. Calculate the observed edge angle from the line endpoints.
6. Calculate the correction required to make that edge horizontal.
7. Show a non-destructive corrected preview.
8. Fast actions: `Accept`, `Retry`, `Skip`.
9. On Accept, create/update the working derivative and persist the orientation transform/result.

Do not add separate top-edge/bottom-edge dialogue branches. Both represent the same horizontal-reference calculation. The user simply chooses whichever long horizontal plate edge is easiest to see.

A line drag is preferred over two separate point clicks because it expresses the actual operation directly, requires one interaction rather than two, and uses mature Fiji/ImageJ line-selection behavior where available.

## Result/state

Conceptual interface:

`capture_plate_orientation(line, image_geometry, options) -> OrientationResult`

Persist at least:

- image UID/reference;
- line endpoints in the source coordinate space;
- observed angle;
- correction angle;
- explicit clockwise/counter-clockwise convention;
- method/version (`manual_horizontal_edge_line` or equivalent);
- accepted/skipped state;
- source and output dimensions/path references;
- transform sufficient to map later crop/grid state correctly.

The accepted orientation is **per image**. Do not assume the same translation/position for another image merely because plates have the same size.

## Source/output behavior

- raw image remains untouched;
- operate on/create a working derivative;
- preview is non-destructive;
- rerun/reset is allowed;
- Skip leaves downstream crop/four-click routes available;
- changing orientation after downstream geometric state exists must mark dependent crop/grid state stale or explicitly transform it; never silently reuse incompatible coordinates.

## Relationship to crop calibration

Straightening and crop placement are distinct:

- orientation stores a per-image rotational transform;
- crop-size calibration may be reusable across multiple similarly imaged plates;
- crop **position/translation remains per image** because the plate may appear at a different x/y offset in each camera image.

Do not infer that a reusable crop size implies a reusable crop center.

## Optional automatic estimator later

Automatic physical-plate orientation can be explored later as an optional suggestion, but must not delay this reliable one-line route.

Research mature Fiji/ImageJ, OpenCV or scikit-image deskew/edge/rectangle methods before custom CV. A useful automatic suggestion with immediate manual fallback is enough; do not turn this into a large detector project.

Automatic failure/low confidence must fall back to the one-line route and must never make four-click grid registration unavailable.

## Mini-app boundary

This applet may:

- display one working image;
- collect/show the straight-line reference;
- preview corrected orientation;
- accept/retry/skip;
- save `OrientationResult` and the working derivative.

It should not parse V10, determine crop size/placement, perform four-click grid registration, adjust visibility, or annotate.

## Required synthetic proofs

1. modest clockwise tilt -> correct opposite correction;
2. modest counter-clockwise tilt -> correct opposite correction;
3. near-zero tilt;
4. top-edge and bottom-edge lines obey the same horizontal-reference rule;
5. preview/accept/retry/skip are non-destructive to raw source;
6. saved orientation can be consumed by the plate-crop step;
7. changing one image's orientation does not imply another image's crop translation;
8. four-click route remains usable when orientation is skipped.

## Success criteria

`Proven` means one straight-line drag reliably produces a correct, reusable orientation transform and derived working image with fast preview/accept/retry/skip behavior and targeted synthetic tests. Automatic orientation is optional future work.

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
