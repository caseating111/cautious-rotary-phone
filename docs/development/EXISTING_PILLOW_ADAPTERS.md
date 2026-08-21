# Existing Pillow adapters

`tools/run_existing_pillow_from_config.py` exposes existing scripts without rewriting their image-composition logic.

Controller choices:
- `matrices` -> `make_matrices.py`
- `all-strains` -> `allstrain matrix.py`
- `all-strains-dedup` -> `allstrainmatrix extra WT removed.py`
- `label-individual` -> `folder per strain all indiv strains labelled.py`

The launcher replaces only the shared five `Path(r"path here")` setting lines in a temporary configured copy and requires each line to occur exactly once. It then runs that copy with the current Python/conda interpreter.

Before any Pillow output job, the adapter normalizes derived crop orientation using Pillow and the configured crop dimensions. PNGs matching the unrotated crop size are rotated 90° CCW; PNGs already matching the swapped dimensions are left untouched. This makes reruns/newly added crops idempotent instead of relying on the legacy one-shot `.rotated_90ccw.done` marker.

The temporary configured copies force `ROTATE_IMAGES_90_CCW = False`, so the existing scripts do not perform their old recursive marker-based rotation after the adapter has normalized the crop set. Original source plate images are not touched; this step applies only to derived files under `crop_output`.

This remains a thin glue layer: the existing Pillow matrix/label composition behavior stays authoritative.
