# Future workflow functional contract

This document records the intended end-to-end workflow after the current basic CSV route is stable. It exists so current Codex integration work and parallel Gemini mini-app prototypes converge on the same product rather than inventing incompatible workflows.

Do not interpret this document as permission to implement future stages during a bounded stabilization task. `WORKFLOW_ROADMAP.md` still controls implementation priority.

See `PROJECT_ASSET_CONTRACT.md` for reusable state, especially accepted grid/spot coordinates.

## Architecture

Prefer a lightweight overall controller that owns project selection, canonical state/status and launch actions. Focused mini-apps may implement independent jobs such as orientation, whole-plate crop, visibility adjustment and annotation.

Do not require every component to live inside one large GUI. Do not make a mini-app rediscover metadata or repeat prior clicks when canonical state already exists.

## 1. V10 metadata and project setup

User fills V10 normally. The program loads V10 read-only and produces canonical metadata/project state.

Key semantics:

- starred `*` fields are machine-readable mirrored/expanded representations where defined;
- a human-facing value such as Set `A` may be entered once while machine-readable `Set*` repeats `A` across every corresponding machine row;
- code should use the intended expanded machine representation rather than require repeated human entry;
- image/experiment Set remains meaningful;
- the Set column retained in vertical-profile tables is ignored for current image-processing semantics;
- `Image UID` is image identity; `sessionUID` is session identity;
- `Original`/`Working filename` are names/locators, not identity;
- incomplete expected image sets are valid.

`Pos` means within-profile position. Vertical-profile `Pos` derives physical row count/order. Strain-profile maximum/extent of `Pos` derives that band's local width. Overall grid columns are the widest assigned strain-profile width.

`Order` means top-to-bottom ordering between multiple strain profiles assigned to one annotation set. For the current 8-row/two-profile case, default row mapping is even split 1-4 / 5-8, while explicit/manual row-band override remains supported for future non-even cases.

The current basic CSV mode intentionally remains simpler and does not need V10 Set/annotationSet/profile-order logic retrofitted into it.

## 2. Optional UID-safe working-copy renaming

Raw camera/source images remain untouched in `raw/`, including generic names such as `image1.jpg`.

Optionally duplicate present raw files to a parallel `working/` tree and apply V10 `Working filename` nomenclature. Renaming is not required for downstream processing when UID/path mapping is already known.

At project root create a human-readable raw->working conversion text file, grouped by Experiment and Set with clear dividers and UID/context where useful. Avoid absolute private machine paths.

## 3. Whole-plate orientation preprocessing

This replaces manual Photoshop straightening and occurs before whole-plate crop/grid registration.

Do **not** reuse the ROI 1-click colony-box plugin.

Preferred first interaction is **one straight-line drag** along whichever long top or bottom physical plate edge is easiest to see.

1. Display working image.
2. Activate a normal line/crosshair-line tool.
3. User drags one line along the chosen top/bottom plate edge.
4. Keep the measured line visible.
5. Derive observed edge angle and correction required to make it horizontal.
6. Show non-destructive corrected preview.
7. Accept / Retry / Skip.
8. Save working derivative plus per-image orientation transform/result.

Top and bottom edges use the same horizontal-reference calculation; do not add separate dialogue branches.

Automatic CV orientation may be explored later but is optional. Skipping/failing orientation must never block the current four-click culture-grid route.

## 4. Whole-plate crop preprocessing

Do **not** reuse the colony ROI-box plugin.

The crop workflow has two distinct state layers: reusable **crop-size calibration** and per-image **crop placement**.

### 4A. Calibrate reusable crop size

When no suitable calibration exists, or when explicitly recalibrating:

1. click left useful boundary;
2. click right useful boundary;
3. click top useful boundary;
4. click bottom useful boundary;
5. exact corners are not required;
6. derive measured width/height;
7. default shape is square;
8. use a conservative side based on the smaller trustworthy extent;
9. round **down to nearest 50 px by default**; rounding is configurable;
10. save the accepted size as reusable `CropSizeCalibration`.

### 4B. Place that size independently on every image

Even plates with identical dimensions may appear at different x/y offsets in the camera frame. Therefore never reuse another image's crop center/translation merely because size matches.

For each image:

1. reuse current calibrated size;
2. click somewhere on the **left plate edge**; use x for horizontal placement;
3. click somewhere on the **top plate edge**; use y for vertical placement;
4. place the calibrated crop from those independent anchors;
5. preview;
6. Accept / Retry placement / Recalibrate size / Skip as appropriate;
7. save per-image crop rectangle/translation + source->crop transform.

This intentionally avoids exact-corner clicking, which is less reliable than finding any clear left-edge and top-edge point.

Normal path after calibration should be only:

`left-edge click -> top-edge click -> preview -> Accept`

Retrying placement must not require size recalibration.

## 5. Four-click culture-grid registration

Preserve the current proven four-click route.

On accepted QC grid, persist the **full reusable grid/spot-coordinate asset**. Registration and crop export must be separable.

Future UI should support:

- register grid only;
- register + immediate unprocessed crop export;
- later export from saved grid without realignment;
- all cultures, first/default subset, or selected strains/cultures;
- optional per-Condition crop subfolders;
- distinct unprocessed/raw and processed crop parents.

Do not bind saved coordinates to one immediate macro export.

## 6. Whole-plate visibility adjustment

After grid coordinates exist, derive adjustment statistics from the overall measured grid ROI while applying the resulting display adjustment to the **entire whole-plate image**.

The existing 2x CLAHE preview remains fit for alignment; it is not automatically the final presentation method.

Research mature Fiji/ImageJ/plugin/Python options before custom algorithms. Preview is non-destructive.

Fast batch decisions:

- Approve -> save processed output and continue;
- Mark for manual -> add image to review queue and continue.

Manual queue should later open flagged images directly in Fiji/ImageJ or chosen editor.

## 7. Processed whole-plate output

Save accepted visibility-adjusted derivatives to a `processed/` parent while preserving relevant project/experiment/Set/condition subfolders.

Normally preserve registered image geometry/dimensions so saved grid coordinates remain valid.

## 8. Processed culture crop export at any later time

If both exist:

1. accepted saved grid coordinates;
2. matching processed whole-plate image;

allow processed culture-crop export without rerunning alignment or prior stages. Check actual prerequisites rather than force sequential workflow replay.

## 9. Automatic whole-plate annotation

Because the project knows exact measured culture coordinates plus strain/row identity, ordinary label placement should be automatic rather than Photoshop-template based.

Required behavior:

- strain labels anchored/distributed from measured culture x/grid coordinates;
- labels mapped to correct strain/profile/band identity;
- default strain text 90 degrees clockwise, top facing right;
- vertical labels upright by default, aligned to measured row/y coordinates;
- multi-strain-profile row bands handled automatically;
- figure description/date/experiment/Set/media/condition labels use deterministic anchors + preset offsets;
- reusable presets store font, size, color, orientation, class visibility, margins/offsets and formatting;
- fast **non-destructive preview** before final render.

Spacing should come from actual measured coordinates wherever possible. Scientific metadata remains separate from presentation options.

Final render creates a derived `annotated/` output and does not modify processed source.

## 10. Annotated whole-plate export

Save explicit annotated derivatives while preserving subfolder structure and enough preset/result metadata for reproducibility.

Changing annotation style does not invalidate grid coordinates.

## 11. Matrices/compositions once required crops exist

Matrix generation can occur as soon as required culture crops exist; it does not depend on whole-plate annotation.

Support structured metadata selection plus practical manual overrides for small quick figures.

Crop tier/position selection must be **per selected strain/image**, not global-only. Example: WT1 may use `top` while STRAIN2 uses `low` in the same matrix.

## Reusable-state rule

The accepted grid result is a durable project asset for unprocessed crop export, processed crop export, whole-grid ROI statistics, automatic annotation placement, QC overlays/previews and selected-strain/matrix crop resolution.

Do not ask the user to repeat four-click registration merely because a later function runs at another stage or in another mini-app.

## UX principles

- reuse saved state rather than repeat clicks;
- keep crop-size calibration separate from per-image placement;
- automate deterministic placement/calculation when coordinates/metadata already determine it;
- manual fallback is for exceptions;
- preview before presentation/crop writes;
- preserve raw sources;
- prefer focused tools/applets with narrow contracts over a monolithic controller;
- one overall controller may orchestrate them later.
