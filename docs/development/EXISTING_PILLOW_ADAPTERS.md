# Existing Pillow adapters

`tools/run_existing_pillow_from_config.py` exposes the existing scripts without rewriting their image-composition logic.

Controller choices:
- `matrices` -> `make_matrices.py`
- `all-strains` -> `allstrain matrix.py`
- `all-strains-dedup` -> `allstrainmatrix extra WT removed.py`
- `label-individual` -> `folder per strain all indiv strains labelled.py`

The launcher replaces only the shared five `Path(r"path here")` setting lines in a configured copy and requires each line to occur exactly once. It runs that copy with the current Python/conda interpreter. The configured `IMAGE_ROOT` points at a disposable validated staging directory, not at the real crop tree.

Before any Pillow output job, the adapter runs the authoritative project CSV validator and derives the exact crop contract produced by the current Fiji exporter from `grid.csv` + `images.csv`.

Input policy:
- the exact current exporter filename is authoritative;
- if one exact current crop exists alongside old prefix-compatible files, the old files are ignored rather than allowed to confuse the legacy scripts;
- more than one file with the same exact current exporter filename is blocking;
- if only old/wrong strain-suffix prefix matches exist and the exact current filename is absent, output is blocking: stale crops are never substituted for missing current crops;
- a missing metadata-defined crop is blocking by default, preventing final matrices from quietly containing blank cells because crop generation was incomplete;
- intentional partial output remains available only through explicit CLI `--allow-missing`; it may omit crops but still cannot substitute stale prefix-compatible files;
- when normal controller config includes `image_root`, the wrapper reuses established source/crop preflight before matrix generation. Source images newer than crops, corrupt/wrong-size expected crops, incomplete plates and other blocking source/crop issues stop final Pillow output automatically. Standalone Pillow-only configurations without `image_root` retain the independent route.

After validation, only the selected exact current crops are copied into a temporary flat staging directory under `~/.cautious-rotary-phone/`. All four existing scripts use `IMAGE_ROOT` as a recursive filename pool and do not rely on original parent-folder identity, so this thin staging view removes stale/unrelated files without changing their composition logic.

Crop-orientation normalization happens **only on staged copies**. Staged crops matching the configured unrotated size are rotated 90° CCW; crops already matching the swapped dimensions are left untouched. The real files under `crop_output` are never rotated or rewritten by Pillow output generation. Current crop inputs with incompatible dimensions still fail before the legacy script runs.

Output-tree policy:
- `matrix_output` must remain outside `crop_output`;
- when `image_root` is configured, `matrix_output` must also remain outside `image_root`, because batch preflight scans immediate source-image subfolders and generated matrix folders inside the source tree would otherwise be rediscovered as source images.

Temporary configured copies force `ROTATE_IMAGES_90_CCW = False`, removing dependence on the legacy one-shot rotation marker because staging already supplies the correct orientation.

The existing scripts create a unique output folder early. If a legacy job fails, the wrapper removes only newly created empty output folders and preserves non-empty partial output for inspection. The temporary staged crop tree is automatically removed after the legacy process exits.

Malformed/non-object `config.json` now produces a targeted wrapper error instead of a traceback. `tests/test_output_tree_layout.py` protects both config handling and source/crop/matrix tree separation.

Regression coverage includes exact/stale filename handling, duplicate-exact rejection, non-destructive staged rotation, source-readiness reuse, strict/partial input behavior and a full synthetic source -> unrotated current crops + stale prefix crop -> staging -> actual legacy matrix route that proves the real crop files remain unchanged.

This remains a thin glue layer: existing Pillow composition behavior stays authoritative; the wrapper only validates and prepares a clean, disposable input handoff.
