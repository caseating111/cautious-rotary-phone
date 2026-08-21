# Existing Pillow adapters

`tools/run_existing_pillow_from_config.py` exposes existing scripts without rewriting their image-composition logic.

Controller choices:
- `matrices` -> `make_matrices.py`
- `all-strains` -> `allstrain matrix.py`
- `all-strains-dedup` -> `allstrainmatrix extra WT removed.py`
- `label-individual` -> `folder per strain all indiv strains labelled.py`

The launcher replaces only the shared five `Path(r"path here")` setting lines in a temporary configured copy and requires each line to occur exactly once. It then runs that copy with the current Python/conda interpreter.

Before any Pillow output job, the adapter derives the same logical crop prefixes used by the existing scripts from authoritative `grid.csv` + `images.csv`. If more than one real file matches one logical cell prefix, output is blocked instead of allowing the legacy scripts to warn and silently choose the first file. This also catches stale/legacy duplicates that may no longer be represented by current source metadata.

The same selected logical crop set is then normalized with Pillow using the configured crop dimensions. Crops matching the unrotated size are rotated 90° CCW; crops already matching the swapped dimensions are left untouched. Only current logical crop matches are touched, so unrelated images under `crop_output` are ignored. In normal controller use, a current crop whose dimensions match neither configured orientation is rejected before matrix generation.

The temporary configured copies force `ROTATE_IMAGES_90_CCW = False`, so the existing scripts do not perform their old recursive marker-based rotation after the adapter has normalized the crop set. Original source plate images are not touched; this step applies only to derived crop inputs selected from `crop_output`.

This remains a thin glue layer: the existing Pillow matrix/label composition behavior stays authoritative.
