# Workflow controller

`tools/workflow_controller.py` is intentionally orchestration-only. It stores paths/settings in `~/.cautious-rotary-phone/config.json` and coordinates the existing Fiji, AHK and Pillow routes rather than moving their processing into Tkinter.

Current controls include:
- CSV semantic validation and metadata review;
- ROI presets, synthetic Fiji test plate, direct full-column alignment and configured global visibility;
- batch preflight and full-column batch launch;
- the four existing Pillow output jobs through their thin config adapter;
- start/stop for the lightweight AHK alignment helper;
- direct opening of source, crop, matrix and config folders.

For **Run full-column batch**, the controller now runs `run_full_column_batch_from_config.py --prepare-only` synchronously first. CSV validation, preflight, pending-image generation, source-marker checks and configured-macro construction therefore finish before AHK starts. If preparation succeeds, the controller verifies Fiji and launches the already-built `~/.cautious-rotary-phone/batch_full_column.configured.ijm` directly instead of repeating preparation in a second helper process.

The controller does not reimplement Fiji/ImageJ operations, ROI 1-Click Tools, the existing Pillow composition logic or AHK workflow logic. Child Python helpers use the same Python/conda interpreter as the controller.

Root `start_controller.cmd` is the thin Windows double-click entry point and prefers the repository's named conda environment when available.
