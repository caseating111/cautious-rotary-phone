# Workflow controller

`tools/workflow_controller.py` is intentionally orchestration-only. It stores paths/settings in `~/.cautious-rotary-phone/config.json` and coordinates the existing Fiji, AHK and Pillow routes rather than moving their processing into Tkinter.

Current controls include:
- CSV semantic validation and metadata review;
- ROI presets, synthetic Fiji test plate, direct full-column alignment and configured global visibility;
- batch preflight and full-column batch launch;
- the four existing Pillow output jobs through their thin config adapter;
- start/stop for the lightweight AHK alignment helper;
- direct opening of source, crop, matrix and config folders.

For **Run full-column batch**, the controller runs `run_full_column_batch_from_config.py --prepare-only` synchronously first. CSV validation, preflight, pending-image generation, source-marker checks and configured-macro construction therefore finish before AHK starts. `--prepare-only` no longer requires even a configured Fiji path. If preparation succeeds, the controller then verifies Fiji and launches the already-built `~/.cautious-rotary-phone/batch_full_column.configured.ijm` directly instead of repeating preparation. If the controller started AHK for this launch and Fiji fails to spawn, that helper is stopped again.

Configured visibility launch is also checked synchronously through its thin launcher so path/configuration errors are shown in the controller rather than disappearing into a child console.

Pillow output jobs are deterministic and are now run synchronously from the controller. The legacy adapter still performs the image work and opens the output folder; the controller simply captures its exit status/output so missing/ambiguous/incompatible crop errors are shown directly. No success modal is added—the status line updates when the job finishes.

The controller does not reimplement Fiji/ImageJ operations, ROI 1-Click Tools, existing Pillow composition logic or AHK workflow logic. Child Python helpers use the same Python/conda interpreter as the controller.

Root `start_controller.cmd` is the thin Windows double-click entry point and prefers the repository's named conda environment when available.
