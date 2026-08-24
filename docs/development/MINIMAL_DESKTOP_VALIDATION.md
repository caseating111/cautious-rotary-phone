# Minimal desktop validation

All automatable logic is covered separately. This desktop session checks only real Fiji/window/visual behavior.

1. Start start_controller.cmd under Miniforge workflow-c Python 3.11.
2. Configure Fiji, AHK v2, roots, and project CSVs; run Reconcile / validate CSV workflow.
3. Run one ordinary plate with Run single image.
4. Confirm one usable Fiji GUI, native-size toolbar, and no unrelated Java windows moved.
5. Place the four required centers. Confirm Z advances and C cancels only the owned workflow.
6. With QC enabled, inspect rotated/skewed full-grid QC, Retry once, then Accept.
7. Run one representative plate with QC disabled.
8. Rerun one completed plate and confirm old crops archive only after accepted bounds-valid geometry.
9. Confirm the redundant launcher loses AlwaysOnTop and moves behind the usable stack.
10. Close and reboot the controller; confirm owned AHK/wrapper processes end and unrelated processes remain.
11. Run preflight and confirm the plate is complete.

Do not send real-image pixels or screenshots to agents. Report textual pass/fail observations only.
