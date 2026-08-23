# ROI preset route

Uses the existing **ROI 1-Click Tools** plugin rather than replacing it.

## First use
1. Configure the Fiji executable in the main controller, then run `tools/roi_preset_gui.py`.
2. Click **Patch ROI 1-Click Tools…**. The preset GUI searches the configured Fiji installation for `Roi 1-Click Tools.ijm`, preferring the normal `macros/toolsets/` location. If exactly one install is found it is patched directly; missing/ambiguous installs fall back to the original file picker. A backup is created automatically. Reload/restart the toolset once.
3. In Fiji, draw/adjust one representative axis-aligned **per-culture/crop-size** rectangle ROI and run `fiji/roi_preset_capture.ijm` once.
4. In the GUI, click **Import captured ROI**, name it, **Save preset**, then **Activate**.

The active preset is stored at `~/.cautious-rotary-phone/active_roi_preset.txt`; named presets are stored in `roi_presets.json` beside it. The patched upstream rectangle tool reads the active file immediately before each click, so changing presets does not require rewriting the plugin settings each time.

## Four-point alignment use

The four-point macro selects the plugin's Rotated Rectangle Click Tool for R1C1, R1C(last), R5C1 and R5C(last). Saved width, height and angle provide the per-culture click box and QC box dimensions; the clicked ROI centres remain the authoritative grid references.

## Scope
This slice intentionally handles the fixed rectangular per-culture ROI case only. It preserves ROI 1-Click Tools' own movement, ROI Manager, measurement and other behavior. The capture macro does not try to infer colony/ROI size automatically: the user's one manually validated per-culture ROI is the reference.

ROI 1-Click Tools already stores rectangle dimensions internally using ImageJ preferences; this bridge adds named external presets and live switching without replacing the plugin. If the Fiji updater overwrites the patched toolset, rerun the GUI patch action.

`tests/test_roi_preset_discovery.py` covers configured-Fiji discovery, preset validation and idempotent patching without requiring Fiji itself.
