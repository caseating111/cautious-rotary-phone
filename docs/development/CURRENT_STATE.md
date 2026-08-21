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

### Metadata reconciliation
- `tools/reconcile_images_csv.py` scans the production source folders, preserves existing authoritative metadata, leaves new metadata blank rather than guessed, and preserves manual draft metadata across rescans.
- Duplicate source basenames, duplicate metadata rows and stale metadata rows are explicitly flagged.
- `tools/finalize_images_reconciliation.py` creates a separate `images_candidate.csv` only when current source rows are complete, basenames are unique and the existing project validator accepts the candidate.
- Authoritative `images.csv` is never overwritten automatically.
- `tools/metadata_review_gui.py` keeps reconcile/edit/finalize/open actions outside the main processing GUI; the controller has one launcher button.
- `tests/test_metadata_reconciliation.py` covers authoritative metadata preservation, draft persistence, stale-row exclusion and incomplete candidate rejection.

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

## Active branch: output-navigation
Purpose: remove unnecessary Explorer navigation after deterministic Pillow output jobs without changing any image-generation logic.

Current changes:
- `tools/run_existing_pillow_from_config.py` snapshots child output directories before/after the existing script runs;
- on success it identifies the actual newly created output folder, writes it to `~/.cautious-rotary-phone/last_pillow_output.txt`, and opens that folder by default on Windows;
- `--no-open-output` preserves command-line control when automatic navigation is unwanted;
- no legacy Pillow script is modified;
- `tests/test_output_navigation.py` covers new-directory detection and the no-new-output case.

## Legacy audit result
- The remaining unwrapped `existing scripts clean/pythonfileaudit.py` is an E2/B-specific diagnostic and is superseded by the generic preflight/reconciliation tooling; do not expose or expand it unless a concrete missing use case appears.

## Pending manual validation (not a stop condition)
- Desktop Fiji interaction for ROI preset patch and whole-column placement/QC.
- Visual confirmation of native profile peak selection on representative real plates.
- End-to-end composed batch on representative images.
- Confirm the installed Fiji desktop launcher accepts a fourth command-line macro argument for the config-driven visibility shortcut; direct dialog launch remains fallback.

## Highest-value next routes
1. Reduce repeated batch navigation/cleanup only where it composes with existing output folders and does not obscure files.
2. Inspect AHK/Fiji interaction for small safe keyboard-efficiency improvements while preserving manual first/last-column oversight.
3. Research/reuse Fiji/BAR profile/peak alternatives only if native `Array.findMaxima()` proves weak on real plates; do not build a custom colony detector first.
4. Keep metadata inference conservative unless real data demonstrates a stable, verifiable pattern worth exploiting.
