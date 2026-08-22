# Visibility adjustment / manual-review preprocessing handoff

Status: Planned

## Goal

Build a focused whole-plate visibility-adjustment component for **human visual comparison**, using the already-registered culture grid as the measurement ROI while applying the chosen adjustment to the entire working image.

This replaces the old manual Photoshop levels step and should remain separate from quantitative/scientific measurement images unless explicitly designed otherwise.

See `docs/gemini/FUTURE_WORKFLOW.md` and `docs/development/PROJECT_ASSET_CONTRACT.md`.

## Workflow position

This step happens after grid coordinates are known. The existing 2x CLAHE alignment preview is already good enough for alignment and does not need to become the final presentation adjustment.

Desired sequence:

1. consume a working whole-plate image and saved grid coordinates;
2. derive the overall grid ROI plus any useful background-reference region;
3. calculate adjustment statistics;
4. apply the resulting visibility adjustment to the **entire image**;
5. show a fast non-destructive preview;
6. user accepts or marks the image for manual adjustment;
7. accepted result is written to a processed parent folder while preserving subfolder structure;
8. manual-review list can later open flagged images directly in ImageJ/Fiji or the chosen tool.

## Measurement ROI versus application area

The saved grid region is the primary biologically relevant ROI for foreground/high-point statistics. The resulting display adjustment applies to the entire image for visual consistency.

Do not crop or adjust only the ROI unless a future explicit mode requests it.

## Specific background-aware candidate to test

A previously desired practical route should be included among the first candidates rather than rediscovered later:

1. derive the total-grid bounding/shape ROI from saved spot coordinates;
2. derive a nearby **outside-grid background region** (for example a border/annulus around the total-grid ROI, clipped to valid image bounds and excluding the grid itself);
3. estimate a robust black/background value from that outside-grid region rather than from the colonies;
4. estimate a robust high/white value from the inside-grid region, e.g. a configurable high percentile rather than absolute maximum;
5. compute one global display transform from those statistics;
6. apply that transform to the entire whole-plate image;
7. preview and allow approve/manual fallback.

This directly supports visual consistency while reducing influence from colonies on the black point and from blank outer image area on the white/high point.

Do not hard-code this as the only method until it has been compared manually against a few mature alternatives.

## Candidate adjustment research

Before custom algorithms, research mature Fiji/ImageJ plugins, built-ins and established Python/scikit-image/OpenCV/Pillow methods suitable for robust display normalization across plate images.

Compare only a bounded practical set, including:

- background-aware black point + inside-grid high percentile as described above;
- robust percentile/min-max display scaling;
- gamma/contrast adjustment after robust endpoints;
- CLAHE/local contrast methods where visually beneficial;
- established illumination/background correction plugins/methods;
- simple combinations of robust statistics plus one mature adjustment primitive.

Do not assume current 2x CLAHE alignment settings are the final presentation method. They are fit for alignment, not necessarily final visual output.

Stop once a small set of good candidates is ready for user visual comparison; do not perform exhaustive benchmarking.

## Manual-review fallback

Some images will not respond well to one automatic adjustment. Default workflow should therefore support two fast decisions, ideally hotkeyable:

- **Approve adjustment** — save/continue;
- **Mark for manual** — add image to a review list and continue batch processing.

Do not make one difficult image block the rest of the batch.

The manual-review list should retain image UID/path, candidate preset/method, and optional reason/state. A later controller action should open flagged files directly in ImageJ/Fiji or another selected editor.

## Preview and source safety

- preview must be non-destructive;
- raw/original images remain unchanged;
- processed visibility-adjusted images are explicit derived outputs;
- preserve project UID and relative folder structure;
- record method/parameters/preset and relevant ROI statistics for reproducibility;
- allow rerun/reprocess without destroying prior sources;
- intensity-only adjustment should preserve image geometry so saved grid coordinates remain valid.

## Presets and batch behavior

A preset may store:

- adjustment method;
- inside-grid percentile/high-point settings;
- outside-grid background-region definition and robust statistic;
- gamma/contrast parameters;
- any CLAHE/background-correction options;
- review thresholds if meaningful.

Batch mode may apply one preset across selected images while still offering per-image approve/manual-review decisions.

## Processed crop integration

Processed strain/culture crops should not require alignment to be rerun.

Once both exist:

1. saved grid coordinates for an image;
2. the corresponding processed whole-plate image;

crop export should be able to run later at any time using those coordinates. Raw/unprocessed crop exports and processed crop exports should live under distinguishable parent outputs.

This handoff does not reimplement the crop-export macro; it defines the state/integration expectation.

## Interface

`adjust_plate_visibility(image, grid_coordinates, preset) -> AdjustmentResult`

Result should include:

- source image UID/reference;
- method and parameters;
- grid ROI and background-reference definition/statistics;
- preview/final output path as applicable;
- accepted/manual-review state;
- warning/diagnostic text;
- no mutation of canonical scientific metadata.

## Mini-app

A focused applet may:

- receive/select a working image and saved grid;
- show adjustment preview;
- switch among a small number of presets/method candidates;
- approve or mark for manual;
- move automatically to the next image;
- open/export the manual-review queue later.

Do not duplicate V10 parsing or grid alignment inside it.

## Data/scientific safety

These outputs are for human visualization/presentation. Do not silently use display-adjusted pixels for quantitative colony measurements or scoring.

Keep raw/working source and adjustment metadata separately.

## Required proofs

1. saved grid derives foreground/statistics ROI;
2. outside-grid region can derive robust background/black statistic;
3. selected transform applies to entire synthetic image;
4. source remains unchanged;
5. preview is non-destructive;
6. approve saves processed output with method metadata;
7. mark-for-manual creates usable review entry without blocking batch;
8. presets can be reused;
9. processed-image crop integration consumes existing grid later without realignment;
10. folder/subfolder identity is preserved.

## Completion record

- Branch:
- Commit:
- Interface:
- Methods researched/compared:
- Selected default/presets:
- Tests:
- Dependencies:
- Background/grid ROI behavior:
- Review-queue behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
