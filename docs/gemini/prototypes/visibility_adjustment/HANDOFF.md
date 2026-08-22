# Visibility adjustment / manual-review preprocessing handoff

Status: Planned

## Goal

Build a focused whole-plate visibility-adjustment component for **human visual comparison**, using the already-registered culture grid as the measurement ROI while applying the chosen adjustment to the entire working image.

This replaces the old manual Photoshop levels step and should remain separate from quantitative/scientific measurement images unless explicitly designed otherwise.

## Workflow position

This step happens after grid coordinates are known. The existing 2x CLAHE alignment preview is already good enough for alignment and does not need to become the final presentation adjustment.

Desired sequence:

1. consume an existing processed/working whole-plate image and saved grid coordinates;
2. derive adjustment statistics from the overall grid area/ROI;
3. calculate/apply a visibility adjustment to the **entire image**;
4. show a fast preview;
5. user accepts or marks the image for manual adjustment;
6. accepted result is written to a processed parent folder while preserving subfolder structure;
7. manual-review list can later open flagged images directly in ImageJ/Fiji or the chosen tool.

## Measurement ROI versus application area

The grid region is the source for adjustment statistics because it represents the biologically relevant plate area and avoids excessive surrounding blank/background influence.

The resulting display adjustment should apply to the entire image for visual consistency.

Do not crop or adjust only the ROI unless a future explicit mode requests it.

## Candidate adjustment research

Before custom algorithms, research mature Fiji/ImageJ plugins, built-ins and established Python/scikit-image/OpenCV/Pillow methods suitable for robust display normalization across plate images.

Potential families to compare may include:

- percentile/robust min-max display scaling;
- background-referenced black point plus high-percentile white point;
- gamma/contrast adjustments;
- CLAHE/local contrast methods;
- established illumination/background correction where visually useful;
- combinations of simple robust statistics plus one mature adjustment primitive.

Do not assume the current 2x CLAHE alignment settings are the final presentation method. They are fit for alignment, not necessarily final visual output.

Keep research bounded and select a practical small set for later manual comparison rather than exhaustive benchmarking.

## Manual-review fallback

Some images will not respond well to one automatic adjustment. The default workflow should therefore support two fast decisions, ideally hotkeyable:

- **Approve adjustment** — save/continue;
- **Mark for manual** — add image to a review list and continue batch processing.

Do not make one difficult image block the rest of the batch.

The manual-review list should retain image UID/path and reason/state, and a later controller action should be able to open flagged files directly in ImageJ/Fiji or another selected editor.

## Preview and source safety

- preview must be non-destructive;
- raw/original images remain unchanged;
- processed visibility-adjusted images are explicit derived outputs;
- preserve project UID and relative folder structure;
- record the adjustment method/parameters/preset used for reproducibility;
- allow rerun/reprocess without destroying the prior raw source.

## Presets and batch behavior

Reusable presets are useful when one adjustment method/settings works across many related images, but the user should not have to create Photoshop-like templates.

A preset may store:

- adjustment method;
- percentiles/thresholds/gamma/etc.;
- ROI-statistic options;
- any background/high-point strategy;
- review thresholds if meaningful.

Batch mode may apply one preset across selected images while still offering per-image approve/manual-review decisions.

## Processed crop integration

Processed strain/culture crops should not require alignment to be rerun.

Once both of these exist:

1. saved grid coordinates for an image;
2. the corresponding processed whole-plate image;

crop export should be able to run later at any time using those coordinates. Raw/unprocessed crop exports and processed crop exports should live under distinguishable parent outputs.

This handoff does not reimplement the crop-export macro; it defines the state/integration expectation.

## Interface

Conceptually:

`adjust_plate_visibility(image, grid_coordinates, preset) -> AdjustmentResult`

Result should include:

- source image UID/reference;
- method and parameters;
- ROI/statistics used;
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

Keep the raw/working source and adjustment metadata available separately.

## Required proofs

1. grid ROI determines statistics while entire synthetic image is adjusted;
2. source remains unchanged;
3. non-destructive preview;
4. approve saves processed output with method metadata;
5. mark-for-manual creates a usable review entry without blocking batch;
6. presets can be reused;
7. processed-image crop integration can consume the existing grid later without realignment;
8. folder/subfolder identity is preserved.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface:
- Methods researched/compared:
- Selected default/presets:
- Tests:
- Dependencies:
- Review-queue behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
