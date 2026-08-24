# Full-column batch composition — historical / retired

The former full-column detector/composition route is not part of the supported workflow-C controller. It is retained only as historical implementation context while related code/tests are retired or migrated.

The supported path is the four-point Fiji workflow:

1. choose a single plate or start a batch/subfolder batch;
2. make four ROI-tool reference clicks;
3. optionally inspect grid QC;
4. accept to export crops, with replacement/discard handling when selected.

Current operational contracts are `docs/development/CURRENT_STATE.md`, `docs/development/CONTROLLER.md`, and `docs/research/fiji-four-point-runtime.md`. Do not revive or test the full-column route as a parallel production workflow without a new explicit decision.