# Current state

## Durable line
`workflow-dev`

## Working baseline
- Original four-point Fiji crop macro and original AHK helper remain unchanged as fallback.
- Original Pillow matrix/label scripts remain under `existing scripts clean/` and are reused through thin config adapters.
- Synthetic `grid.csv`, `images.csv` and `condition_order.csv` examples are kept semantically valid.
- Implementation is governed by `AGENTS.md` and `IMPLEMENTATION_DECISION_POLICY.md`.

## Implemented on workflow-dev

### ROI presets / manual alignment assistance
- Named ROI-size presets around the published ROI 1-Click Tools plugin.
- `fiji/full_column_alignment.ijm`: manually authoritative first/last whole-column ROIs -> native ImageJ `getProfile()` + `Array.findMaxima()` -> regular grid -> full-grid QC -> accept/retry.
- `ahk/full_column_alignment_hotkeys.ah2` keeps only small global-hotkey convenience.
- Source identity/dimensions are persisted with accepted alignment geometry to prevent stale reuse.

### Visibility / crop handoff
- `fiji/apply_global_visibility.ijm`: robust outside-grid background + inside-grid high percentile -> one whole-image display range while preserving quantitative source pixels.
- It can consume saved visibility settings through ImageJ macro arguments; direct no-argument launch retains the original dialog.
- `fiji/export_crops_from_alignment.ijm`: accepted alignment -> established Top/Low crop naming and geometry.

### Existing production batch composition
- `tools/run_full_column_batch_from_config.py` reuses the existing production Fiji batch macro's folder/CSV/image loop.
- Only the old four-point calibration/export section is replaced in a temporary configured copy by calls to `full_column_alignment.ijm` and `export_crops_from_alignment.ijm`.
- The original four-point macro remains untouched as fallback.
- CSV semantic validation runs before Fiji starts.
- Saved crop width/height and alignment tolerance are consumed only where metadata already supplies the grid column count.

### Batch preflight / resume
- `tools/preflight_batch.py` mirrors production immediate-subfolder, basename metadata and exact output-name semantics.
- It reports discovered/mapped/unmapped images, duplicate source basenames, stale metadata rows, missing grid definitions and expected/existing/missing crop counts.
- It writes `~/.cautious-rotary-phone/last_preflight.txt` and pending-only `pending_images.csv`.
- The composed batch uses pending-only metadata, so the unchanged production macro naturally skips fully completed plates on rerun.
- Partially complete plates remain pending as a whole plate; no fragile per-crop resume path is introduced.
- Controller checks preflight before AHK/Fiji and launches nothing when the batch is already complete.
- `tests/test_preflight_batch.py` provides stdlib synthetic coverage for missing, complete and duplicate-basename cases.

### Existing Pillow output reuse
- `tools/run_existing_pillow_from_config.py` exposes the existing matrix/all-strain/individual-label scripts through saved controller paths without rewriting their image logic.
- Existing scripts remain authoritative; configured temporary copies only replace their shared explicit path block.

### CSV validation
- `tools/validate_project_csvs.py` checks required headers, grid completeness/duplicates, consistent GridCols, unique source filenames, image->grid references and condition-order coverage.

### Lightweight controller / conda
- `tools/workflow_controller.py` persists paths/settings, validates CSVs, launches Fiji/AHK/Pillow helpers and ROI presets.
- Processing settings cover alignment tolerance, crop size and global visibility values without moving processing into the GUI.
- `tools/run_fiji_macro_from_config.py` is a thin visibility launcher using ImageJ's macro argument mechanism and supports dry-run command inspection.
- `environment.yml` remains minimal (`python`, `pillow`).

## Active branch: metadata-reconciliation
Purpose: reduce repeated `images.csv` setup while preserving original filenames and existing metadata as authoritative.

Current changes:
- `tools/reconcile_images_csv.py` scans the same immediate source folders as production and reconciles them against the configured `images.csv`;
- existing authoritative metadata is copied unchanged for known source basenames;
- new source images are listed with blank Experiment/Set/Type fields rather than guessed from filenames;
- duplicate source basenames, duplicate metadata rows and stale metadata rows are explicitly flagged;
- `~/.cautious-rotary-phone/images_reconciliation.csv` is non-destructive and preserves manually entered draft metadata across rescans;
- `tools/finalize_images_reconciliation.py` converts current-source review rows into a separate `images_candidate.csv` only when all metadata is complete, basenames are unique and the existing cross-file validator accepts the candidate;
- authoritative `images.csv` is never overwritten automatically;
- `tools/metadata_review_gui.py` provides a small reconcile/edit/finalize/open window rather than expanding processing inside the main GUI;
- the main controller has one Metadata review launcher button;
- `tests/test_metadata_reconciliation.py` covers preservation of existing metadata, draft persistence, stale-row exclusion from candidates and incomplete metadata rejection.

## Pending manual validation (not a stop condition)
- Desktop Fiji interaction for ROI preset patch and whole-column placement/QC.
- Visual confirmation of native profile peak selection on representative real plates.
- End-to-end composed batch on representative images.
- Confirm the installed Fiji desktop launcher accepts a fourth command-line macro argument for the config-driven visibility shortcut; direct dialog launch remains fallback.

## Highest-value next routes
1. Audit remaining existing Pillow/output scripts for reusable entry points/settings rather than adding new image-processing implementations.
2. Add output-folder/open-result convenience only where it reduces actual navigation burden.
3. Research/reuse Fiji/BAR profile/peak alternatives only if native `Array.findMaxima()` proves weak on real plates; do not build a custom colony detector first.
4. Keep metadata inference conservative: use filename/folder heuristics only if a future real-data sample demonstrates a stable, user-verifiable pattern worth exploiting.
