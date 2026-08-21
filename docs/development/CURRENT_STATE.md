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

### Profile implementation
Normal operation uses ImageJ's compiled wide-line `getProfile()` with line width equal to the user's tall rectangle width. If an installation/image type unexpectedly returns a short profile, the fallback now uses one-row ImageJ `getStatistics(area, mean)` ROI means rather than an invalid/custom pixel accessor. This keeps the fallback native across grayscale/RGB/16/32-bit images and restores the tall rectangle afterwards. `tests/test_alignment_macro_contract.py` guards against reintroducing the old pixel-call path.

## Crop handoff
`fiji/export_crops_from_alignment.ijm` consumes only an accepted `last_alignment.txt` and checks that the saved alignment belongs to the currently open source image before export.

- saved directory + filename + dimensions are matched when source path information is available;
- title + dimensions is retained only as the backward-compatible fallback for old/unsaved synthetic alignments;
- every grid column and Top/Low crop bound is validated before the first output is written;
- duplicate/missing grid columns and out-of-image crop rectangles fail before partial output;
- source pixels are never modified.

## Batch / fallback
`tools/run_full_column_batch_from_config.py` reuses the original production Fiji folder/CSV/image loop.

- normal route replaces only the old four-point calibration/export block with `full_column_alignment.ijm` + `export_crops_from_alignment.ijm`;
- `--prepare-only` validates/preflights/builds pending-only configured work before Fiji/AHK starts and does not require a Fiji path;
- `--legacy` keeps the original four-point calibration/export block and supports its original 10/12-column contract only;
- controller exposes **Run full-column batch** and **Run 4-point fallback** through the same prepare-before-AHK path;
- after validation and clean preflight, preparation creates the configured `crop_output` root if needed and performs a real temporary directory/file write probe before Fiji starts. A missing/unwritable output root therefore fails before any manual alignment time is spent. `tests/test_batch_prepare_end_to_end.py` and `tests/test_batch_crop_output_root.py` protect this first-run/writeability contract.

## Preflight / metadata
`tools/preflight_batch.py` is the source/crop readiness authority. It checks source mapping, duplicate basenames/metadata rows, grid availability, output collisions, source freshness, crop readability/dimensions, source/crop tree separation and plate-level resume state.

Additional platform/runtime safeguards:
- malformed/unreadable/non-object `config.json` fails with a concise configuration error rather than a traceback;
- derived output path claims are compared with **Windows case-insensitive path semantics** as well as logical-name checks, so case-only output collisions are blocked before Fiji;
- diagnostics distinguish stale/incompatible expected crops, superseded prefix crops, unrelated PNGs and blocking misplaced exact-current crops.

Report: `~/.cautious-rotary-phone/last_preflight.txt`.

### Metadata reconciliation safety
Existing `images.csv` rows remain authoritative. New sources get blank metadata rather than guesses, manual drafts survive rescans, and candidate adoption is explicit with backup.

`tools/reconcile_images_csv.py` now:
- fails cleanly on malformed/non-object config;
- refuses to refresh an existing review whose exact column schema changed, protecting manual draft edits from accidental erasure;
- writes a complete temporary review and atomically replaces the old review only after the write succeeds.

`tools/finalize_images_reconciliation.py` also fails cleanly on malformed/non-object config and verifies the review still matches the live source set before producing a candidate. `tools/metadata_review_gui.py` distinguishes a normal return-code-1 "review written but needs metadata attention" result from structural/fatal return-code-1 errors, so malformed reviews/config are shown as real errors. Candidate adoption remains atomic with an adjacent backup of existing `images.csv`.

## CSV contract
`tools/validate_project_csvs.py` is used before Fiji/Pillow work. `docs/development/CSV_VALIDATION.md` is the full contract.

Important parser/output-safety rules:
- exact headers; surrounding header whitespace is rejected rather than normalized;
- duplicate headers after trimming are rejected cleanly;
- source `Filename` values with surrounding whitespace are rejected because the reused Fiji batch parser matches the raw filename field;
- quoted comma-containing source filenames remain supported;
- ImageJ-unsafe metadata commas/line breaks, composed-handoff semicolons and filename-unsafe output metadata are blocked;
- case-only Experiment/Set identities and case-only condition Types are blocked because the mature Pillow scripts lowercase crop prefixes;
- underscore metadata is allowed, but the validator rejects only combinations of Experiment/Set/Type that flatten to the same case-insensitive legacy `Experiment_Set_Type` prefix. This prevents cross-matching while preserving normal underscore-bearing names.

`tests/test_csv_casefold_contract.py` covers case and underscore-boundary collisions plus valid controls.

## Pillow output route and safety
`tools/run_existing_pillow_from_config.py` is the only supported config-driven entry point for matrices, all-strains, all-strains-dedup and labelled-individual outputs.

Before running an established Pillow job it:
1. validates project CSVs;
2. reuses source/crop preflight when `image_root` is configured;
3. derives exact current crop filenames;
4. rejects duplicate/missing exact-current inputs and duplicate case-insensitive logical crop identities even in standalone mode;
5. creates/verifies `matrix_output` and performs a temporary directory/file write probe before staging any crops;
6. stages only validated exact crops into a disposable directory;
7. normalizes orientation on staged copies only;
8. disables/retains disabled legacy in-place rotation in the configured child copy;
9. runs the established composition script;
10. requires one new **non-empty** top-level output directory;
11. removes staging automatically.

Real `crop_output` files are not rotated or rewritten. `matrix_output` must be outside both `crop_output` and configured `image_root`.

The old unsafe `tools/run_matrices_from_config.py` direct route is removed and guarded against reintroduction.

### Labelled-individual repairs
`existing scripts clean/folder per strain all indiv strains labelled.py` keeps its established Pillow rendering but has narrow handoff/reliability repairs:

1. outputs now stay under the intended unique `MATRIX_OUTPUT`;
2. staged orientation remains wrapper-owned and legacy in-place rotation is disabled;
3. normal staged use maps exact current filenames to strains from authoritative `grid.csv` + `images.csv`, avoiding underscore-fragile filename reparsing;
4. skipped/failed labelled crops return nonzero, allowing the wrapper to retain non-empty partial output for inspection instead of reporting success.

All four controller Pillow choices have representative synthetic end-to-end routes in the suite. The standard/all-strains routes also assert staged rotation leaves real crops unchanged.

### Deferred legacy semantics/polish
`docs/development/DEFERRED_LEGACY_OUTPUT_QUESTIONS.md` records two non-blocking legacy issues that should not drive speculative rewrites:
- extra-WT-removed comments say E2/B while executable logic/output naming point to E2/A; do not guess the intended biological control source;
- standard `make_matrices.py` computes optional WT highlight colour but does not pass it to the strain-label drawing call; default is off and controller does not expose it.

## Visibility
`fiji/apply_global_visibility.ijm` uses outside-grid robust background + inside-grid high percentile and applies one whole-image display range for QC while preserving quantitative source pixels. Keep this display/QC-only until a concrete derived-output requirement exists.

Configured visibility/batch wrappers reject malformed config objects and non-finite numeric settings before Fiji.

## Controller / setup
Controller remains a lightweight control surface for paths, sibling CSV discovery, metadata review, ROI presets, processing settings, preflight/report opening, both Fiji batch routes, Pillow jobs, AHK and output-folder navigation.

Current setup/feedback hardening:
- **Batch preflight** shows a short readiness/pending summary instead of duplicating the full report into a modal;
- full-column/fallback launch collapse only actual current preflight-generated failures to the saved report while current CSV/configuration errors remain direct;
- Processing Settings rejects `NaN`/infinite values before saving;
- unreadable/malformed/non-object existing `config.json` is preserved rather than silently replaced by defaults. The controller shows defaults for recovery but blocks implicit helper/action saves; replacement requires an explicit **Save config** confirmation;
- ROI preset values are normalized before the patched ROI 1-Click Tools handoff. Non-numeric/non-finite/non-positive dimensions are rejected/ignored;
- direct ROI preset Fiji discovery now treats malformed/non-object config as unavailable and falls back to the existing file picker rather than throwing;
- direct metadata-review config parsing rejects non-object config cleanly.

Root `start_controller.cmd` remains deliberately thin: active named conda -> `conda run` -> Windows `py` -> PATH Python. No automatic environment/Fiji/AHK installation layer.

## Annotation route
There is currently no new general-purpose plate-annotation stage beyond the established matrix and labelled-individual Pillow outputs. A reuse search in August 2026 confirmed ImageMagick, Fiji overlays and Pillow all provide mature text annotation primitives. Pillow remains the preferred future route because it is already a project dependency and supports anchored text directly; do **not** invent an annotation metadata/placement contract until a concrete desired derived output is defined. Reuse existing `images.csv`/`grid.csv` metadata wherever possible rather than creating another CSV.

## Mature reuse candidates / stop-loss
### Peak selection
BAR **Find Peaks** remains the first peak-selection fallback but is deliberately not pre-integrated.

If native `Array.findMaxima()` fails on a representative plate after one sensible reposition/retry, keep the manual ROI + native wide-line profile route and test BAR as the peak-selection substitution before any custom detector work. The original four-point route remains immediately available regardless.

### Quantitative yeast-growth measurement
`docs/development/STOWERS_PLATE_MEASUREMENT_CANDIDATE.md` records a mature downstream measurement candidate: Jay Unruh/Stowers `plate analysis jru v1` and its batch companion. The plugin uses a four-corner polygon, bilinear grid interpolation, circular spot measurements/background options and table output; the batch variant can load a saved ROI and recurse a directory.

This is **research only, not integrated**. Accepted `last_alignment.txt` already stores the left/right X positions and every left/right row Y needed to derive the four corner colony centres without changing the alignment schema. If quantitative growth scoring becomes the next end-product need, prove this plugin on one representative accepted plate before any bespoke scoring implementation/controller integration. Keep measurement on unmodified source pixels and abandon the route if it requires compatibility-surgery/retest cycles.

## Automated checks / environment limitation
`.github/workflows/python-glue-tests.yml` runs compileall plus unittest discovery on pushes to `workflow-dev` and PRs with Pillow installed.

The GitHub connector can confirm branch heads and PR-scoped runs, but its available commit-run query only returns PR-triggered runs and direct repository Actions-list URLs are blocked by its allowlist. Do not claim a whole-suite pass from this environment unless a visible run becomes available; rely on narrow deterministic/contract checks here and repository CI elsewhere.

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
4. If quantitative growth measurement becomes a concrete output need after alignment works, test the Stowers plate-analysis plugin on one plate before custom scoring.
5. Continue deterministic setup/output/user-time improvements only where they prevent real failures or repetitive work; avoid duplicative GUI polish.
6. Keep metadata inference conservative; resolve deferred legacy semantics only from authoritative workflow evidence.
