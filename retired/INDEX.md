# Retired runtime routes

These implementations are retained only as historical reference. They are deprecated, unsupported, excluded from the current controller, and must not be scanned, adapted, tested, or accommodated unless the user explicitly restores one.

- Full-column alignment and batch entry points in `fiji/full_column_alignment.ijm`, `fiji/export_crops_from_alignment.ijm`, and the non-legacy route in `tools/run_full_column_batch_from_config.py`.
- Standalone synthetic-plate, global-visibility, direct Fiji macro, full-column batch, and four-point fallback controller actions.
- Manual Start/Stop alignment-hotkey controller actions; the supported one-plate action manages its helper lifecycle.

Current canonical basic-CSV actions are:

- alignment: **Run one-plate 4-point proof (choose plate)**;
- selected DONE rerun: **Reset / re-run selected DONE plate**;
- reconciliation/validation: **Reconcile / validate CSV workflow**;
- Fiji invocation: `tools/run_one_plate_validation.py`, currently using the configured Fiji/Jaunch executable and the installation's single-instance behavior. The retired custom RMI helper has been deleted.
