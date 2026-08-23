# Intended future workflow / mini-app map

This document records the intended end-to-end user workflow so isolated Gemini prototypes fit together later. It is a **functional specification**, not an instruction to implement everything in one GUI or one branch.

The current working four-click Fiji culture-grid route is a proven component and should be integrated around, not casually replaced.

See `docs/development/PROJECT_ASSET_CONTRACT.md` for the reusable-state contract. In particular, accepted grid coordinates are a durable project asset rather than a one-time crop-export intermediate.

## Overall architecture

Prefer a lightweight project/controller GUI that owns project selection, canonical identity/state and launch/status controls, while focused mini-apps perform coherent jobs such as orientation, plate cropping, visibility adjustment and annotation.

A mini-app should:

1. receive canonical project/image identity plus only the state it needs;
2. perform one coherent operation;
3. preview/validate when visual judgement matters;
4. persist a narrow result/state object;
5. return control without rediscovering V10 or repeating previous clicks.

The user should not be forced through a rigid wizard. Later actions should be callable whenever their actual prerequisites exist.

Core reusable state should include canonical V10 identity, raw/working/processed/annotated file mappings, orientation transforms, crop-size calibration, per-image crop placement, logical `PlateLayout`, measured culture-grid/spot coordinates, visibility-adjustment state, annotation presets/results, and crop/matrix outputs.

---

## 1. V10 metadata + project setup

### User goal

Fill in the V10 workbook in its normal human-facing manner and use that as the rich project metadata source without maintaining a second manual metadata system.

### Intended function

1. User selects/loads the V10 workbook/project.
2. Adapter reads it read-only and produces canonical project/image records.
3. Program validates identifiers/assignments and reports missing/ambiguous metadata clearly.
4. Program creates/prepares the project output structure without requiring every expected image to physically exist.
5. Present concise per-image/project readiness state rather than forcing a complete dataset.

### Workbook semantics that must remain explicit

- Human-readable fields may be entered compactly while machine-readable `*` fields expand the value row-by-row.
- Example: the user may type one human `Set` value `A` for a logical block; machine-readable `Set*` contains `A` on each corresponding machine row. Code should consume the expanded machine-readable representation where appropriate rather than requiring repeated human entry.
- Image/experiment `Set` remains meaningful.
- The `Set` retained inside the **vertical-profile table** is currently a workbook artifact and is ignored for image-processing semantics.
- `Pos` means ordered physical/logical position **inside one profile**. For strain profiles, maximum valid `Pos` gives that profile's local column count. For vertical profiles, `Pos` gives physical row order/count. Repeated label text still occupies separate positions.
- `Order` means top-to-bottom ordering **between multiple strain profiles assigned to the same annotation set**. It is not strain-column order.
- Overall grid columns come from the **widest assigned strain profile**, not the sum of widths of different row bands.
- One vertical profile with `Pos` 1-8 means an 8-row plate layout.
- When two ordered strain profiles share an 8-row plate, default row allocation is an even split: `Order=1` rows 1-4 and `Order=2` rows 5-8.
- Explicit/manual row-band override must also be supported so unusual layouts are not forced into equal division.

### CSV boundary

The currently working basic CSV workflow is intentionally simpler. It does **not** need V10 `Set`/annotationSet/profile-order semantics retrofitted into it. V10 is the richer metadata input around the same image-processing components.

### State produced

Canonical `ProjectModel`, image/session identity, expected-image records, annotation/profile assignments and enough normalized layout-source metadata for downstream layout derivation.

---

## 2. Optional UID-safe working-copy renaming

### User goal

Keep original camera/export files untouched (`image1.jpg`, `image2.jpg`, etc.) while optionally gaining readable V10-based working filenames.

### Intended function

1. Raw files remain unchanged under `raw/`.
2. Reconcile each present raw file to canonical Image UID/session context.
3. Preview raw -> working mappings before writing.
4. If enabled, duplicate into a parallel `working/` tree and apply V10 `Working filename` nomenclature.
5. If disabled, later processing still works with generic filenames because UID/path mapping is authoritative.
6. Similar human-readable names must not overwrite/confuse one another; use UID-aware collision handling.
7. Re-running setup is idempotent rather than creating rename chains or duplicate copies.

### Human conversion map

At project root write a human-readable mapping file, conceptually:

`image1.jpg -> ypda+type1,01.jpg`

Group with clear dividers/headings by Experiment and Set, include UID/session context where useful, keep paths relative, and treat this as a QC aid rather than the canonical database.

### State produced

Raw/working path mappings and per-image copied/unchanged/missing/ambiguous/collision disposition.

---

## 3. Whole-plate orientation preprocessing

### User goal

Replace manual Photoshop straightening with one very fast action before plate cropping/grid registration.

### Required first interaction

Do **not** use the colony ROI-box plugin.

Use one ordinary **straight-line drag** along a long trustworthy **top or bottom physical plate edge**. Top and bottom use the same calculation; do not create separate dialogue branches.

### Intended function

1. Open current working whole-plate image.
2. Activate a standard line/crosshair-line tool.
3. User drags one line along whichever top/bottom plate edge is easiest to see.
4. Keep the reference line visibly overlaid.
5. Calculate observed line angle.
6. Calculate correction angle required to make it horizontal.
7. Render a non-destructive corrected preview.
8. Fast actions: `Accept`, `Retry`, `Skip`.
9. On Accept, save/update a derived working image and persist the orientation transform.

This is a **per-image rotational correction**. Do not assume another plate has the same rotation or translation.

Automatic CV orientation may later offer a suggestion, but it must be optional and must never block the manual one-line route or the existing four-click culture-grid route.

### State produced

Per-image `OrientationResult`: reference-line endpoints, observed/correction angle, convention, accepted/skipped state, source/output geometry and transform.

---

## 4. Whole-plate crop preprocessing

### User goal

Replace manual Photoshop cropping with a consistent crop while minimizing repeated clicks across similarly imaged plates.

### Critical design: size calibration != image placement

A batch of plates may have the same physical/imaged dimensions but different x/y offsets in the camera frame.

Therefore:

- **crop size** may be calibrated once and reused;
- **crop placement/translation** must normally be determined separately for every image.

Never reuse another plate's crop center merely because dimensions match.

### 4A. Calibrate reusable crop size

When no suitable calibration exists, or user chooses `Recalibrate crop size`:

1. On the orientation-corrected plate, click leftmost useful boundary.
2. Click rightmost useful boundary.
3. Click topmost useful boundary.
4. Click bottommost useful boundary.
5. Exact corners are not required; each click contributes one extreme coordinate.
6. Measure width/height.
7. Default shape is square.
8. Default side is conservative so blank background is not introduced; slight loss of nonessential plate edge is acceptable.
9. Default calculation: `floor(min(width,height)/50)*50`.
10. Rounding increment/rule is configurable.
11. Save accepted size as reusable `CropSizeCalibration`.

### 4B. Place calibrated crop on each image

For every image, including the calibration image and later images using the same size:

1. Reuse current calibrated side/width/height.
2. Click **somewhere on the left plate edge**. Use its x coordinate for horizontal placement.
3. Click **somewhere on the top plate edge**. Use its y coordinate for vertical placement.
4. Position the calibrated crop using those independent x/y anchors plus configured inset/offset rules.
5. Show crop overlay/cropped preview.
6. Fast actions: `Accept`, `Retry placement`, `Recalibrate size`, `Skip/Cancel`.
7. Accept persists this image's crop rectangle/translation and writes the derived working crop.

This deliberately avoids exact-corner clicking, which is harder and less robust than finding any clear point on a left edge and any clear point on a top edge.

### Routine interaction cost

With a valid size calibration:

`left-edge click -> top-edge click -> preview -> Accept`

Only size changes require the extra four calibration clicks.

### State produced

Reusable `CropSizeCalibration` plus per-image `CropResult` containing left/top anchors, final rectangle and source->crop transform.

---

## 5. Four-click culture-grid registration + reusable coordinates

### User goal

Determine all culture positions once, then reuse those coordinates for crop export, visibility adjustment, annotation and matrices without repeating alignment.

### Intended function

1. Run the current four authoritative colony-center placements.
2. Compute grid geometry and individual culture-center coordinates.
3. Show QC grid.
4. Accept or retry.
5. On Accept, persist a reusable `GridCoordinateAsset`.
6. Crop export is optional at this point; registration and export are separate operations.

### Export modes required later

- `register only`;
- `register + export unprocessed crops`;
- `export later from saved grid`;
- all cultures;
- current first/default subset;
- selected strains/cultures.

Raw/unprocessed and processed crop outputs must have distinct parent folders.

Optional organization: per-Condition subfolders under crop parents, while retaining project/experiment structure.

### State produced

Accepted reference points, coordinate-space/version, grid basis/transform, row/column counts, every culture-center coordinate and logical identity mapping.

This component is currently production/Codex-owned; Gemini should consume the saved-grid contract rather than replacing the proven route.

---

## 6. Whole-plate visibility adjustment for human comparison

### User goal

Replace most manual Photoshop levels work with a repeatable automatic proposal, while quickly flagging exceptions instead of blocking a batch.

### Intended function

1. Require an accepted grid coordinate asset for the image.
2. Derive overall grid-area ROI from saved grid/spot geometry.
3. Compute adjustment statistics from that ROI.
4. Apply resulting display adjustment to the **entire image**.
5. Show non-destructive preview.
6. Fast actions:
   - `Approve` -> save processed output and continue;
   - `Mark for manual` -> queue image and continue.
7. Manual queue can later open flagged images directly in Fiji/ImageJ or another chosen editor.

The existing 2x CLAHE alignment preview is fit for alignment and does not need to become the final presentation adjustment.

Research mature Fiji/ImageJ/plugins/Python approaches before custom algorithms; expect a small amount of manual comparison to choose good presentation presets.

### State produced

`AdjustmentResult`: method, parameters, grid ROI/statistics, accepted/manual-review state, processed path and reproducibility metadata.

---

## 7. Export processed whole plates

Accepted visibility-adjusted images go under a `processed/` parent while preserving relevant experiment/Set/condition/date substructure.

Processed output should normally preserve the geometry/dimensions of the registered working image so saved culture-grid coordinates remain valid.

Raw/working source images remain available separately.

---

## 8. Optional processed-image culture crop export

This action may run **at any later time** once both exist:

1. saved `GridCoordinateAsset`;
2. matching processed whole-plate image.

It should not force the user back through alignment/visibility steps. It checks its actual prerequisites and exports the requested cultures using saved coordinates.

Processed and unprocessed crop parents remain distinct.

---

## 9. Automatic whole-plate annotation

### User goal

Eliminate Photoshop template generation and per-image manual label alignment. Because the workflow knows exact culture coordinates and V10/PlateLayout identity, normal placement should be automatic.

### Intended function

1. Choose processed whole plate by default as annotation source.
2. Load saved grid coordinates + `PlateLayout` + canonical metadata.
3. Place strain labels from actual measured x/culture coordinates and correct row-band/profile assignment.
4. Default strain-label orientation: **90 degrees clockwise**, top of text facing right.
5. Place vertical labels upright at actual measured row/y coordinates.
6. Place figure description/date/experiment/Set/media/condition labels using deterministic anchor rules plus preset offsets.
7. Multi-strain-profile plates automatically use the correct label set for each row band.
8. Show a fast non-destructive preview.
9. Allow preset adjustments, regenerate preview quickly, then render final annotated derivative.

### Presentation presets

Reusable presets should include font, size, color, orientation, label visibility, offsets/margins, figure/date anchor rules and optional display abbreviations.

Spacing should derive from actual measured culture/grid coordinates wherever possible rather than from hand-built label templates.

Preview should detect obvious clipping/out-of-bounds labels and preferably obvious collisions. Manual per-plate label alignment should be exceptional, not normal.

### State produced

`AnnotationResult`: preset/version, placed label geometry, source/grid version, preview/final output references and warnings.

---

## 10. Export annotated whole plates

Write final annotated images under an `annotated/` parent preserving relative subfolder structure.

Annotation is a presentation derivative. Changing fonts/styles must not invalidate culture-grid geometry or processed-image identity.

---

## 11. Matrices/compositions once crops exist

Matrix generation is independent of whole-plate annotation and may start as soon as the required culture crops exist.

### Intended function

1. Select strains/images/conditions/crop tiers from canonical crop records.
2. Allow structured metadata-driven selection plus practical manual overrides.
3. Crop tier/position is selected **per chosen strain/image**, not globally only.
4. Example: one matrix can combine WT1 `top` with STRAIN2 `low`.
5. Preserve requested ordering and labels.
6. Render/export derived matrix without mutating crop sources.

Matrix requests should use canonical identities rather than infer everything from display filenames.

---

## Dependency summary

Preferred full workflow:

`V10/setup -> optional working rename -> optional line-drag orientation -> optional crop calibration/placement -> four-click grid registration -> visibility adjustment -> processed whole plate -> annotation`

Culture crop export is decoupled after grid registration and can happen before or after visibility adjustment depending on whether unprocessed or processed crops are desired.

Matrix generation depends on the required crop files, not on annotation.

Orientation and whole-plate crop are optional preprocessing conveniences. Skipping/failing either must not make the working four-click route unusable.

## UX / optimization principles

- Reuse saved state instead of repeating clicks.
- Prefer one direct interaction over multiple dialogue branches when the mathematics is the same.
- Automatic placement/calculation is preferred when metadata/grid coordinates make it deterministic.
- Manual fallback/review is for exceptions, not the routine burden.
- Preview before saving where crop/presentation quality matters.
- Preserve raw sources and explicit derivative stages.
- Keep crop-size calibration separate from per-image placement.
- Keep logical metadata/layout separate from measured pixel geometry.
- Favor focused mini-apps with narrow contracts over one oversized GUI.
- The main controller should orchestrate project state/status/prerequisites and launch tools rather than reimplement every tool internally.
