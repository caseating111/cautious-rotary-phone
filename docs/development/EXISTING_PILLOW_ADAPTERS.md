# Existing Pillow adapters

The current user route is the unified BCM applet. `tools/run_existing_pillow_from_config.py` retains strict internal adapters for matrices, all-strains, and label-individual. The mature deduplication patch helpers remain in `run_dedup_with_control.py`; preferred WT selection now occurs inside BCM rather than a separate GUI.

Generic adapter calls validate CSV/source/crop readiness and require their complete exact requested crop contract. BCM first filters the contract to selected groups/strains, conditions, and states. Both routes stage disposable copies, normalize only staged orientation, disable legacy in-place rotation, and verify non-empty expected output. The old public allow-missing flag remains retired.

Real crops are never rewritten. Failed jobs remove only new empty output directories and keep non-empty partial results for inspection.

The labelled renderer uses authoritative CSV metadata first. Its historical filename parser remains fallback-only. Strain folders are Windows-component validated and containment-checked beneath MATRIX_OUTPUT.
