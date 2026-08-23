# Existing Pillow adapters

tools/run_existing_pillow_from_config.py publicly supports matrices, all-strains, and label-individual. The deduplicated renderer is internal to run_dedup_with_control.py, where the user explicitly chooses the WT/control Experiment/Set.

The wrapper validates CSV/source/crop readiness, requires complete exact current crops, stages disposable copies, normalizes only staged orientation, disables legacy in-place rotation, and requires a new non-empty output. The allow-missing flag is retired.

Real crops are never rewritten. Failed jobs remove only new empty output directories and keep non-empty partial results for inspection.

The labelled renderer uses authoritative CSV metadata first. Its historical filename parser remains fallback-only. Strain folders are Windows-component validated and containment-checked beneath MATRIX_OUTPUT.
