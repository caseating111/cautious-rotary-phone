# Branch audit

workflow-C is the active integration/product branch. workflow-dev and alpha-pre-release are historical and are not current implementation bases.

The 2026-08-23 audit covered controller/GUI wiring, Windows launchers, Python 3.11, all/subfolder/single/rerun preparation, crop macro generation, AHK v2 lifecycle, CSV/reconciliation, current raw output routes, tests, and documentation.

Removed or de-exposed routes include the absent visibility launcher/tests, legacy full-column tests, generic dedup CLI, allow-missing, direct unrecorded custom entrypoints, and presentation-normalized GUI output. Historical Fiji/RMI evidence remains in research docs.

The alpha launcher lesson remains preserved: conda is called with call so control returns after an unavailable environment probe.
