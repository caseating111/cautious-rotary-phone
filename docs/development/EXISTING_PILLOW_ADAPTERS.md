# Existing Pillow adapters

`tools/run_existing_pillow_from_config.py` exposes existing scripts without rewriting their image logic.

Controller choices:
- `matrices` -> `make_matrices.py`
- `all-strains` -> `allstrain matrix.py`
- `all-strains-dedup` -> `allstrainmatrix extra WT removed.py`
- `label-individual` -> `folder per strain all indiv strains labelled.py`

The launcher replaces only the shared five `Path(r"path here")` setting lines in a temporary configured copy and requires each line to occur exactly once. It then runs that copy with the current Python/conda interpreter.

This is intentionally a glue layer: existing Pillow behavior remains authoritative.