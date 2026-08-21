# Current state

## Durable line
`workflow-dev`

Routine implementation goes directly onto `workflow-dev`. Do not create a branch for normal fixes, tests, docs, adapters, UI/default changes or low-risk experiments. Old policy/foundation side branches are obsolete/superseded and must not be resumed.

Root `AGENTS.md` and `docs/development/IMPLEMENTATION_DECISION_POLICY.md` are binding: optimize user time-to-reliable-result, reuse mature tools first, preserve manual alignment authority/source pixels, and stop patch/retest escalation early.

## Active architecture
- **Fiji/ImageJ:** interactive alignment, native profile/peak tools, display/QC and crop export.
- **AHK v2:** hotkeys/dialog positioning only.
- **Pillow:** established matrix/label jobs behind validated disposable staging.
- **Tkinter controller:** paths/config/orchestration only.
- **Original four-point Fiji macro:** immediate preserved fallback.

No real experimental data belongs in the repo; synthetic fixtures/examples only.

## Full-column Fiji route
`fiji/full_column_alignment.ijm` keeps manual first/last whole-column placement authoritative:
1. manually confirm first-column tall rectangle;
2. native wide-line `getProfile()` averages it;
3. native `Array.findMaxima()` selects row peaks;
4. manually confirm the same rectangle on the last column;
5. interpolate complete regular grid;
6. inspect full-grid overlay;
7. explicit Accept/Retry;
8. only accepted geometry is persisted and handed to crop export.

Repeated-image conveniences remain suggestion-only:
- same-sized previous first-column ROI may seed the next first-column placement;
- after confirming the **current** first ROI, the previous first-to-last horizontal span may pre-position that current rectangle near the last column;
- last-column failure or QC Retry restores the current attempt's first rectangle so the user need not drag back across the plate.

None of these conveniences auto-accept geometry. `tests/test_alignment_macro_contract.py` protects that contract.

## Batch / fallback
`tools/run_full_column_batch_from_config.py` reuses the original production Fiji folder/CSV/image loop.

- normal route replaces only the old four-point calibration/export block with `full_column_alignment.ijm` + `export_crops_from_alignment.ijm`;
- `--prepare-only` validates/preflights/builds pending-only configured work before Fiji/AHK starts and does not require a Fiji path;
- `--legacy` keeps the original four-point calibration/export block and supports its original 10/12-column contract only;
- controller exposes **Run full-column batch** and **Run 4-point fallback** through the same prepare-before-AHK path.

## Preflight / metadata
`tools/preflight_batch.py` is the source/crop readiness authority. It checks source mapping, duplicate basenames/metadata rows, grid availability, output collisions, source freshness, crop readability/dimensions, source/crop tree separation and plate-level resume state.

Diagnostics distinguish stale/incompatible expected crops, superseded prefix crops, unrelated PNGs and blocking misplaced exact-current crops. Report: `~/.cautious-rotary-phone/last_preflight.txt`.

Metadata reconciliation remains conservative: existing `images.csv` rows are authoritative, new sources get blank metadata rather than guesses, manual drafts survive rescans, and candidate adoption is explicit with backup.

## CSV contract
`tools/validate_project_csvs.py` is used before Fiji/Pillow work.

Important parser-safety rules:
- exact headers; surrounding header whitespace is rejected rather than normalized;
- duplicate headers after trimming are rejected cleanly;
- source `Filename` values with surrounding whitespace are rejected because the reused Fiji batch parser matches the raw filename field;
- quoted comma-containing source filenames remain supported;
- ImageJ-unsafe metadata commas/line breaks, composed-handoff semicolons and filename-unsafe output metadata are blocked.

`docs/development/CSV_VALIDATION.md` has the full contract.

## Pillow output route and safety
`tools/run_existing_pillow_from_config.py` is the only supported config-driven entry point for matrices, all-strains, all-strains-dedup and labelled-individual outputs.

Before running an established Pillow job it:
1. validates project CSVs;
2. reuses source/crop preflight when `image_root` is configured;
3. derives exact current crop filenames;
4. blocks duplicate/missing exact-current inputs;
5. stages only validated exact crops into a disposable directory;
6. normalizes orientation on staged copies only;
7. disables/retains disabled legacy in-place rotation in the configured child copy;
8. runs the established composition script;
9. requires one new **non-empty** top-level output directory;
10. removes staging automatically.

Real `crop_output` files are not rotated or rewritten. `matrix_output` must be outside both `crop_output` and configured `image_root`.

The old unsafe `tools/run_matrices_from_config.py` direct route is removed and guarded against reintroduction.

### Labelled-individual repairs
`existing scripts clean/folder per strain all indiv strains labelled.py` keeps its established Pillow rendering but has three narrow handoff repairs:

1. It already created a unique `MATRIX_OUTPUT` but accidentally wrote strain folders beside it under `MATRIX_ROOT`; outputs now go under the intended unique folder.
2. The shared staged adapter expects an explicit rotation setting. The label job now declares `ROTATE_IMAGES_90_CCW = False` but has no internal rotation function; staged orientation remains wrapper-owned.
3. Normal controller/staged use no longer reparses Experiment/Set from generated filenames. It constructs the exact current filename -> strain map from authoritative `grid.csv` + `images.csv`. The old underscore-fragile filename parser remains fallback-only for direct legacy inputs outside that current map.

Regression coverage:
- `tests/test_label_individual_output.py`: unique output root, adapter rotation contract, metadata-first lookup before legacy fallback.
- `tests/test_label_individual_end_to_end.py`: underscore-bearing Experiment/Set/Type metadata, exact staged crops, zero skips, one output tree, expected strain subfolders, and unchanged real crop dimensions.
- the pre-existing all-alias adapter test now also has a valid `label-individual` rotation-setting contract to configure.

The other three Pillow jobs were audited and already use their unique top-level output folders and structured metadata-based crop lookup correctly.

### Deferred legacy semantics/polish
`docs/development/DEFERRED_LEGACY_OUTPUT_QUESTIONS.md` records two non-blocking legacy issues that should not drive speculative rewrites:
- extra-WT-removed comments say E2/B while executable logic/output naming point to E2/A; do not guess the intended biological control source;
- standard `make_matrices.py` computes optional WT highlight colour but does not pass it to the strain-label drawing call; default is off and controller does not expose it.

## Visibility
`fiji/apply_global_visibility.ijm` uses outside-grid robust background + inside-grid high percentile and applies one whole-image display range for QC while preserving quantitative source pixels. Keep this display/QC-only until a concrete derived-output requirement exists.

Configured visibility/batch wrappers reject malformed config objects and non-finite numeric settings before Fiji.

## Controller / setup
Controller remains a lightweight control surface for paths, sibling CSV discovery, metadata review, ROI presets, processing settings, preflight/report opening, both Fiji batch routes, Pillow jobs, AHK and output-folder navigation.

Root `start_controller.cmd` remains deliberately thin: active named conda -> `conda run` -> Windows `py` -> PATH Python. No automatic environment/Fiji/AHK installation layer.

## Mature peak fallback / stop-loss
BAR **Find Peaks** was re-verified against official ImageJ documentation in August 2026 and remains the first peak-selection fallback, but is deliberately not pre-integrated.

If native `Array.findMaxima()` fails on a representative plate after one sensible reposition/retry, keep the manual ROI + native wide-line profile route and test BAR as the peak-selection substitution before any custom detector work. The original four-point route remains immediately available regardless.

## Automated checks / environment limitation
`.github/workflows/python-glue-tests.yml` runs compileall plus unittest discovery on pushes to `workflow-dev` and PRs with Pillow installed.

This ChatGPT execution environment cannot obtain a local checkout because outbound GitHub DNS is unavailable. The exposed GitHub status/run APIs also do not provide a reliable direct-push CI result here. Do not claim a whole-suite pass from this environment; rely on repository CI when visible elsewhere and narrow deterministic/contract reasoning here.

## Pending minimal desktop validation — not a stop condition
One representative real plate remains the important interactive uncertainty:
- Fiji `waitForUser` rectangle interaction;
- native wide-line profile on real plate data;
- `Array.findMaxima()` row selection;
- first/last interpolation and full-grid QC;
- crop handoff;
- optional AHK convenience.

If it succeeds, one same-sized next plate checks both suggestion-only geometry conveniences during normal use. Do not broadly stress-test first.

## Highest-value next routes
1. Run `--prepare-only` with real configured metadata when available.
2. Perform the minimal representative desktop route in `MINIMAL_DESKTOP_VALIDATION.md`.
3. If native peaks remain weak after one sensible retry, test BAR Find Peaks before custom detection.
4. Continue deterministic setup/output/user-time improvements that can be proven without repeated manual testing.
5. Keep metadata inference conservative; resolve deferred legacy semantics only from authoritative workflow evidence.
