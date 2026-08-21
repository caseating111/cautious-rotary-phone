# Full-column batch composition

`tools/run_full_column_batch_from_config.py` reuses the existing production Fiji batch macro rather than replacing its folder/CSV/image loop.

It creates a configured copy under `~/.cautious-rotary-phone/`, replaces only the established path/crop settings, and swaps only the old four-point calibration/export block for:

1. `fiji/full_column_alignment.ijm` — manual first/last whole-column alignment + full-grid QC.
2. `fiji/export_crops_from_alignment.ijm` — established Top/Low crop export semantics.

Before interactive Fiji work, the route runs the authoritative CSV validator and `tools/preflight_batch.py`. Preflight checks source/metadata/grid mapping, resume state, output collisions, downstream duplicate logical crop names, source/output tree separation and Fiji macro-argument delimiter hazards. Completed plates are removed from the temporary pending metadata; partially complete plates remain plate-level reruns and are reported explicitly.

The crop helper validates the complete matching grid, duplicate columns and every intended Top/Low rectangle before writing the first PNG, then checks the final export count. Accepted alignment identity includes ImageJ source directory/filename when available so same-named/same-sized real files cannot silently reuse each other's geometry.

`--prepare-only` performs CSV validation, preflight, pending-image generation, exact source-marker checks and configured macro construction without requiring Fiji to start. The controller's **Run full-column batch** uses this as the authoritative preparation step. Only after preparation succeeds does it verify Fiji, optionally start the lightweight AHK helper, and launch the already-built `batch_full_column.configured.ijm` directly. Preparation is therefore not repeated and AHK is not started for ordinary validation/preflight/build failures.

The original production four-point macro remains unchanged as fallback. The adapter verifies expected source markers exactly and refuses to guess if that source structure changes.
