# Workflow controller

Launch with start_controller.cmd. It runs tools/workflow_controller_extended.py and stores config below the user .cautious-rotary-phone folder.

Setup covers paths, CSV discovery, metadata review, preflight, and explicit project layout. Align and Export covers all, subfolder, single, and rerun four-point modes plus Skip done, replacement, QC, source hiding, and cancel cleanup. Outputs covers validated raw Pillow jobs, raw custom matrices, and explicit preferred-WT selection. Settings covers crop dimensions, ROI presets, logs, report, config folder, and reboot.

The controller checks ROI readiness before Fiji launch, owns only recorded processes, and does not infer success from process exit. The macro completion sentinel and subsequent preflight are authoritative.

The AHK v2 helper provides Fiji-scoped hotkeys/window ordering and preserves launcher lowering, toolbar placement, duplicate containment, restart, source hiding, and cancel cleanup.

Presentation/global-visibility controls and full-column detection are retired.
