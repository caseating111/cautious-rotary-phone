# Current state

## Durable line
`workflow-dev`

Routine implementation goes directly onto `workflow-dev`. Do not create a branch for normal fixes, tests, UI, docs, adapters, or low-risk experiments. The old policy/foundation side branches are obsolete/superseded and must not be resumed.

Implementation remains governed by root `AGENTS.md` and `docs/development/IMPLEMENTATION_DECISION_POLICY.md`: optimize for fast reliable workflow results, reuse mature tools first, keep manual alignment authority, preserve source pixels, and stop patch/retest cycles early.

## Working architecture

- **Fiji/ImageJ:** interactive image work, manual alignment, native profile/peak tools, crop export and QC.
- **AutoHotkey v2:** only hotkeys and non-destructive dialog placement convenience.
- **Pillow:** deterministic composition/labels through the existing scripts, now behind validated staging.
- **Tkinter controller:** orchestration/config/path navigation only.
- **Original four-point Fiji macro:** preserved unchanged under `existing scripts clean/` and exposed as an immediate fallback.

No real experimental CSV/image data is committed. Synthetic CSVs/images remain the machine fixtures.

## Current Fiji alignment route

`fiji/full_column_alignment.ijm` is the active experimental speed-up:

1. user manually confirms one tall rectangle around the full first grid column;
2. native ImageJ wide-line `getProfile()` averages the column; the explicit pixel loop is fallback only;
3. native `Array.findMaxima()` selects row peaks;
4. user manually confirms the same rectangle at the last column;
5. first/last row centers interpolate the complete regular grid;
6. Fiji draws the complete proposed grid overlay;
7. user explicitly Accepts or Retries;
8. only accepted geometry is persisted to `~/.cautious-rotary-phone/last_alignment.txt` and handed to crop export.

Manual first/last placement and full-grid QC remain authoritative.

### Repeated-image conveniences
- A previous accepted first-column rectangle from a same-sized image is offered only as a movable starting suggestion.
- After the user confirms the **current** first-column ROI, a valid previous same-sized first-to-last horizontal span can move that same current rectangle near the last column. The user must still fine-tune and confirm it.
- If last-column ROI/profile validation fails, or the user chooses QC Retry, the current attempt's first-column rectangle is restored before the next first-column prompt. This removes a needless full-plate drag without accepting anything automatically.
- `tests/test_alignment_macro_contract.py` protects all three invariants: previous geometry is suggestion-only, last-column confirmation remains manual, and saved alignment is Accept-gated.

`docs/development/MINIMAL_DESKTOP_VALIDATION.md` keeps the remaining interactive burden to one representative plate, plus one same-sized next plate only if the first works. The second image covers both first-ROI seeding and previous-span last-column pre-positioning during the normal interaction; it is not a separate validation pass.

## AHK alignment helper

`ahk/full_column_alignment_hotkeys.ah2` is shared by both alignment routes:

- `Z`: advances full-column dialogs, accepts full-column QC, advances the preserved four-point dialogs, and dismisses `ALL DONE`;
- `X`: full-column QC Retry only;
- `Esc`: explicit helper stop.

It reuses the original helper's Windows shell-hook pattern to move only newly created placement dialogs (`1 / 2`, `2 / 2`, `1 / 4` through `4 / 4`) once to a predictable corner. The hook does not activate windows or send keys. QC positioning is untouched. `tests/test_controller_contract.py` protects the move-only behavior.

## Batch composition and fallback

`tools/run_full_column_batch_from_config.py` reuses the original production Fiji batch macro's folder/CSV/image loop.

### Full-column route
Only the old four-point calibration/export block is replaced with calls to:
- `fiji/full_column_alignment.ijm`
- `fiji/export_crops_from_alignment.ijm`

`--prepare-only` validates metadata, runs preflight, writes pending-only `pending_images.csv`, verifies patch markers and builds the configured macro without launching Fiji or requiring a configured Fiji executable.

### Preserved four-point route
`--legacy` configures only the original macro's path/state/crop-size settings and leaves its original four calibration/export interactions untouched. It uses the same validator, source/crop preflight and pending-only image list.

The preserved macro's actual original contract is explicit: only 10- or 12-column grids. Unsupported widths fail before Fiji.

Composed-only semicolon path restrictions are disabled for `--legacy`; all substantive source/crop/metadata checks remain active.

The controller exposes both **Run full-column batch** and **Run 4-point fallback** through one prepare-before-AHK launch path. If a click starts AHK and Fiji then fails to spawn, that helper is stopped again.

Synthetic `tests/test_batch_prepare_end_to_end.py` proves both preparation routes without Fiji.

## Preflight / resume

`tools/preflight_batch.py` mirrors the production immediate-subfolder and crop-name semantics.

It checks:
- source/crop tree separation;
- discovered/mapped/unmapped images;
- duplicate source basenames and duplicate `images.csv` rows;
- grid availability and route geometry constraints;
- output collisions and downstream logical-name ambiguity;
- source freshness;
- expected crop readability and configured dimensions;
- plate-level completion/pending status.

Resume intentionally remains **plate-level**, not per-crop. A partial/stale plate is rerun as a whole instead of adding fragile resume state.

Crop diagnostics:
- **STALE EXPECTED CROPS — WILL REBUILD**: expected crop older than source;
- **INCOMPATIBLE EXPECTED CROPS — WILL REBUILD**: corrupt/wrong dimensions;
- **SUPERSEDED PREFIX CROPS — NON-BLOCKING**: old/wrong strain suffix matching a current logical prefix; safe to leave because final Pillow staging uses exact current names only;
- **OTHER UNEXPECTED CROP PNGS — NON-BLOCKING**: outside current crop contract;
- **EXACT CURRENT CROP IN UNEXPECTED FOLDER**: blocking, because a rerun would create a second exact-current filename.

The report is written to `~/.cautious-rotary-phone/last_preflight.txt`; the controller has **Open last preflight report**.

## CSV contract

`tools/validate_project_csvs.py` remains the authoritative project validator used before Fiji/Pillow work.

It checks required columns, complete/consistent grids, unique image filenames, image-to-grid mapping, condition ordering, ImageJ line-parser unsafe metadata, composed-macro semicolons and Windows filename-unsafe output metadata.

Header behavior is now intentionally exact: surrounding whitespace in column names is rejected early with a targeted error, rather than being silently trimmed and later breaking the reused Pillow `csv.DictReader` scripts. Duplicate headers that collapse to the same name after trimming are also rejected cleanly. `tests/test_csv_validation.py` covers these cases.

Comma-containing **source filenames** remain supported because the reused production ImageJ macro explicitly handles quoted filenames containing commas.

## Metadata reconciliation

`tools/reconcile_images_csv.py` scans current source folders while keeping existing `images.csv` authoritative:
- existing rows are preserved;
- new sources are added with blank metadata rather than guessed values;
- manual draft metadata is preserved across rescans by `(Folder, Filename)`;
- duplicate basenames/rows and removed sources are explicit statuses.

`tools/finalize_images_reconciliation.py` creates a candidate only when the edited review still matches the current source set and passes project validation.

`tools/metadata_review_gui.py` can explicitly adopt that validated candidate as `images.csv`, creating an adjacent backup first. It deliberately uses the normal spreadsheet editor for CSV editing rather than reimplementing a table editor in Tkinter.

## Pillow output safety

`tools/run_existing_pillow_from_config.py` is the **only supported config-driven Pillow output entry point** for:
- matrices;
- all strains;
- all strains with extra WT removed;
- labelled individual crops.

The original Pillow composition scripts remain authoritative and unchanged under `existing scripts clean/`.

Before composition the wrapper:
1. validates project CSVs;
2. reuses source/crop preflight when `image_root` is configured;
3. derives exact current exporter filenames;
4. blocks duplicate exact current inputs and missing current inputs;
5. ignores superseded prefix-compatible files only when the exact current file exists;
6. copies only validated exact current crops into a disposable staging directory;
7. normalizes orientation on those **staged copies only**;
8. configures the original legacy script to read the staging directory with its own rotation disabled;
9. runs the legacy script;
10. deletes staging automatically.

Real files under `crop_output` are not rotated or rewritten by Pillow output generation.

The old `tools/run_matrices_from_config.py` was removed because it bypassed validation/staging and could invoke the legacy matrix script directly against real `crop_output`, where legacy in-place rotation was still enabled. `docs/development/MATRIX_CONFIG_ADAPTER.md` is now a retirement note and `tests/test_safe_pillow_entrypoint.py` protects against restoring that unsafe route.

`tests/test_pillow_wrapper_end_to_end.py` proves a real synthetic legacy matrix run using current unrotated crops plus a stale prefix crop while confirming real crop dimensions remain unchanged.

## Visibility

`fiji/apply_global_visibility.ijm` calculates a robust outside-grid background and inside-grid high percentile, then applies one whole-image display range while preserving quantitative source pixels. RGB uses a disposable 8-bit QC duplicate because ImageJ display-range operations can modify RGB pixels.

This remains intentionally **QC/display only**. Do not build a second derived intensity pipeline before the core alignment route is proven and a concrete final-output requirement exists.

Configured visibility and batch wrappers now reject non-finite numeric values before Fiji. Malformed/non-object `config.json` is reported as a short configuration error on those user-facing launch paths rather than surfacing a Python traceback. `tests/test_fiji_launcher.py` and `tests/test_numeric_config_guards.py` cover these guards.

## Controller / setup

`tools/workflow_controller.py` remains orchestration-only.

Useful shortcuts already present:
- selecting one exact project CSV (`grid.csv`, `images.csv`, `condition_order.csv`) auto-fills exact sibling CSVs only into still-empty fields;
- batch preflight + saved report navigation;
- full-column and four-point batch launch;
- Pillow output job selection;
- ROI preset GUI;
- metadata review;
- source/crop/matrix/config folder navigation;
- start/stop AHK.

Fiji and AHK executable discovery remains a one-time persisted manual selection. Automatic installation/discovery was deliberately not added because the small setup saving does not justify extra Windows/environment failure modes.

Root `start_controller.cmd` remains thin: active named conda -> `conda run` -> Windows `py` -> PATH Python. `environment.yml` remains minimal (`python>=3.11`, `pillow`).

## Mature peak fallback / stop-loss

The BAR **Find Peaks** route was re-verified against current official ImageJ documentation in August 2026 and remains ready but **not integrated**.

If native `Array.findMaxima()` fails on a representative real plate after one sensible ROI reposition/retry:
1. keep the current manual first/last ROI interaction;
2. keep native wide-line profile extraction;
3. test BAR Find Peaks as the replacement peak-selection step, using its mature minimum peak-distance filtering;
4. preserve full-grid QC and the immediate original four-point fallback.

Do not tune another custom detector first. Details are in `docs/development/BAR_FIND_PEAKS_FALLBACK.md`.

## Automated checks / environment limitation

`.github/workflows/python-glue-tests.yml` runs compileall and `python -m unittest discover -s tests -v` on pushes to `workflow-dev` and pull requests, installing Pillow explicitly.

This ChatGPT execution environment cannot obtain a local checkout because outbound DNS for `github.com` is unavailable, so do **not** claim a local whole-suite pass. The available GitHub combined-status endpoint returns no direct-push contexts and the exposed workflow-run helper is not sufficient for branch push runs; do not infer a CI result from that absence.

## Pending manual validation — not a stop condition

The remaining important uncertainty is one representative real Fiji interaction:
- `waitForUser` rectangle behavior;
- native wide-line profile on real plate data;
- `Array.findMaxima()` peak selection;
- first/last interpolation;
- full-grid QC;
- crop handoff;
- optional AHK convenience.

If that succeeds, use a second same-sized plate only to verify the two suggestion-only geometry conveniences during normal operation. Do not broadly stress-test before using the workflow.

The config-driven original four-point route is immediately available for production continuity regardless.

## Highest-value next routes

1. Use `--prepare-only` with real configured metadata when available.
2. Perform the minimal representative desktop route in `MINIMAL_DESKTOP_VALIDATION.md`.
3. If native peaks are weak after one sensible retry, test BAR Find Peaks before any custom detection work.
4. Continue only deterministic setup/output/user-time improvements that can be proven without repeated manual testing.
5. Keep metadata inference conservative unless real data demonstrates a stable, verifiable pattern.
