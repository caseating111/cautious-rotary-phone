# Current state

## Durable line
`workflow-dev` is the only active development line. Routine work goes directly here; do not create side branches for ordinary fixes/features/tests/docs. Current repository branches are `main`, `workflow-dev` and `alpha-pre-release`; `alpha-pre-release` points at an ancestor of `workflow-dev` and is a stale pre-release pointer, not a development line. Previously superseded side branches are no longer present.

Binding rules: root `AGENTS.md` and `docs/development/IMPLEMENTATION_DECISION_POLICY.md`. Optimize total user time-to-reliable-result, reuse mature tools first, preserve source pixels/manual alignment authority, prove small routes, and stop patch/retest escalation early.

## Active workflow
- **Fiji/ImageJ:** manual first/last whole-column alignment, native profile/peak selection, full-grid QC, crop export, display-only visibility.
- **AHK v2:** Z/X dialog convenience and placement positioning only.
- **Pillow:** established matrix/label jobs behind validated disposable staging.
- **Tkinter controller:** paths/config/orchestration only.
- **Original four-point Fiji macro:** preserved immediate fallback.

No real experimental data belongs in the repo.

## Full-column alignment
`fiji/full_column_alignment.ijm`:
1. user confirms one tall rectangle around the first column;
2. ImageJ wide-line `getProfile()` averages across the rectangle width;
3. native `Array.findMaxima()` returns peaks by descending strength; keep strongest expected count, then sort top-to-bottom;
4. user confirms the same rectangle on the last column;
5. interpolate complete grid;
6. inspect overlay and explicitly Accept/Retry;
7. only accepted geometry is saved.

Official ImageJ docs confirm both thick `makeLine(..., lineWidth)` and wide-line pixel averaging. The emergency profile fallback uses ImageJ `getStatistics(area, mean)` row means, not custom pixel code.

Previous accepted same-sized geometry may only **suggest** the next first ROI and first-to-last span. It never auto-accepts. Retry/failure restores the current first ROI.

Detailed contract: `docs/development/FULL_COLUMN_ALIGNMENT.md`. Regression: `tests/test_alignment_macro_contract.py`.

## Crop export
`fiji/export_crops_from_alignment.ijm` verifies `last_alignment.txt` belongs to the current image (path+filename+dimensions when available), validates the complete grid and every intended Top/Low crop before the first write, then exports without modifying source pixels.

Detailed contract: `docs/development/ALIGNED_CROP_HELPER.md`.

## Batch + fallback
`tools/run_full_column_batch_from_config.py` reuses the established production folder/CSV loop.

Current important behavior:
- `--prepare-only` validates CSVs, preflights, creates the pending-only metadata file, builds the configured macro, creates `crop_output` if needed and proves it writable before Fiji starts;
- the reused Fiji loop now looks up raw `fileName` in the active metadata **before** `open(fullPath)`, so completed/non-pending plates are not loaded during resumed batches;
- its final summary separates `Not listed / not pending` from real post-metadata skips;
- the composed full-column macro neutralizes only the old pre-calibration 10/12-column guard, so full-column batches accept any validated `GridCols >= 2`;
- `--legacy` keeps the original four-point calibration/export block **and** original 10/12-only guard.

Tests: `tests/test_pending_skip_before_open.py`, `tests/test_full_column_grid_width_contract.py`, `tests/test_batch_prepare_end_to_end.py`, `tests/test_batch_crop_output_root.py`.

Detailed route: `docs/development/FULL_COLUMN_BATCH.md`.

## Preflight / CSV / metadata safety
`tools/preflight_batch.py` is the source/crop readiness authority. It covers source mapping, grid availability, duplicate basenames/rows, crop freshness/readability/dimensions, output collisions, tree separation and plate-level resume state. Output collision checks include Windows case-insensitive path semantics.

`tools/validate_project_csvs.py` protects the actual Fiji/Pillow parsers rather than inventing a new format. Important rules include exact headers, raw filename whitespace rejection, quoted comma-filename support, ImageJ-unsafe metadata delimiters/line breaks, Windows filename safety, and case/underscore collision checks for the mature Pillow `Experiment_Set_Type` prefix lookup.

Metadata reconciliation remains conservative: existing `images.csv` is authoritative, new sources get blank metadata, drafts survive rescans, malformed review schemas are refused before overwrite, review refresh is atomic, candidate adoption is explicit/validated/backed up.

Detailed CSV contract: `docs/development/CSV_VALIDATION.md`.

## Pillow outputs
`tools/run_existing_pillow_from_config.py` is the supported entry for `matrices`, `all-strains`, `all-strains-dedup` and `label-individual`.

Before an established Pillow child runs it validates project/source readiness, resolves exact current crop filenames, rejects missing/duplicate/case-colliding logical inputs, creates/probes `matrix_output`, stages only exact crops, normalizes orientation on staged copies, disables legacy in-place rotation, requires one new non-empty output folder and removes staging.

Real `crop_output` files are never rotated/rewritten. All four controller choices have representative synthetic end-to-end tests.

Detailed route: `docs/development/EXISTING_PILLOW_ADAPTERS.md`. Deferred legacy semantics: `docs/development/DEFERRED_LEGACY_OUTPUT_QUESTIONS.md`.

## Visibility
`fiji/apply_global_visibility.ijm` derives one display range from outside-grid robust background plus an inside-grid high percentile. It verifies current-image alignment identity and preserves quantitative pixels; RGB uses a disposable 8-bit QC duplicate. Keep this display/QC-only.

Detailed route: `docs/development/GLOBAL_VISIBILITY.md`.

## Controller / setup
Controller stays a thin orchestration surface. It provides paths, CSV discovery/validation, metadata review, ROI presets, settings, preflight/report opening, both Fiji batch routes, Pillow jobs, AHK and output navigation.

Important hardening:
- malformed/unreadable/non-object existing `config.json` is preserved rather than silently overwritten; implicit config-driven actions are blocked until explicit replacement;
- all config-driven workflow actions honor that save guard;
- processing/ROI numeric settings reject non-finite or invalid values;
- standalone metadata/ROI helpers also handle non-object config cleanly;
- `start_controller.cmd` remains thin: named conda -> Windows `py` -> PATH Python. No installer layer.

Environment: `environment.yml` = Python >=3.11 + Pillow. CI runs compileall + unittest discovery on Python 3.11 **and 3.14**.

## Mature fallbacks / optional routes
### Peak fallback
If native `Array.findMaxima()` is still unreliable after one sensible reposition/retry on the representative plate, test mature BAR **Find Peaks** before custom detection. Do not pre-integrate it. The four-point route is always available.

See `docs/development/BAR_FIND_PEAKS_FALLBACK.md`.

### Quantitative growth measurement
Jay Unruh/Stowers `plate analysis jru v1` is the first mature measurement candidate. `fiji/stowers_measure_current_alignment.ijm` is an **optional one-plate proof adapter only**: it verifies accepted geometry belongs to the current source, creates the plugin's required UL→UR→LR→LL polygon, displays geometry-derived spot count/XY ratio, then opens the plugin's native options dialog. It does not guess radius, replicate grouping or background settings and is not exposed in the controller.

The current upstream **batch** plugin must not be used unchanged: its active directory-analysis code writes both `_avg.xls` and `_sem.xls` from `stats2[0]`, while its plotting path correctly uses `stats2[1]` for errors. If the single-plate proof succeeds and batch measurement is useful, prefer a tiny verified patch/wrapper around the mature plugin rather than custom scoring code.

See `docs/development/STOWERS_PLATE_MEASUREMENT_CANDIDATE.md`.

### General annotation
No new generic annotation stage yet. Pillow is the preferred future route because it is already installed and has mature anchored text rendering, but do not invent another metadata/placement contract until a concrete derived annotation output is defined. Reuse existing CSV metadata where possible.

## Pending minimal desktop validation
The main remaining uncertainty is one representative real plate:
- Fiji `waitForUser` whole-column interaction;
- real wide-line profile;
- native row peaks;
- interpolation/full-grid overlay;
- accepted crop handoff;
- optional AHK Z/X convenience.

Use one ordinary plate, allow one sensible retry, then stop. If it succeeds, one same-sized next plate validates both previous-geometry suggestions during normal use. Do not broad-stress-test first.

Exact checklist: `docs/development/MINIMAL_DESKTOP_VALIDATION.md`.

## Highest-value next work
1. Run `--prepare-only` with real configured metadata when available.
2. Perform the one-plate desktop validation.
3. If peaks fail after one retry, test BAR before custom detection.
4. Continue deterministic changes only when they prevent a real failure or remove repetitive work.
5. If quantitative measurement becomes a concrete need, use the Stowers one-plate proof before custom scoring.
6. Keep annotation/legacy biological semantics deferred until authoritative output requirements exist.

## Environment limitation
The GitHub connector can verify branch/file state but direct-push Actions-run listing is not exposed here; do not claim a whole-suite pass from this environment. Repository CI is the whole-suite authority when visible elsewhere.
