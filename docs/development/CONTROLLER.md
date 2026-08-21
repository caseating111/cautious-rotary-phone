# Workflow controller

`tools/workflow_controller.py` is intentionally orchestration-only. It stores paths/settings in `~/.cautious-rotary-phone/config.json` and coordinates the existing Fiji, AHK and Pillow routes rather than moving their processing into Tkinter.

Current controls include:
- CSV semantic validation and metadata review;
- ROI presets, synthetic Fiji test plate, direct full-column alignment and configured global visibility;
- batch preflight, saved preflight-report opening, full-column batch launch and one-click access to the preserved four-point fallback;
- the four existing Pillow output jobs through the safe staging wrapper;
- start/stop for the lightweight AHK alignment helper;
- direct opening of source, crop, matrix and config folders.

Selecting any one of the exact project CSV names (`grid.csv`, `images.csv`, `condition_order.csv`) discovers exact-named siblings in the same folder and fills only still-empty controller fields. Existing path choices are never overwritten.

**Batch preflight** keeps modal feedback short: success shows the pending-image count, while blocking preflight results point to the saved `~/.cautious-rotary-phone/last_preflight.txt` report instead of duplicating the long report into a message box. If preflight fails before a report can be produced, the actual setup/config error is still shown directly.

For **Run full-column batch**, the controller runs `run_full_column_batch_from_config.py --prepare-only` synchronously first. CSV validation, preflight, pending-image generation, source-marker checks and configured-macro construction therefore finish before AHK starts. `--prepare-only` does not require a configured Fiji path. Preflight-generated preparation failures use the same short saved-report handoff; validator/configuration errors remain direct. If preparation succeeds, the controller verifies Fiji and launches the already-built `~/.cautious-rotary-phone/batch_full_column.configured.ijm` directly instead of repeating preparation. If the controller started AHK for this launch and Fiji fails to spawn, that helper is stopped again.

**Run 4-point fallback** uses the same prepare-before-AHK controller path, validator, current/stale crop preflight and pending-image list, but builds `batch_four_point_fallback.configured.ijm` from the preserved production macro without replacing its four-point calibration/export block. The adapter configures paths and crop dimensions only and rejects grids outside the original macro's 10/12-column contract. Semicolon restrictions that exist solely because of the composed route's `runMacro` argument delimiter are not applied to this fallback; source/crop separation, freshness, mapping and collision checks remain active.

The single AHK helper recognizes both the `1 / 2` / `2 / 2` full-column dialogs and the preserved `1 / 4` through `4 / 4` fallback dialogs. It also moves newly created placement dialogs once to a predictable corner without activating them. `X` remains specific to full-column QC retry; `Esc` remains the explicit helper stop.

Configured visibility launch is checked synchronously through its thin launcher so path/configuration errors are shown in the controller rather than disappearing into a child console.

Pillow output jobs are run synchronously through `tools/run_existing_pillow_from_config.py`. That wrapper validates readiness, stages only exact current crop files in a disposable directory, normalizes orientation on the copies, and then runs the existing Pillow composition script. The controller captures its exit status/output so missing/duplicate/incompatible crop errors are visible. Real `crop_output` images are not rotated or rewritten by final-output generation.

The retired direct matrix launcher is intentionally absent; the controller must not bypass the staging wrapper.

The controller does not reimplement Fiji/ImageJ operations, ROI 1-Click Tools, existing Pillow composition logic or AHK workflow logic. Child Python helpers use the same Python/conda interpreter as the controller.

Root `start_controller.cmd` is the thin Windows double-click entry point and prefers the repository's named conda environment when available.
