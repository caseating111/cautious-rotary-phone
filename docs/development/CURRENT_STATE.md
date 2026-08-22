# Current state

## Durable line
`workflow-dev` is the only active development line. Routine work goes directly here; do not create side branches for ordinary fixes/features/tests/docs.

Current repository branches are `main`, `workflow-dev` and `alpha-pre-release`. `alpha-pre-release` is a **diverged obsolete release snapshot**, not an active development line: an explicit 2026-08-21 compare found four alpha-only commits (archival release notes plus older/smaller batch/preflight/controller-test implementations) and 98 workflow-dev-only commits. Do not merge/cherry-pick its old runtime/test changes merely because Git reports unique commits. See `docs/development/BRANCH_AUDIT.md`.

Binding rules: root `AGENTS.md` and `docs/development/IMPLEMENTATION_DECISION_POLICY.md`. Optimize total user time-to-reliable-result, reuse mature tools first, preserve source pixels/manual alignment authority, prove small routes, and stop patch/retest escalation early.

## Current target environment
The user's current required runtime environment is **Windows with Python 3.14**. Their normal Python installation and Anaconda environment are both Python 3.14. Treat Windows + Python 3.14 as the authoritative compatibility/CI target for current development and release validation. Linux compatibility and Python 3.11 compatibility are not current requirements and should not delay routine implementation or desktop debugging. Preserve broader compatibility when it comes essentially for free, but do not spend user/development time maintaining or repeatedly validating it unless requirements change.

## Current alignment priority
The current desktop test route is the established four-point mathematical alignment, not the experimental full-column detector. The four authoritative colony-centre references are R1C1, R1C(last), R5C1 and R5C(last). The complete 8 x N grid is interpolated mathematically from those four centres; there is no colony/peak detection in this route.

For the one-plate proof, the installed mature ROI 1-click toolset supplies the click ROI. The proof selects `Rotated Rectangle Click Tool` automatically and does not create its own 108x108 click box. The user's saved ROI 1-click dimensions therefore remain authoritative for click convenience. The fixed crop dimensions remain configurable and currently default to 130 x 546 for consistent outputs.

The proof uses a disposable boosted alignment-view duplicate, sampling the central 30% for temporary contrast so bright plate edges do not dominate. Source pixels remain unchanged. After the four clicks it shows a full mathematical grid QC with Accept/Retry before exporting crops from the original source image.

The controller no longer treats a still-open Fiji application process as proof that a one-plate macro is still active. A later proof may be launched while Fiji remains open; Fiji's own single-instance behavior is allowed to handle reuse. The AHK helper keeps recognised placement dialogs in the upper-left and the small main Fiji/ImageJ toolbar window in the upper-right, and supports Z to advance/accept plus X to Retry on either QC dialog.

The full-column native-profile route remains available as an experimental/alternate path, but do not invest more effort in it before the four-point route is proven on a representative real plate.

## Active workflow
- **Fiji/ImageJ:** current priority is four-point manual centre references -> mathematical grid -> QC -> crop export; full-column profile alignment remains optional/experimental.
- **ROI 1-click tools:** existing `Rotated Rectangle Click Tool` supplies the one-click ROI for four-point calibration; do not duplicate this plugin behavior in project code.
- **AHK v2:** Z/X dialog convenience and window placement only.
- **Pillow:** established matrix/label jobs plus focused composition adapters, always behind validated disposable staging.
- **Tkinter controller:** paths/config/orchestration only; focused output tools are launched as separate small GUIs.

No real experimental data belongs in the repo.

## Crop export
The preserved four-point route keeps the mature R1/R5 interpolation and fixed Top/Low crop semantics. Current default crop dimensions are 130 x 546 and remain configurable. Source pixels are not modified by crop export.

The alternate full-column helper `fiji/export_crops_from_alignment.ijm` verifies `last_alignment.txt` belongs to the current image (path+filename+dimensions when available), validates the complete grid and every intended Top/Low crop before the first write, then exports without modifying source pixels.

## Batch + fallback
`tools/run_full_column_batch_from_config.py` reuses the established production folder/CSV loop.

Current important behavior:
- `--prepare-only` validates CSVs, preflights, creates the pending-only metadata file, builds the configured macro, creates `crop_output` if needed and proves it writable before Fiji starts;
- the reused Fiji loop looks up raw `fileName` in the active metadata **before** `open(fullPath)`, so completed/non-pending plates are not loaded during resumed batches;
- its final summary separates `Not listed / not pending` from real post-metadata skips;
- the composed full-column macro neutralizes only the old pre-calibration 10/12-column guard, so full-column batches accept any validated `GridCols >= 2`;
- `--legacy` keeps the original four-point calibration/export lineage and original 10/12-only guard.

The current one-plate four-point proof further patches only the interaction layer so ROI 1-click provides the click ROI and the generated full-grid QC uses the clicked ROI's dimensions for display boxes. Do not broaden this until the desktop proof passes.

## Preflight / CSV / metadata safety
`tools/preflight_batch.py` is the source/crop readiness authority. It covers source mapping, grid availability, duplicate basenames/rows, crop freshness/readability/dimensions, output collisions, tree separation and plate-level resume state. Output collision checks include Windows case-insensitive path semantics.

`tools/validate_project_csvs.py` protects the actual Fiji/Pillow parsers rather than inventing a new format. Important rules include exact required header names, but column order is not semantically significant because parsing is header-based; surrounding header whitespace is rejected. Raw filename whitespace, ImageJ-unsafe metadata delimiters/line breaks, Windows filename safety, case collisions and legacy flattened Experiment_Set_Type prefix collisions are also blocked.

Metadata reconciliation remains conservative: existing `images.csv` is authoritative, new sources get blank metadata, drafts survive rescans, malformed review schemas are refused before overwrite, review refresh is atomic, candidate adoption is explicit/validated/backed up.

## Project layout / config
The controller can discover project CSVs from one selected CSV folder using case-insensitive filename matching where `grid.csv`, `images.csv` and `condition_order.csv` may be contained within longer filenames (for example `15.01.21 grid.csv`). Ambiguous matches fail closed.

Automatic project layout remains explicit/confirmed: one selected image root can be moved intact, same-filesystem only, into `<PREFIX>_<original>/Raw/<original>` with sibling `Crops`, `Matrices` and `Metadata` folders. Default prefix is dd.mm.yy but arbitrary safe text such as ATTEMPT1 is accepted. Existing organised Raw projects reconnect idempotently. No fallback giant copy is attempted, no existing destination is silently merged, and CSV paths inside a moved source tree are rebased while external CSV paths remain unchanged.

Global config remains under the user application folder so projects can reopen without reconfiguring the controller every launch. A more local optional preflight/report destination remains a future convenience, not a blocker.

## Launchers
`start_controller.cmd` prefers an already-active named conda environment, then `call conda run` for the named environment, then Anaconda/base, then Windows `py`, then PATH `python`. Using `call` is required for Windows conda batch/cmd entry points so fallback execution returns to the launcher.

`start_controller_no_anaconda.cmd` deliberately skips conda/Anaconda and uses Windows `py` then PATH `python`.

Do not add an installer/environment manager unless concrete desktop evidence requires it.

## Established Pillow outputs
`tools/run_existing_pillow_from_config.py` is the supported entry for `matrices`, `all-strains`, `all-strains-dedup` and `label-individual`.

Before an established Pillow child runs it validates project/source readiness, resolves exact current crop filenames, rejects missing/duplicate/case-colliding logical inputs, creates/probes `matrix_output`, stages only exact crops, normalizes orientation on staged copies, disables legacy in-place rotation, requires one new non-empty output folder and removes staging.

Real `crop_output` files are never rotated/rewritten. Standard multi-image jobs use representative preview-first orchestration from the controller; single-image jobs remain direct.

## Focused custom composition
Focused composition remains an opt-in thin adapter over the established matrix generator, not a replacement renderer. It preserves authoritative CSVs, stages only exact current crops, supports group/column/condition/state selection, preview, raw versus presentation-normalized output, recipe reopening with exact availability validation, processing logs, and explicit user-selected WT/control Experiment/Set for the mature deduplicated output.

Presentation normalization acts only on disposable staged copies. Archived Fiji display ranges are rejected when stale relative to current source images when `image_root` is configured. Successful builds verify all expected output matrices before remembering selections or recording success.

Do not evolve this into a freeform figure editor.

## Visibility
Routine visibility changes must remain non-destructive. The current four-point proof uses only a disposable alignment duplicate for its temporary central-sample boost. The separate global visibility route remains available for presentation consistency and derives one display range from robust background/high-percentile logic while preserving source pixels.

## Quantitative measurement direction
Do not implement a large custom scoring system yet. The desired future output should preserve multiple views rather than silently choosing one:
- raw measurement from original grayscale pixels;
- plate-background-corrected / normalized measurement suitable for within-plate WT comparisons;
- optionally a clearly labelled measurement from the same visual-adjusted representation used for human inspection.

Visual transforms must be recorded explicitly. Linear display transforms after background correction can be ratio-safe; hard thresholds, clipping, gamma and other nonlinear operations are not automatically equivalent to raw measurements.

The calculated mathematical grid can provide measurement regions directly; ROI Manager population is not inherently required. Jay Unruh/Stowers `plate analysis jru v1` remains a mature candidate worth testing before custom scoring, but its upstream batch plugin contains a known avg/sem write bug and must not be adopted unchanged.

## Pending minimal desktop validation
Use one representative real plate for the current four-point proof:
1. launch `Run one-plate 4-point proof (choose plate)`;
2. confirm the Fiji toolbar remains visible upper-right and the placement dialogs appear upper-left;
3. confirm `Rotated Rectangle Click Tool` is selected automatically;
4. click R1C1, R1C(last), R5C1 and R5C(last), using the existing ROI 1-click interaction;
5. inspect the full mathematical grid QC and Accept or Retry once;
6. verify expected crops are actually written and correctly positioned.

If that succeeds, run one second same-sized plate. Only then propagate any remaining interaction cleanup to the full four-point batch route. Do not return to detector tuning first.

## Highest-value next work
1. Complete the one-plate four-point desktop proof above.
2. If successful, make the full four-point batch interaction match the proven one-plate ROI 1-click behavior exactly.
3. Keep crop size fixed across a job by default; later optionally support one-time first-plate crop-size/grid-spacing calibration followed by locked dimensions and per-image position recalculation.
4. Later patch/adapt ROI 1-click locally rather than rewriting it, especially for optional draw-once preset calibration.
5. After alignment/cropping is reliable, test mature quantitative measurement routes and export raw + plate-normalized + clearly labelled visual-adjusted metrics.
6. Continue deterministic Pillow/controller improvements only where they remove real repetitive work without changing mature generators.
