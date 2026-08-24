# workflow-C implementation roadmap

This roadmap is outcome-first and staged. Do not jump ahead merely because later work is interesting. Get each earlier stage practically reliable before expanding scope.

Detailed future behavior now lives in:

- `docs/development/FUTURE_WORKFLOW_CONTRACT.md` — step-by-step intended user workflow and feature semantics;
- `docs/development/PROJECT_ASSET_CONTRACT.md` — reusable state/coordinate contract, especially accepted grid/spot coordinates.

Use those documents when implementing a future stage. Do not reread them during unrelated bounded stabilization unless the current change affects those contracts.

## Integrated checkpoint

Priorities 1-8 are integrated on `workflow-integrated`. V10/layout, optional Working copies, orientation, whole-plate crop, saved-grid visibility, annotation, later unprocessed/processed culture export, and mixed Top/Low matrices are available through the stateful V10 applets. The proven four-point route remains the registration owner; its additive register-only mode separates accepted grid persistence from crop export without replacing production behavior. The sections below retain the behavioral contract and dependency order, not an unfinished-status claim.

## Priority 1 — keep the current basic CSV/Fiji route reliable and slim

The current Windows + Miniforge `workflow-c` Python 3.11 + Fiji + AHK v2 four-click route is the production baseline.

Preserve the now-proven core behavior:

- four authoritative culture-center clicks;
- QC grid;
- accept/export/DONE lifecycle;
- reset/re-run selected DONE plate;
- incomplete physical image-set tolerance;
- case-insensitive identity matching where semantically appropriate;
- image-blind privacy/testing requirements.

Continue to remove duplicate/legacy launch paths and obsolete GUI actions when they interfere with the supported route. Do not revive abandoned column-alignment behavior as a parallel supported path.

The basic CSV route intentionally remains simpler than V10. **Do not retrofit V10 `Set`/annotationSet/profile-order semantics into it.**

### Reusable-grid requirement

The accepted four-click grid result is no longer conceptually just an immediate crop-export intermediate. It is persisted/exposed as a durable project asset so later actions can reuse it for raw/unprocessed crop export, processed crop export later without realignment, overall-grid ROI statistics, automatic annotation placement, QC overlays/previews and selected-strain/matrix crop resolution.

Registration and crop export should therefore remain separable.

## Priority 2 — V10 workbook integration

Make V10 the preferred rich metadata input for full experiments while reusing the same downstream processing components.

Implement in bounded slices:

1. read-only adapter using the supported sanitized/real workbook form without unnecessary conversion;
2. canonical internal records using V10 terminology;
3. machine-readable starred-column handling, including compact human Set entry vs expanded `Set*` rows;
4. `sessionUID` / `Image UID` identity;
5. local session-folder mapping;
6. raw/working/known-derivative filename reconciliation;
7. incomplete-dataset validation and READY / EXPECTED_NOT_PRESENT / AMBIGUOUS / UNMAPPED_FILE states;
8. local provenance keyed by Image UID;
9. annotation-derived layout metadata using current one-vertical-profile scope;
10. derive rows from vertical `Pos` and each strain-band width from strain `Pos`;
11. widest strain band defines overall grid columns;
12. use strain-profile `Order` for top-to-bottom bands;
13. default even row distribution for multiple ordered strain profiles when appropriate, with explicit/manual row-band override available;
14. first prove simpler 8x12 operation;
15. then prove the 8x10 two-strain-band case;
16. compatibility handoffs only where existing Fiji/Pillow code actually needs them.

See `V10_WORKBOOK_CONTRACT.md` plus the detailed future workflow contract. Ignore the vertical-profile table's `Set` values for current processing semantics even though that workbook column remains present.

## Priority 3 — project setup / optional working-copy renaming

Once V10 canonical identity is available:

- keep raw `image1/image2/...` source files unchanged in `raw/`;
- optionally create a parallel `working/` tree with V10 working filenames;
- use Image UID, not filename text, as identity;
- write a human-readable raw->working conversion map at project root grouped by Experiment and Set;
- make renaming optional so generic raw filenames remain processable.

## Priority 4 — optional whole-plate orientation preprocessing

Replace manual Photoshop straightening with a tiny pre-grid helper.

Preferred first route is **one straight-line drag along a clear top or bottom physical plate edge**, not two separate point-click dialogues and not the colony ROI-box plugin.

Calculate correction angle needed to make that line horizontal, show preview, then Accept/Retry/Skip. Save the per-image orientation derivative + transform. Automatic CV orientation is optional future convenience and must never block the working four-click grid route.

## Priority 5 — optional whole-plate crop preprocessing

Keep **crop-size calibration** separate from **per-image placement**.

### Size calibration

On a representative plate, use four forgiving boundary/extreme clicks (left/right/top/bottom), not exact corners and not the colony ROI-box plugin.

Derive a default square crop size and round its side **down to nearest 50 px by default**, with configurable rounding. Save that size as reusable calibration.

### Placement for every image

Even when size is reused, a plate may appear at a different x/y camera-frame offset.

For every image:

- click somewhere on the left plate edge -> x anchor;
- click somewhere on the top plate edge -> y anchor;
- place the calibrated-size crop from those anchors;
- preview and Accept/Retry placement;
- Recalibrate size only when needed.

Do not require exact-corner clicks. Do not reuse another image's crop center merely because dimensions match.

Persist crop-size calibration separately from per-image crop rectangle/transform.

## Priority 6 — automated visibility adjustment with manual-review fallback

After accepted grid coordinates exist:

- use overall grid area as the ROI from which adjustment statistics are derived;
- apply the resulting display adjustment to the **entire image**;
- research mature Fiji/ImageJ/plugin/Python methods before custom algorithms;
- show non-destructive preview;
- fast actions: Approve or Mark for manual;
- maintain a manual-review queue that can reopen flagged images in Fiji/ImageJ or selected editor;
- keep display-adjusted pixels separate from quantitative/scientific source pixels.

Processed whole plates should preserve registered geometry where possible so grid coordinates stay reusable.

## Priority 7 — metadata + coordinate-driven automatic annotation

Annotation should no longer depend on Photoshop templates/manual per-image label alignment.

Use canonical strain/row identity from V10/PlateLayout plus accepted measured culture/grid coordinates for actual placement.

Required presentation behavior includes strain labels rotated 90 degrees clockwise by default (top facing right), vertical labels upright by default, deterministic figure/date/experiment/Set/media/condition anchors, reusable font/size/color/orientation/offset presets, and a fast **non-destructive preview** before final render.

Spacing should derive from actual measured coordinates. Manual placement overrides are exception/fallback behavior, not the normal workflow.

## Priority 8 — crop/matrix flexibility

Crop exports should be runnable later whenever the required saved grid + source derivative exist; do not force realignment.

Support distinct raw/unprocessed and processed crop parents, plus optional Condition subfolders.

Matrix/composition selection supports **per-strain crop tier choices** within one matrix, e.g. WT1 `top` together with STRAIN2 `low`, rather than global all-top/all-low only.

## Lightweight CSV mini-project input

A small CSV/folder-discovery adapter remains useful for quick comparisons without editing V10.

Do not create a second processing architecture. It should feed the same downstream reusable project/grid/annotation/crop components while keeping its metadata model intentionally simpler than V10.

## General implementation rule

At every stage, first check whether Fiji/ImageJ, Pillow, scikit-image, OpenCV, CellProfiler, ilastik, pandas/Polars, SQLite or another mature tool already covers the required function. Add only the smallest glue needed to connect stable components.

Prefer focused mini-apps with narrow contracts where that reduces parallel-development conflicts and GUI bulk. The eventual overall controller can orchestrate them rather than absorbing every implementation internally.
