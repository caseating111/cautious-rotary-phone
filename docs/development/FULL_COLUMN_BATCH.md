# Full-column batch composition

`tools/run_full_column_batch_from_config.py` reuses the existing production Fiji batch macro rather than replacing its folder/CSV/image loop.

## Full-column route

The configured copy under `~/.cautious-rotary-phone/` replaces only established path/crop settings and swaps only the original four-point calibration/export block for:

1. `fiji/full_column_alignment.ijm` — manually authoritative first/last whole-column alignment, native ImageJ profile/peak selection, starting-position conveniences, full-grid QC and explicit Accept/Retry.
2. `fiji/export_crops_from_alignment.ijm` — established Top/Low crop export semantics.

Before interactive Fiji work, the route runs the authoritative CSV validator and `tools/preflight_batch.py`. Preflight checks source/metadata/grid mapping, resume state, output collisions, downstream duplicate logical crop names, source/output tree separation, crop freshness/dimensions and composed Fiji macro-argument delimiter hazards. Completed plates are removed from the temporary pending metadata; partially complete plates remain plate-level reruns and are reported explicitly.

The reused source loop now checks each raw source `fileName` against that active pending-only metadata **before** opening the image in Fiji. Completed/non-pending plates therefore do not incur an image-open/close cycle during resumed runs. The final Fiji summary reports these as `Not listed / not pending` separately from actual post-metadata skips. The exact existing plain/quoted filename matching is preserved, including quoted comma-containing filenames.

The crop helper validates the complete matching grid, duplicate columns and every intended Top/Low rectangle before writing the first PNG, then checks the final export count. Accepted alignment identity includes ImageJ source directory/filename when available so same-named/same-sized real files cannot silently reuse each other's geometry.

`--prepare-only` performs CSV validation, preflight, pending-image generation, exact source-marker checks and configured macro construction without requiring Fiji to start. After those checks succeed it also creates the configured crop-output root if necessary and proves it is writable with a disposable directory/file probe. The controller's **Run full-column batch** uses this as the authoritative preparation step. Only after preparation succeeds does it verify Fiji, optionally start the lightweight AHK helper, and launch the already-built `batch_full_column.configured.ijm` directly. Preparation is therefore not repeated and AHK is not started for ordinary validation/preflight/build failures.

### Grid widths

The original four-point production macro contains a 10/12-column guard before its calibration block. Because the composed route keeps the old folder/CSV loop, `build_macro()` now explicitly neutralizes **only that legacy guard** in the generated full-column macro. Full-column batches therefore accept any CSV/preflight-valid `GridCols >= 2`, matching the generic interpolation code and preflight contract.

`tests/test_full_column_grid_width_contract.py` protects this distinction. `tests/test_pending_skip_before_open.py` protects the pending-before-open resume behavior.

## Immediate preserved fallback

`--legacy` / controller **Run 4-point fallback** configures the same original production macro but leaves its four-point calibration/export block untouched. It still receives the same CSV validation, source/crop preflight, pending-only image list, configured paths/crop dimensions and shared AHK convenience.

The original macro supports its original 10- or 12-column grid contract only; the adapter rejects other widths before Fiji and the generated legacy macro retains the original source guard. Composed-only semicolon handoff restrictions are not applied to the preserved route because that macro does not use the composed helper argument delimiter.

The fallback is for immediate production continuity if the new full-column route is unsuitable. Do not compare both routes across every plate or develop a second crop implementation.

Both user-facing routes reject malformed/non-object `config.json` and non-finite alignment tolerance with targeted errors rather than handing invalid settings to Fiji.
