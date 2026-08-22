# Intended future workflow / mini-app map

This document records the intended end-to-end user workflow so isolated Gemini prototypes fit together later. It is a functional workflow contract, not an instruction to implement everything in one GUI or branch.

The current working four-click Fiji grid route is a valuable proven component and should be integrated around, not casually replaced.

See `docs/development/PROJECT_ASSET_CONTRACT.md` for the reusable-state contract, especially the rule that accepted grid coordinates are a durable project asset rather than a one-time crop-export intermediate.

## Architecture

Prefer a lightweight overall project/controller GUI that owns project selection/shared state and launches focused mini-apps or actions. Separate agents may implement independent components on child branches when their file/interface boundaries do not overlap.

A mini-app should do one coherent job well, consume canonical project state, and return/persist a narrow result. Do not make every mini-app rediscover V10, rescan filenames, or repeat previous clicks.

Core reusable state should include:

- canonical V10-derived project/image identity;
- raw/working/processed/annotated file mappings;
- whole-plate orientation/crop transforms;
- logical `PlateLayout`;
- measured pixel grid/spot coordinates;
- visibility-adjustment result/preset;
- annotation preset/result;
- crop/matrix output metadata.

## 1. V10 metadata + project setup

### User intent

Fill in the V10 workbook in its normal human-facing way, then use the program to load/export the metadata needed for image processing without manually reproducing that information in another system.

### Intended function

1. User selects the V10 workbook/project.
2. The V10 adapter reads it **read-only** and produces canonical project/image records.
3. The setup step prepares the project folder structure and expected-output areas.
4. Missing expected physical images are allowed; metadata completeness and file availability are separate concepts.
5. The controller presents concise READY / missing / ambiguous / unmapped information rather than requiring a complete image set.

### Important workbook semantics

- Human-readable fields may be entered compactly while machine-readable `*` fields expand values row-by-row for code consumption.
- Example: the user may enter a human-facing Set value `A` once for a logical block, while machine-readable `Set*` contains `A` on every corresponding machine row. The adapter should consume the machine-readable representation when appropriate rather than expecting repeated manual entry.
- `Set` for image/experiment grouping remains meaningful.
- The `Set` column retained inside the **vertical-profile table** is a workbook artifact for current purposes and is ignored by the image-processing semantics.
- `Pos` means ordered physical/logical position **within one profile**. For a strain profile, the maximum valid `Pos` is that profile's local column count. For a vertical profile, `Pos` gives physical row ordering/count. Repeated label text does not collapse positions.
- `Order` means top-to-bottom ordering **between multiple strain profiles assigned to one annotation set**. It is not column order within a strain profile.
- Overall grid columns are derived from the **widest assigned strain profile**, not by adding widths of separate row bands.
- With one vertical profile containing positions 1-8, overall grid rows are 8.
- With two ordered strain profiles on an 8-row layout, default mapping is an even split: `Order=1` rows 1-4 and `Order=2` rows 5-8. Explicit/manual row-band override must also be supported later for cases where equal distribution is not appropriate.

### CSV compatibility boundary

The currently working basic CSV workflow remains a simpler baseline. It does **not** need V10 Set/annotationSet/profile-order semantics retrofitted into it. V10 is the richer metadata path around the same image-processing components.

## 2. Optional UID-safe working-copy renaming

### User intent

Keep original camera/export files safe and simple (`image1.jpg`, `image2.jpg`, etc.) while optionally creating human-readable working copies whose names come from V10.

### Intended function

1. Raw files remain in a `raw/` parent tree, unchanged.
2. Program reconciles each present raw file to its canonical image record/Image UID.
3. Preview proposed raw -> working mappings before writing.
4. If renaming is enabled, duplicate/copy into a parallel `working/` tree and apply the V10 `Working filename` nomenclature.
5. If renaming is disabled, downstream processing still works using canonical UID/path mapping even when filenames remain generic.
6. Similar human-readable names must not cause identity collision because `Image UID` is canonical. If a filesystem collision still occurs, report it and use a deterministic UID-aware disambiguation strategy rather than overwriting.

### Human QC conversion file

At overall project root, create a small text file listing conversions, for example:

`image1.jpg -> ypda+type1,01.jpg`

Organize it with visible headings/dividers by Experiment and Set, and include UID/context where useful. Keep it human-readable and relative-path based; it is a QC aid, not the machine database.

## 3. Whole-plate orientation preprocessing

### User intent

Replace manual Photoshop straightening with a very fast interaction before whole-plate cropping and grid registration.

### Preferred first implementation

Do **not** use the ROI 1-click rotated rectangle plugin here; its 108x108 colony-box behavior adds no value for plate orientation.

Preferred interaction is either:

- **two point clicks with a crosshair cursor** along one trustworthy straight physical plate edge; or
- one standard straight-line drag between the same two points.

Two visible point markers/one visible line should remain on screen until accepted so the user can see exactly what angle was measured.

The app calculates the edge angle and rotates a **working derivative** by the correction angle needed to make that edge horizontal/vertical according to the chosen convention.

### User flow

1. Open one working plate image.
2. Cursor becomes a precise crosshair/point tool.
3. User clicks point A and point B along a long, visually reliable plate edge.
4. App draws the measured line and reports/proposes the correction angle.
5. Preview corrected orientation without overwriting source.
6. Hotkey/button: Accept or Retry.
7. Save orientation angle/transform as project state for later crop/coordinate transforms.

Automatic CV orientation can be researched later as an optional convenience/fallback, but must never block or replace this simple reliable route unless it clearly proves better in practice.

Skipping the orientation mini-app must still leave the current four-click grid route usable.

## 4. Whole-plate crop preprocessing

### User intent

Replace manual Photoshop whole-plate cropping with a fast, repeatable crop that removes excess blank space while tolerating small edge losses.

### Boundary interaction

Do not use the colony ROI-box plugin.

Default interaction uses **four crosshair boundary clicks**:

1. leftmost useful plate boundary;
2. rightmost useful plate boundary;
3. topmost useful plate boundary;
4. bottommost useful plate boundary.

From these, the app can already estimate plate center, width and height. Therefore the first crop proposal should be generated immediately without forcing extra clicks.

### Default crop calculation

- default shape: square;
- use a conservative dimension based on the measured plate extent so blank space is not introduced;
- round the proposed square side **down to nearest 50 px by default**;
- rounding increment/behavior is configurable;
- cropping slightly into nonessential plate edge is preferable to expanding into blank background.

Recommended initial square rule: derive from the smaller trustworthy plate extent and round downward, unless testing demonstrates a better simple rule.

### Optional anchor correction

The previously requested two extra references — `somewhere on the left edge` and `somewhere along the top` — remain useful as an **optional reposition/re-anchor correction**, not mandatory on every image.

If the four-boundary proposal is already correct, user can simply Accept. If placement is off, user enters Adjust mode and clicks a left-edge x reference and top-edge y reference; the same calculated crop size is repositioned accordingly.

This reduces the common case to four clicks while preserving precise manual control when needed.

### Preview/save

Show the proposed square overlay and/or cropped preview before writing. Provide fast Accept / Retry / Re-anchor actions, ideally hotkeyable. Save accepted crop/transform to reusable project state and write the working derivative, never the raw source.

## 5. Four-click grid registration and culture crop availability

### User intent

Use the now-proven four-click culture-grid route to obtain the actual culture coordinates once, then reuse them for multiple later jobs.

### Required function

1. Run current four authoritative colony-center placements.
2. Compute and show QC grid.
3. Accept or retry.
4. On accept, persist the full reusable grid/spot-coordinate asset.
5. **Do not require immediate crop export.** Registration and export are separate actions.

### Export modes

The production UI should ultimately allow:

- register grids only;
- register + export unprocessed crops immediately;
- export crops later from already-saved grids;
- export all cultures;
- export the existing first/default subset;
- export selected strains/cultures.

Raw/unprocessed and processed crop outputs need distinct parent folders.

Optional organization: create per-Condition subfolders under crop parents, e.g. CONTROL and CAFFEINE, while retaining experiment/project structure.

This area is currently production/Codex-owned. Gemini components should consume the saved-grid contract rather than replacing the working grid route.

## 6. Whole-plate visibility adjustment for human comparison

### User intent

Replace most manual Photoshop levels work with a repeatable visibility adjustment, while quickly flagging exceptions rather than blocking the batch.

### Required function

1. Require an accepted grid coordinate asset for the image.
2. Derive the overall grid-area ROI from saved spot/grid geometry.
3. Compute adjustment statistics **from that ROI**.
4. Apply the resulting display adjustment to the **entire whole-plate image**, not only the ROI.
5. Show non-destructive preview.
6. User uses one of two fast actions:
   - Approve -> save processed output and continue;
   - Mark for manual -> add to review queue and continue.
7. Manual-review queue can later open flagged images directly in Fiji/ImageJ or chosen editor.

The existing 2x CLAHE preview remains suitable for alignment and does not need to be changed merely because final presentation adjustment may use another method.

Research mature Fiji/ImageJ/plugin/Python options before custom algorithms. Expect some manual comparison of candidate presets before choosing final defaults.

## 7. Export processed whole plates

Accepted visibility-adjusted images go to a `processed/` parent while preserving relevant experiment/Set/condition/date structure. Source raw/working images remain available separately.

The processed image should normally preserve geometry/dimensions of the registered working image so the saved grid coordinates remain valid.

## 8. Optional processed-image culture crop export

At **any later time** when both requirements exist:

1. saved grid coordinate asset;
2. matching processed whole-plate image;

allow culture crop export without realignment or rerunning earlier steps.

The action should check those two requirements directly rather than enforce the entire workflow sequence again.

## 9. Automatic whole-plate annotation

### User intent

Eliminate the old Photoshop template generation and per-image manual label alignment. Because the workflow knows every spot coordinate and every strain/row identity, ordinary annotation placement should be automatic.

### Placement rules

- strain labels derive from actual culture x/grid coordinates, not evenly-spaced assumptions when measured coordinates are available;
- each strain label is associated with its actual logical strain position/band from V10 + `PlateLayout`;
- default strain text orientation remains **90 degrees clockwise**, top of text facing right;
- vertical labels remain upright by default and align to measured row/y coordinates;
- figure description/date/experiment/Set/media/condition labels use deterministic anchors relative to accepted plate/grid/image bounds plus configurable offsets;
- multi-strain-profile plates use the correct row-band-specific strain labels automatically.

Manual per-plate alignment should be exceptional, not the normal workflow.

### Presentation presets

Reusable presets should store presentation choices such as:

- font;
- size;
- color;
- orientation;
- label-class visibility;
- offsets/margins;
- figure-description/date anchor rules;
- optional abbreviations/display formatting.

Spacing should normally come from measured spot/grid coordinates rather than a hand-built template.

### Preview

A fast **non-destructive preview mode is required**. It should render/display the proposed labels using the chosen preset without overwriting or requiring the user to create/delete temporary final files merely to inspect font, size, spacing, clipping and general appearance.

Useful preview diagnostics include clipping/out-of-bounds warnings and obvious label collisions. Prefer automatic repositioning/scale within preset rules where deterministic, but keep the final presentation settings user-adjustable.

Final annotation writes a derived `annotated/` output; processed source remains unchanged.

## 10. Export annotated whole plates

Render/export annotated images while preserving relative subfolder structure and enough preset/result metadata to reproduce the presentation later.

Annotation is a derived presentation step; changing annotation style must not invalidate grid geometry or processed-image identity.

## 11. Matrices/compositions may begin once crops exist

Matrix generation does not need to wait for whole-plate annotation. Once the required individual crop files exist, matrices can be generated independently.

Composition should support both structured metadata selection and practical manual overrides for quick figures.

Important enhancement: crop tier/position selection is **per selected strain/image**, not global-only. A matrix must be able to combine, for example, WT1 `top` with STRAIN2 `low` in the same output.

Matrix requests should reference canonical crop/image identities rather than infer everything from display filenames.

## Dependency summary

Preferred order for full automatic-assisted workflow:

`V10/setup -> optional working rename -> optional plate orientation -> optional plate crop -> grid registration -> visibility adjustment -> processed whole plate -> annotation`

Culture crop export is intentionally decoupled after grid registration and can occur before or after visibility adjustment depending on whether raw or processed crops are desired.

Matrix generation depends on the required crop files, not on annotation.

Orientation/crop helpers are preprocessing conveniences. If either is skipped or fails, they must not make the working four-click grid route unusable.

## UX principles

- reuse state rather than repeat clicks;
- automatic placement/calculation is preferred when grid/metadata makes it deterministic;
- manual fallback/review exists for exceptions, not as the default burden;
- preview before destructive/derived writes where presentation or crop quality matters;
- preserve raw sources;
- favor focused mini-apps with narrow contracts over one enormous GUI;
- the overall controller should orchestrate state and launch tools rather than reimplement every tool internally.
