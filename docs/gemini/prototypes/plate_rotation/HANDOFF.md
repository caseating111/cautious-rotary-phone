# Whole-plate rotation prototype handoff

Status: Planned

## Goal

Research and prototype **physical whole-plate rotation/orientation estimation** independently of the colony/grid alignment system. The purpose is to estimate the overall plate/image rotation from the plate itself so a downstream workflow can optionally deskew the entire plate before or alongside logical grid alignment.

Primary interface:

`estimate_plate_rotation(path) -> RotationResult`

This is a research/proof component, not a replacement for the current authoritative manual four-click grid alignment route.

## Critical separation from grid alignment

Keep these concepts separate:

- **whole-plate physical rotation:** estimate the orientation of the plate/image as a physical object;
- **grid/colony alignment:** determine the logical colony/grid geometry and reference positions.

A whole-plate rotation estimate may later make images easier to view/process, but it must not silently override or remove the current manual alignment authority.

Do not modify the production Fiji four-click alignment, ROI tool, AHK lifecycle, or controller runtime in this branch.

## Mature-tool-first research requirement

Before writing custom computer-vision logic, search and compare established routes, including where relevant:

- Fiji/ImageJ built-ins and update-site plugins;
- ImageJ/Fiji deskew, edge, threshold, Hough/line/rectangle, registration, template, or shape-analysis tooling;
- OpenCV contour/min-area rectangle/Hough/line-orientation facilities;
- scikit-image edge/Hough/region/transform facilities;
- other mature scientific-image packages or desktop tools that already estimate rectangular-object orientation;
- combinations of simple preprocessing plus a mature estimator.

Search exact plate-orientation solutions first, then functionally equivalent rectangular-object/document/tray/plate deskew methods if exact solutions are weak.

Record meaningful searches/findings in `docs/research/` if they materially affect the route, following the shared research-memory policy.

## Privacy/test data

- Never inspect or commit real confidential plate images as part of Gemini prototype development.
- Use synthetic images and, where genuinely helpful, public/non-confidential example images.
- Keep test fixtures small and clearly synthetic/public.
- Do not derive conclusions about production-image quality from synthetic-only testing; record that limitation explicitly.

## Desired result contract

`RotationResult` should be able to represent at least:

- estimated angle in degrees;
- method used;
- optional confidence/quality score where the method supports a meaningful one;
- `needs_manual_review` or equivalent;
- concise non-pixel diagnostics explaining weak/ambiguous estimates;
- no requirement to store derived image pixels in the result.

The estimator should be callable independently of any GUI.

## Practical behavior

Prefer a robust modest estimator over a complex "fully automatic" vision system. It is acceptable to return low confidence/manual review when the plate boundary/orientation is not reliably detectable.

Potential practical routes may include:

- finding the dominant plate/tray rectangle or long outer edges;
- threshold/edge preprocessing followed by a mature minimum-area rectangle or line-angle estimator;
- using multiple candidate edges and robustly combining their orientation;
- allowing a small manual confirmation/fallback later if automatic estimation is uncertain.

Do not assume colonies themselves form reliable straight lines for this component; this estimator is intended to use the plate/image structure rather than the logical colony grid where possible.

## Angle conventions

Choose and document one deterministic convention, for example:

- positive/negative direction;
- whether returned angle means "observed rotation" or "correction to apply";
- expected canonical range (for example around -45..45 or another justified range).

Tests must make this convention explicit so later integration does not reverse the sign accidentally.

## Optional corrected-image proof

The core contract is angle estimation. A small helper may optionally demonstrate applying the returned correction with Pillow/OpenCV/Fiji to a **derived** synthetic output, but do not make image rewriting the estimator's core responsibility.

Source files must remain unchanged.

## Failure/ambiguity behavior

Do not return a confident-looking arbitrary angle when evidence is weak. Detect/report cases such as:

- no usable plate boundary/edge structure;
- several incompatible dominant angles;
- nearly square/ambiguous geometry where orientation is not identifiable;
- strong unrelated image borders or labels dominating the detector;
- estimate outside sensible configured bounds.

A clean `needs_manual_review=true` result is preferable to brittle automatic correction.

## Relationship to later workflow

A later integrator may choose to use the estimate to:

- rotate a derived working image before grid alignment;
- suggest/preview a correction for user acceptance;
- normalize visual orientation across images;
- pass the transform to annotation/composition tools.

That integration decision belongs to `workflow-C` later. This prototype should remain a narrow estimator/result contract.

## Mini-app option

A tiny evaluation applet is acceptable if useful for comparing methods. It may:

- load a synthetic/public image;
- show the estimated angle/method/confidence;
- preview a derived corrected image;
- allow switching among a small number of mature-method candidates.

Do not build a general image editor or duplicate main-controller functionality.

## Required prototype comparison

Compare a small number of promising mature approaches rather than committing immediately to the first custom method. Prefer evidence such as:

- correctness on known synthetic rotations;
- stability across contrast/background variation;
- runtime/setup burden;
- dependency maturity;
- ease of later integration on Windows/Python 3.14/Fiji where applicable.

Stop once a practical best-supported route is established; do not turn this into exhaustive CV benchmarking.

## Required synthetic proofs

At minimum include images with known rotations and demonstrate:

1. near-zero rotation;
2. modest clockwise rotation;
3. modest counter-clockwise rotation;
4. contrast/background variation;
5. an intentionally ambiguous/failed case that returns manual-review/low-confidence rather than a misleading result;
6. deterministic angle-sign convention.

## Out of scope

- current four-click Fiji/grid alignment implementation;
- colony segmentation;
- V10 parsing;
- annotation rendering;
- live confidential image testing;
- automatic cropping/grid derivation;
- replacing manual alignment authority.

## Success criteria

The prototype is `Proven` when:

1. mature approaches have been compared with concise evidence;
2. one practical default route is selected or a small fallback chain is justified;
3. `estimate_plate_rotation(path) -> RotationResult` works on synthetic/public examples;
4. angle convention is explicit and tested;
5. weak cases are reported rather than silently corrected;
6. source images are not modified;
7. targeted tests pass;
8. the implementation remains independent of current Fiji/AHK/controller runtime.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface: `estimate_plate_rotation(path) -> RotationResult`
- Methods researched/compared:
- Selected method/fallback:
- Angle convention:
- Tests:
- Dependencies:
- Proven synthetic/public cases:
- Failure/manual-review behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
