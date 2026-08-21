# Matrix config adapter — retired

The old `tools/run_matrices_from_config.py` entry point has been removed.

It directly configured `existing scripts clean/make_matrices.py` against the real `crop_output` tree. That bypassed the newer validation/staging wrapper and could allow the legacy script's in-place rotation behavior to modify production crops.

Use `tools/run_existing_pillow_from_config.py matrices` (or the controller's **Matrices** Pillow job) instead. The authoritative wrapper validates project/source/crop readiness, stages only exact current crop files into a disposable input directory, normalizes orientation on those copies, disables legacy rotation, and then runs the existing matrix composition logic unchanged.

`docs/development/EXISTING_PILLOW_ADAPTERS.md` documents the current route.
