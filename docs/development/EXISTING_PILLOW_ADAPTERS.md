# Existing Pillow adapters

`tools/run_existing_pillow_from_config.py` exposes the existing scripts without rewriting their image-composition logic.

Controller choices:
- `matrices` -> `make_matrices.py`
- `all-strains` -> `allstrain matrix.py`
- `all-strains-dedup` -> `allstrainmatrix extra WT removed.py`
- `label-individual` -> `folder per strain all indiv strains labelled.py`

The launcher replaces only the shared five `Path(r"path here")` setting lines in a temporary configured copy and requires each line to occur exactly once. It runs that copy with the current Python/conda interpreter.

Before any Pillow output job, the adapter runs the authoritative project CSV validator and derives the exact crop contract produced by the current Fiji exporter from `grid.csv` + `images.csv`.

Input policy:
- more than one real file matching one legacy logical prefix is blocking, instead of allowing the legacy scripts to warn and choose the first file;
- a single prefix match with an old/wrong strain suffix is also blocking: the wrapper requires the exact current exporter filename, preventing an obsolete crop from satisfying the legacy script's broader prefix lookup;
- a missing metadata-defined crop is blocking by default, preventing final matrices from quietly containing blank cells because crop generation was incomplete;
- intentional partial output remains available only through explicit CLI `--allow-missing`; it may omit crops but still cannot substitute stale prefix-compatible files;
- when normal controller config includes `image_root`, the wrapper reuses the established batch preflight before matrix generation. Source images newer than crops, corrupt/wrong-size expected crops, incomplete plates and other blocking source/crop preflight issues therefore stop final Pillow output automatically. Standalone Pillow-only configurations without `image_root` retain the independent route.

The selected current crop set is normalized with Pillow using configured crop dimensions. Crops matching the unrotated size are rotated 90° CCW; crops already matching the swapped dimensions are left untouched. Only current logical crop matches are touched, so unrelated images under `crop_output` are ignored. Current crop inputs with incompatible dimensions fail before matrix generation.

`matrix_output` must remain outside `crop_output`, preventing recursive legacy searches from ingesting previously generated matrices. Temporary configured copies force `ROTATE_IMAGES_90_CCW = False`, removing dependence on the legacy one-shot rotation marker.

The existing scripts create a unique output folder early. If a legacy job fails, the wrapper removes only newly created empty output folders and preserves non-empty partial output for inspection.

Regression coverage includes exact/stale filename handling, source-readiness reuse, strict/partial input behavior and a full synthetic source -> crops -> wrapper -> actual legacy matrix end-to-end route.

This remains a thin glue layer: existing Pillow composition behavior stays authoritative; the wrapper only validates and prepares its inputs/handoff.
