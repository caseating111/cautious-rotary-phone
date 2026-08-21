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
- `fiji/export_crops_from_alignment.ijm`: accepted alignment -> established Top/Low crop naming and geometry.

### Existing production batch composition
- `tools/run_full_column_batch_from_config.py` reuses the existing production Fiji batch macro's folder/CSV/image loop.
- Only the old four-point calibration/export section is replaced in a temporary configured copy by calls to `full_column_alignment.ijm` and `export_crops_from_alignment.ijm`.
- The original four-point macro remains untouched as fallback.
- CSV semantic preflight runs before Fiji starts.

### Existing Pillow output reuse
- `tools/run_existing_pillow_from_config.py` exposes the existing matrix/all-strain/individual-label scripts through saved controller paths without rewriting their image logic.
- Existing scripts remain authoritative; configured temporary copies only replace their shared explicit path block.

### CSV validation
- `tools/validate_project_csvs.py` checks required headers, grid completeness/duplicates, consistent GridCols, unique source filenames, image->grid references and condition-order coverage.

### Lightweight controller / conda
- `tools/workflow_controller.py` persists paths, validates CSVs, launches Fiji/AHK/Pillow helpers and ROI presets.
- `environment.yml` remains minimal (`python`, `pillow`).

## Active branch: runtime-settings-presets
Purpose: remove repeated numeric-setting entry without moving processing into the GUI.

Current changes:
- controller processing-settings dialog for alignment tolerance, crop width/height and visibility parameters;
- composed batch consumes saved crop dimensions and peak tolerance;
- global visibility accepts optional ImageJ macro args but keeps its existing dialog when launched normally;
- `tools/run_fiji_macro_from_config.py` passes saved settings through Fiji/ImageJ's own macro-argument mechanism;
- example config includes the settings;
- dry-run support exists for the config-aware Fiji launcher so command composition can be checked without opening Fiji.

## Pending manual validation (not a stop condition)
- Desktop Fiji interaction for ROI preset patch and whole-column placement/QC.
- Visual confirmation of native profile peak selection on representative real plates.
- End-to-end composed batch on representative images.
- Confirm Fiji desktop invocation accepts the config-launcher's fourth command-line macro argument as expected; direct dialog-driven macros remain fallback if this behaves differently on the installed Fiji build.

## Highest-value next routes after settings merge
1. Reduce metadata setup effort: inspect filename/folder patterns and provide safe assisted `images.csv` generation/reconciliation rather than requiring repeated hand entry. Preserve original filenames as authoritative metadata.
2. Add a lightweight batch preflight/report that counts discovered source images vs `images.csv`, expected crop count and existing outputs before manual alignment starts.
3. Research/reuse Fiji/BAR profile/peak tools only if native `Array.findMaxima()` proves weak on real plates; do not build a custom colony detector first.
4. Inspect current output/annotation scripts for additional shared path/settings blocks that can be exposed through the same generic adapters rather than new implementations.
