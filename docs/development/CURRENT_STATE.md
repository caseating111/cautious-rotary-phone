# Current state

## Durable line
`workflow-dev`

## Working baseline
- Existing Fiji crop macro, AHK helper and Pillow matrix scripts remain unchanged.
- Synthetic `grid.csv`, `images.csv` and `condition_order.csv` examples exist.
- Implementation is governed by `AGENTS.md` and `IMPLEMENTATION_DECISION_POLICY.md`.

## Implemented now
ROI-size presets around the existing ROI 1-Click Tools plugin:
- `fiji/roi_preset_capture.ijm` captures one manually validated rectangle ROI size.
- `tools/roi_preset_gui.py` stores/selects named presets and writes the active preset file.
- The GUI can minimally patch the published ROI 1-Click Tools macro so its rectangle tool reads the active preset before each click; it creates a backup first.
- Existing plugin behavior (move/ROI Manager/measure/etc.) is preserved.

## Research-backed next route
For full-column alignment, prefer native ImageJ profile/peak machinery before bespoke detection:
- a tall rectangular column ROI can provide a vertical intensity profile using ImageJ profile plotting/getProfile behavior;
- ImageJ has built-in `Array.findMaxima` for 1-D peak positions;
- BAR `Find Peaks` is an established optional alternative if built-in peak handling is insufficient;
- use the two manually positioned first/last whole-column references as authoritative, fit expected rows/columns from those results, then show a full-grid QC overlay.

Do not expand this into custom colony detection unless the profile/peak + manual-reference composition demonstrably fails.

## Exact next implementation target
Prototype the smallest Fiji-only full-column alignment slice on synthetic/representative data: two manual whole-column references -> row peak estimates -> calculated regular grid -> visual overlay -> accept/retry. Keep the current 4-point macro available as fallback until the new route is proven.