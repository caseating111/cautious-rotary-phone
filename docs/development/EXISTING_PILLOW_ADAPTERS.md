# Existing Pillow adapters

`tools/run_existing_pillow_from_config.py` exposes the existing Pillow jobs while keeping their established image-composition behavior authoritative.

Controller choices:
- `matrices` -> `make_matrices.py`
- `all-strains` -> `allstrain matrix.py`
- `all-strains-dedup` -> `allstrainmatrix extra WT removed.py`
- `label-individual` -> `folder per strain all indiv strains labelled.py`

The launcher replaces only the shared five `Path(r"path here")` setting lines in a configured copy and requires each line to occur exactly once. It runs that copy with the current Python/conda interpreter. The configured `IMAGE_ROOT` points at a disposable validated staging directory, not at the real crop tree.

## Narrow labelled-individual repairs

The reused labelled-individual script had two evidenced handoff defects; both are patched narrowly rather than replacing its Pillow label rendering:

1. It already created a unique `MATRIX_OUTPUT` folder but accidentally wrote strain subfolders directly under `MATRIX_ROOT`. It now writes those same labelled files under the intended unique output folder.
2. It historically reparsed Experiment/Set from crop filenames with `split("_")`, even though authoritative `grid.csv` + `images.csv` metadata already exists and valid metadata may contain underscores. Normal staged/controller use now builds the exact current exporter filename -> strain map from those CSVs. The old filename parser remains fallback-only for direct legacy inputs not represented in the current metadata map.

The script declares `ROTATE_IMAGES_90_CCW = False` only to satisfy the shared adapter contract; it has no internal rotation function. Orientation remains owned by the wrapper on disposable staged copies.

`tests/test_label_individual_output.py` protects these contracts. `tests/test_label_individual_end_to_end.py` uses underscore-bearing Experiment/Set/Type metadata to prove wrapper -> staged orientation -> metadata-first lookup -> one non-empty labelled output tree with zero skipped current crops.

Before any Pillow output job, the adapter runs the authoritative project CSV validator and derives the exact crop contract produced by the current Fiji exporter from `grid.csv` + `images.csv`.

Input policy:
- the exact current exporter filename is authoritative;
- if one exact current crop exists alongside old prefix-compatible files, the old files are ignored rather than allowed to confuse the legacy scripts;
- more than one file with the same exact current exporter filename is blocking;
- if only old/wrong strain-suffix prefix matches exist and the exact current filename is absent, output is blocking: stale crops are never substituted for missing current crops;
- a missing metadata-defined crop is blocking by default, preventing final matrices from quietly containing blank cells because crop generation was incomplete;
- intentional partial output remains available only through explicit CLI `--allow-missing`; it may omit crops but still cannot substitute stale prefix-compatible files;
- when normal controller config includes `image_root`, the wrapper reuses established source/crop preflight before matrix generation. Source images newer than crops, corrupt/wrong-size expected crops, incomplete plates and other blocking source/crop issues stop final Pillow output automatically. Standalone Pillow-only configurations without `image_root` retain the independent route.

After validation, only the selected exact current crops are copied into a temporary flat staging directory under `~/.cautious-rotary-phone/`. All four jobs use `IMAGE_ROOT` as a recursive filename pool and do not rely on original parent-folder identity, so this thin staging view removes stale/unrelated files without replacing their composition logic.

Crop-orientation normalization happens **only on staged copies**. Staged crops matching the configured unrotated size are rotated 90° CCW; crops already matching the swapped dimensions are left untouched. The real files under `crop_output` are never rotated or rewritten by Pillow output generation. Current crop inputs with incompatible dimensions still fail before the legacy script runs.

Output-tree policy:
- `matrix_output` must remain outside `crop_output`;
- when `image_root` is configured, `matrix_output` must also remain outside `image_root`, because batch preflight scans immediate source-image subfolders and generated matrix folders inside the source tree would otherwise be rediscovered as source images.

Temporary configured copies force/retain `ROTATE_IMAGES_90_CCW = False`, removing dependence on legacy one-shot rotation markers because staging already supplies the correct orientation.

Each successful job must create one new non-empty top-level output directory. A child script returning exit code zero without producing a usable new output directory is treated as failure rather than reported as completion. Failed jobs remove only newly created empty output folders and preserve non-empty partial output for inspection. The temporary staged crop tree is automatically removed after the legacy process exits.

Malformed/non-object `config.json` produces a targeted wrapper error instead of a traceback. `tests/test_output_tree_layout.py` protects both config handling and source/crop/matrix tree separation.

Regression coverage includes exact/stale filename handling, duplicate-exact rejection, non-destructive staged rotation, source-readiness reuse, strict/partial input behavior, output postconditions, a full synthetic matrix route, and the metadata-first labelled-individual route.

This remains a thin glue layer: established Pillow composition behavior stays authoritative; the wrapper validates and prepares a clean disposable input handoff, with only narrowly evidenced legacy defects patched rather than replaced.
