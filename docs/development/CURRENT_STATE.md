# Current state

## Durable line
`workflow-dev`

## Working baseline
- Original four-point Fiji crop macro and original AHK helper remain unchanged as fallback.
- Original Pillow matrix/label scripts remain present under `existing scripts clean/`.
- Synthetic `grid.csv`, `images.csv` and `condition_order.csv` examples exist.
- Implementation is governed by `AGENTS.md` and `IMPLEMENTATION_DECISION_POLICY.md`.

## Implemented

### ROI presets around ROI 1-Click Tools
- `fiji/roi_preset_capture.ijm`: capture one manually validated rectangle size.
- `tools/roi_preset_gui.py`: named presets and active preset selection.
- Minimal optional patch of the published ROI 1-Click Tools rectangle tool reads the active preset before each click; plugin behavior is otherwise preserved.

### Full-column alignment
- `fiji/full_column_alignment.ijm`: manually authoritative first/last whole-column ROIs -> native `getProfile()` + `Array.findMaxima()` row estimates -> interpolated regular grid -> full-grid QC overlay -> accept/retry.
- Accepts optional ImageJ macro args `cols=...;rows=...;tolerance=...` so other macros can compose it via `runMacro`.
- Saves source identity/dimensions with geometry in `~/.cautious-rotary-phone/last_alignment.txt`.
- `fiji/create_synthetic_grid_plate.ijm` supplies a synthetic tilted grid fixture.
- `ahk/full_column_alignment_hotkeys.ah2`: Z advance/accept, X retry.

### Global visibility
- `fiji/apply_global_visibility.ijm`: outside-grid side medians -> robust background; inside-grid high percentile -> one whole-image display range.
- Rejects stale/mismatched alignment geometry.
- Grayscale source uses display range only; RGB-converted source uses an 8-bit QC duplicate because ImageJ RGB display-range operations can alter pixels.
- Quantitative source pixels remain untouched.

### Crop handoff
- `fiji/export_crops_from_alignment.ijm`: small current-image adapter from accepted alignment to the established Top/Low crop convention, names and default 130x546 crop dimensions.
- Intended to be called by the existing batch macro via `runMacro`, not to become a second batch architecture.

### Lightweight controller / Anaconda
- `tools/workflow_controller.py`: persistent paths, CSV header validation, Fiji macro launch, ROI preset launch, AHK start/stop, matrix launch.
- `~/.cautious-rotary-phone/config.json` stores user paths.
- `environment.yml` supplies a minimal conda environment (`python`, `pillow`).

### Existing matrix integration
- `tools/run_matrices_from_config.py` reuses `existing scripts clean/make_matrices.py` unchanged.
- It replaces only that script's explicit path-setting lines in a temporary configured copy, verifies each expected line exactly once, then runs it with the same Python/conda interpreter.

## Pending manual validation (not a stop condition)
- Desktop Fiji interaction for ROI preset patch, full-column placement/QC and global visibility.
- Visual confirmation that row-peak selection is satisfactory on representative real plates.
- End-to-end current-image aligned crop export.

The four-point production macro remains available while these are validated.

## Active next route
1. Wire the existing batch crop loop to call `full_column_alignment.ijm` and `export_crops_from_alignment.ijm` as optional helpers, preserving four-point fallback.
2. Reuse/adapt existing Pillow labelling scripts through controller config before adding new annotation code.
3. Add CSV/template convenience only where it removes repeated manual translation.
4. BAR Find Peaks remains an established fallback if native `Array.findMaxima()` proves insufficient; do not invent a new peak detector first.
