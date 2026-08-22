# Intended future workflow / mini-app map

This document records the intended end-to-end user workflow so isolated Gemini prototypes fit together later. It is a workflow contract, not an instruction to implement everything in one GUI or branch.

The current working four-click Fiji grid route is a valuable proven component and should be integrated around, not casually replaced.

## Architecture

Prefer a lightweight overall project/controller GUI that owns project selection/shared state and launches focused mini-apps or actions. Separate agents may implement independent components on child branches when their file/interface boundaries do not overlap.

Core reusable state should include:

- canonical V10-derived project/image identity;
- raw/working/processed/annotated file mappings;
- whole-plate orientation/crop transforms;
- logical `PlateLayout`;
- measured pixel grid/spot coordinates;
- visibility-adjustment result/preset;
- annotation preset/result;
- crop/matrix output metadata.

Do not make later actions rerun earlier manual steps when the required state already exists.

## 1. V10 metadata + project setup

User fills V10 appropriately and exports/loads the structured metadata. The V10 adapter produces canonical project state.

A setup step prepares the project folder structure and expected outputs without requiring all expected images to exist physically.

The currently working simple CSV workflow remains a simpler baseline; it does not need V10 Set/annotation-set semantics retrofitted into it.

## 2. Optional UID-safe working-copy renaming

Raw images such as `image1`, `image2`, etc. remain unchanged in the `raw/` parent structure.

Optionally duplicate them into a `working/` parent tree and apply V10 working filenames. Image UID/session identity prevents similar names from being confused.

At project root, write a small human-readable conversion map such as `image1.jpg -> <working name>.jpg`, grouped by experiment and Set with clear dividers and UID/context where useful.

Renaming is optional; later processing must still be possible with generic raw names when canonical identity is known.

## 3. Whole-plate orientation preprocessing

Before grid registration, optionally straighten the physical plate/image.

Preferred reliable first route: a small two-click orientation interaction that derives correction angle and creates/updates the working image. Save orientation state for the next crop step.

Automatic mature-tool-based orientation estimation may be explored later but must fall back cleanly and must never block the working four-click grid route.

## 4. Whole-plate crop preprocessing

On the orientation-corrected working image:

- estimate overall plate size from four boundary/side clicks or equivalent;
- default to a square crop;
- round crop size down to nearest 50 px by default, with configurable increment/behavior;
- use a left-edge and top-edge reference to place the crop;
- account for small residual orientation mathematically where useful;
- provide a fast preview/accept/retry gate;
- save accepted working crop while preserving source/raw files and identity.

## 5. Four-click grid registration and culture crop availability

Run the existing proven four-click grid route next. It determines actual culture spot/grid coordinates.

Important architectural requirement: **alignment/registration and crop export must be separable**.

The user should be able to:

- register all grids first without exporting crops;
- persist grid coordinates;
- export raw/unprocessed crops immediately or later;
- after visibility processing, export processed crops later using the same saved coordinates;
- never rerun alignment merely because crop export occurs at a different workflow stage.

Selection should ultimately support all strains, first/default selection, or selected strains as appropriate to the production UI.

Optional output organization: crop exports may create subfolders per Condition (e.g. CONTROL, CAFFEINE) under the relevant parent. Raw/unprocessed and processed crop outputs should have distinct parent locations.

This area is currently production/Codex-owned; Gemini prototypes should consume the saved-grid contract rather than duplicate the working crop macro unless explicitly assigned later.

## 6. Whole-plate visibility adjustment for human comparison

Once grid coordinates exist, use the overall grid area as the ROI from which adjustment statistics are derived, while applying the resulting display adjustment to the entire image.

The existing 2x CLAHE alignment preview is fit for alignment but is not automatically assumed to be the final presentation adjustment.

Research mature Fiji/ImageJ/plugins/Python methods for robust visualization. Expect manual trials before choosing defaults.

Batch review should support fast actions:

- approve automatic adjustment;
- mark for manual adjustment and continue.

Maintain a manual-review queue that can later open flagged images directly in ImageJ/Fiji or another selected tool.

## 7. Export processed whole plates

Accepted visibility-adjusted images go to a `processed` parent while preserving relevant experiment/date/condition subfolder structure.

Raw/working source images remain available separately.

## 8. Optional processed-image crop export

At any time after both saved grid coordinates and processed whole-plate images exist, allow the existing crop engine to export processed strain/culture crops.

This action should check only that required coordinate state and processed images exist; it should not require rerunning the earlier workflow in order.

## 9. Automatic whole-plate annotation

By this stage the workflow knows:

- exact grid/spot coordinates;
- logical strain/row identity from V10/PlateLayout;
- which strains occur on each image and where;
- experiment/Set/date/condition/etc. metadata.

Therefore annotation placement should be automatic from coordinates rather than using Photoshop-style templates or requiring per-plate manual label alignment.

Support reusable presentation presets for font, size, color, orientation and offsets. Strain labels should support the established 90-degree-clockwise convention (top of text facing right); vertical labels remain upright by default.

Provide a fast non-destructive preview so fonts/labels/spacing/offsets can be inspected before final render.

Figure descriptions and dates should be generated from structured metadata/preset rules, with optional manual override where appropriate.

Final annotated outputs go to an `annotated` parent while preserving subfolder structure.

## 10. Export annotated whole plates

Render/export annotated derived images without modifying processed source images. Preserve metadata/preset information sufficient to reproduce the presentation if needed.

## 11. Matrices/compositions may begin once crops exist

Matrix generation does not need to wait for whole-plate annotation. Once required individual crops exist, matrices can be generated independently.

Composition should support structured selection but also practical manual overrides for small quick figures.

Important enhancement: crop tier/position selection must be per selected strain/image, not global-only. A matrix should be able to combine, for example, WT1 `top` with STRAIN2 `low` in the same output.

## Dependencies and non-dependencies

- V10 metadata/project identity is foundational for the richer future workflow.
- orientation preprocessing -> plate crop preprocessing -> grid registration is the preferred image-preprocessing order, but orientation/crop helpers must not make grid registration unusable when skipped.
- saved grid coordinates are foundational for automatic annotation, ROI-based visibility adjustment, and later crop export.
- visibility-adjusted whole plates are the default annotation source, but annotation rendering should remain a separate derived-output operation.
- matrix generation depends on the required crop files, not on whole-plate annotation.

## UX principle

Prefer short, focused interactions and reusable state. A user should not repeatedly click/align/re-enter information that the project already knows.

Automatic placement/calculation is preferred where the grid/metadata makes it deterministic. Manual fallback/review is valuable for exceptions, but should not become the normal burden merely to avoid implementing straightforward deterministic behavior.
