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

Preferred first interaction:

1. display working image;
2. crosshair cursor;
3. user clicks two well-separated points along one trustworthy straight physical plate edge;
4. show point markers + connecting line;
5. derive edge angle/correction;
6. show non-destructive corrected preview;
7. Accept / Retry / Skip;
8. save working derivative plus orientation transform/result.

A native straight-line drag is an acceptable equivalent if materially simpler. Automatic CV orientation may be explored later but is optional and must fall back cleanly. Skipping/failing orientation must never block the current four-click culture-grid route.

## 4. Whole-plate crop preprocessing

Do **not** reuse the colony ROI-box plugin.

Preferred default interaction is four crosshair boundary/extreme clicks on the straightened working plate:

1. left useful boundary;
2. right useful boundary;
3. top useful boundary;
4. bottom useful boundary.

From those four points derive measured width/height, center and default square crop. Use a conservative square side from the smaller trustworthy extent and round **down to nearest 50 px by default**. Rounding increment/behavior is configurable.

Immediately preview the proposed crop. Common path should be four clicks -> Accept.

Optional correction mode: if crop size is correct but placement is off, click one left-edge x anchor and one top-edge y anchor to reposition the existing square without remeasuring size.

Provide fast Accept / Retry / Re-anchor. Raw remains untouched. Save crop geometry/source->crop transform as reusable state.

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
- figure description/date/experiment/Set/media/condition labels use deterministic anchors + preset offsets.

Reusable presentation presets store font, size, color, orientation, class visibility, margins/offsets and formatting. Scientific metadata remains separate from presentation options.

A fast **non-destructive preview is required** so font/size/spacing/clipping/layout can be reviewed without writing/deleting final files. Final render creates derived `annotated/` output and does not modify processed source.

## 10. Annotated whole-plate export

Save explicit annotated derivatives while preserving subfolder structure and enough preset/result metadata for reproducibility.

Changing annotation style does not invalidate grid coordinates.

## 11. Matrices/compositions once required crops exist

Matrix generation can occur as soon as required culture crops exist; it does not depend on whole-plate annotation.

Support structured metadata selection plus practical manual overrides for small quick figures.

Crop tier/position selection must be **per selected strain/image**, not global-only. Example: WT1 may use `top` while STRAIN2 uses `low` in the same matrix.

## Reusable-state rule

The accepted grid result is a durable project asset for:

- unprocessed crop export;
- processed crop export;
- whole-grid ROI statistics;
- automatic annotation placement;
- QC overlays/previews;
- selected-strain/matrix crop resolution.

Do not ask the user to repeat four-click registration merely because a later function runs at another stage or in another mini-app.

## UX principles

- reuse saved state rather than repeat clicks;
- automate deterministic placement/calculation when coordinates/metadata already determine it;
- manual fallback is for exceptions;
- preview before presentation/crop writes;
- preserve raw sources;
- prefer focused tools/applets with narrow contracts over a monolithic controller;
- one overall controller may orchestrate them later.
