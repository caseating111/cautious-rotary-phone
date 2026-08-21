# Full-column batch composition

`tools/run_full_column_batch_from_config.py` reuses the existing production batch macro rather than replacing its folder/CSV/image loop.

It creates a temporary configured copy under `~/.cautious-rotary-phone/`, replaces only the original path settings, and swaps only the old four-point calibration/export block for two existing helpers:

1. `fiji/full_column_alignment.ijm` — manual first/last whole-column alignment + QC.
2. `fiji/export_crops_from_alignment.ijm` — established Top/Low crop export semantics.

Before Fiji starts, `tools/preflight_batch.py` verifies the production source/output mapping. In addition to missing metadata/grid checks and resume accounting, it blocks if two distinct source images would claim the same derived crop pathname in one output folder. This prevents one plate from silently overwriting another when Experiment/Set/Type metadata would otherwise generate identical names.

Immediately before PNG export, the crop helper also verifies that every intended Top/Low rectangle fits fully inside the current source image. A bad edge crop therefore fails before the first crop is written instead of leaving a partial set.

The source production macro remains unchanged as fallback. The adapter verifies the expected source markers exactly before patching and refuses to guess if the source structure changes.

The controller's **Run full-column batch** action starts the lightweight alignment hotkeys when configured, then launches this composed route.