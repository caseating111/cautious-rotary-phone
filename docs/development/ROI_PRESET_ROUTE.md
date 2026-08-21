# ROI preset route

Uses the existing **ROI 1-Click Tools** plugin rather than replacing it.

## First use
1. Run `tools/roi_preset_gui.py`.
2. Click **Patch ROI 1-Click Tools…** and select Fiji's installed `Roi 1-Click Tools.ijm`. A backup is created automatically. Reload/restart the toolset once.
3. In Fiji, draw/adjust one representative axis-aligned rectangle ROI and run `fiji/roi_preset_capture.ijm` once.
4. In the GUI, click **Import captured ROI**, name it, **Save preset**, then **Activate**.

The active preset is stored at `~/.cautious-rotary-phone/active_roi_preset.txt`; named presets are stored in `roi_presets.json` beside it. The patched upstream rectangle tool reads the active file immediately before each click, so changing presets does not require rewriting the plugin settings each time.

## Scope
This first slice intentionally handles the fixed rectangular per-culture ROI case only. It preserves ROI 1-Click Tools' own movement, ROI Manager, measurement and other behavior. The capture macro does not try to infer colony/ROI size automatically: the user's one manually validated ROI is the reference.

ROI 1-Click Tools already stores rectangle dimensions internally using ImageJ preferences; this bridge adds named external presets and live switching without replacing the plugin. If the Fiji updater overwrites the patched toolset, rerun the GUI patch action.