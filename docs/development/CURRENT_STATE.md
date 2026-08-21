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

## Active branch: batch-preflight-report
Purpose: prevent wasted manual alignment and make interrupted/repeated batches resume around already-complete plates using the existing production macro rather than new batch logic.

Current changes:
- `tools/preflight_batch.py` mirrors the production macro's actual immediate-subfolder, basename-metadata and output-naming semantics;
- reports discovered/mapped/unmapped images, duplicate source basenames, missing source rows, expected/existing/missing crop counts and missing grid definitions;
- persists `~/.cautious-rotary-phone/last_preflight.txt`;
- writes `~/.cautious-rotary-phone/pending_images.csv` containing only mapped images whose full expected Top/Low output set is not already present;
- the composed batch uses that pending-only metadata file, so the unchanged production macro naturally skips fully completed images on rerun;
- partially complete images remain pending and are re-aligned/re-exported as one plate, avoiding risky per-crop resume logic;
- controller exposes Batch preflight and runs it before starting AHK/Fiji;
- if everything is already complete, the controller starts no AHK/Fiji process;
- `tests/test_preflight_batch.py` covers missing outputs, exact complete outputs and duplicate source basenames using only synthetic temporary files and stdlib unittest.

## Pending manual validation (not a stop condition)
- Desktop Fiji interaction for ROI preset patch and whole-column placement/QC.
- Visual confirmation of native profile peak selection on representative real plates.
- End-to-end composed batch on representative images.
- Confirm the installed Fiji desktop launcher accepts a fourth command-line macro argument for the config-driven visibility shortcut; direct dialog launch remains fallback.

## Highest-value next routes
1. Safely reduce metadata setup effort: generate a reconciliation/template from discovered source images plus existing `images.csv`, preserving original filenames and existing metadata rather than guessing or overwriting authoritative data.
2. Continue auditing existing output/annotation scripts for shared path/settings blocks suitable for the same thin adapters.
3. Research/reuse Fiji/BAR profile/peak alternatives only if native `Array.findMaxima()` proves weak on real plates; do not build a custom colony detector first.
4. Keep batch resume plate-level unless real use demonstrates that per-crop resume would materially save time; current plate-level re-export is simpler and safer.
