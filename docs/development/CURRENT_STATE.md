# Current state

## Durable line
`workflow-dev` is the only active development line. Routine work goes directly here; do not create side branches for ordinary fixes/features/tests/docs.

Current repository branches are `main`, `workflow-dev` and `alpha-pre-release`. `alpha-pre-release` is a diverged release snapshot, not the active development line. Do not merge/cherry-pick its old runtime/test changes merely because Git reports unique commits. See `docs/development/BRANCH_AUDIT.md`.

Binding rules: root `AGENTS.md` and `docs/development/IMPLEMENTATION_DECISION_POLICY.md`. Optimize total user time-to-reliable-result, reuse mature tools first, preserve source pixels/manual alignment authority, prove small routes, and stop patch/retest escalation early.

## Current target environment
The current required runtime environment is **Windows with Python 3.14**. The normal Python installation and Anaconda environment are both Python 3.14. Treat Windows + Python 3.14 as the authoritative compatibility/CI target for current development and release validation. Linux compatibility and Python 3.11 compatibility are not current requirements and must not delay routine implementation or desktop debugging. Preserve broader compatibility when it comes essentially for free, but do not spend development/user time maintaining or repeatedly validating it unless requirements change.

## Current alignment priority
The active desktop test route is the established four-point mathematical alignment, not the experimental full-column detector. The four authoritative colony-centre references are R1C1, R1C(last), R5C1 and R5C(last). The complete 8 x N grid is interpolated mathematically from those four centres; there is no colony/peak detection in this route.

For the one-plate proof, the mature ROI 1-click toolset supplies the click ROI. The proof must use the plugin's custom **Rotated Rectangle Click Tool**, not ImageJ's built-in rotated-rectangle tool, and must not create its own 108x108 click box. Saved ROI 1-click dimensions remain authoritative for click convenience. The local ROI 1-click patch restores saved rectangle/shared click preferences on fresh Fiji sessions and optional workflow presets may override only width/height/angle.

The temporary alignment view is a disposable duplicate. **There is no central sampling ROI anymore.** The current visibility aid applies CLAHE to the **whole disposable image twice**, using block size approximately `3.3 * max(rect.width, rect.height)`, histogram bins 256 and maximum slope 1000. Source pixels remain unchanged and crops are exported from the original source image.

After the four clicks, QC uses the same mathematical plate vectors as the grid: both centres and the displayed grid boxes/lines rotate or skew with the clicked plate geometry. Axis-aligned QC boxes at rotated centres are not acceptable.

The full-column native-profile route remains available as an experimental/alternate path, but do not invest more effort in it before the four-point route is proven on representative real plates.

## Fiji reuse and UI state
A live Fiji process is not proof that a one-plate proof is still running. Other open Fiji images do not block a proof. The relevant duplicate guard is the exact selected proof-plate window.

The actual Fiji main-window title observed on the user's desktop is `(Fiji Is Just) ImageJ`; existing-instance detection must recognize it. The proof currently attempts Fiji/ImageJ's normal single-instance/Macro Runner handoff when Fiji is already open. This is still a desktop-validation point because the user's Fiji installation previously showed a stale ImageJ single-instance/RMI stub connection error.

The proof should explicitly use ImageJ/Fiji's own **Window -> Show All** behavior before interaction. ImageJ's `Show All`/`WindowOrganizer` brings windows to the front but does not reposition the main ImageJ frame, so a remembered off-screen/bad toolbar position can still make the main GUI appear missing. The AHK helper currently rescues this case by moving the already-created Fiji/ImageJ `SunAwtFrame` into the visible upper-right. AHK may assist with positioning, but the proof must not depend on AHK for basic creation/visibility of the Fiji GUI; keep a non-AHK visibility path working as well. The small main Fiji toolbar/interface should remain available in the upper-right so the ROI tool can be changed manually if automatic selection fails.

Fresh launches use `--no-splash`; the previously observed persistent central "Launching Fiji" splash should therefore remain gone, but this still needs desktop confirmation.

## AHK v2
**Hard runtime contract: AutoHotkey v2 only. AutoHotkey v1 compatibility is not required or desired.** Every repository AHK helper must use valid v2 syntax and must run under an AutoHotkey v2 executable. Do not copy v1 syntax, do not write v1/v2 hybrid code, and do not spend time preserving v1 behavior.

Keep the helper thin: Z advances/accepts recognized alignment dialogs, X selects Retry on either `Alignment QC` or `Full-grid QC`, Esc exits, placement dialogs go upper-left, and the visible Fiji toolbar is positioned upper-right.

Recent v2 mistakes that must not recur include using v1-style catch/try shorthand such as `catch title := ""`, using a one-line `try` before `else if`, and omitting `&` on `WinGetPos` output variables. Use explicit v2 `catch { ... }` blocks where assignment is needed. Dialog movement uses the normal shell-hook move plus one small delayed catch-up pass (~120 ms); do not reintroduce permanent polling unless concrete evidence requires it.

## Active workflow
- **Fiji/ImageJ:** four centre clicks -> mathematical 8 x N grid -> rotated/skewed full-grid QC -> crop export from original image.
- **ROI 1-click tools:** existing Rotated Rectangle Click Tool supplies the one-click ROI; project code does not duplicate it.
- **AHK v2:** hotkeys and predictable window placement only.
- **Pillow:** established matrix/label jobs plus focused composition adapters behind validated disposable staging.
- **Tkinter controller:** paths/config/orchestration only; do not absorb mature Fiji/Pillow/plugin behavior.

No real experimental data belongs in the repo.

## Crop export
The preserved four-point lineage keeps mature R1/R5 interpolation and fixed Top/Low crop semantics. Current default crop dimensions are 130 x 546 and remain configurable. Keep crop dimensions fixed across a job by default; do not derive a different crop size from small click differences on every plate. Future optional first-image calibration may establish a job-level size and then lock it.

Source pixels are not modified by crop export. The alternate full-column helper remains available and keeps its own alignment-identity validation.

## Batch + fallback
`tools/run_full_column_batch_from_config.py` reuses the established production folder/CSV loop.

Important behavior remains:
- `--prepare-only` validates CSVs, preflights, creates the pending-only metadata file, builds the configured macro, creates/probes `crop_output` before Fiji starts;
- pending metadata lookup happens before image open so completed/non-pending plates are not loaded on resume;
- final summary distinguishes not-pending images from real failures;
- full-column supports validated `GridCols >= 2` after neutralizing only the obsolete 10/12 guard in that composed route;
- preserved four-point fallback intentionally retains its original 10/12-column contract.

The one-plate proof currently adapts only the interaction/visibility/QC layer around the established four-point route. Do not broaden the full batch until the proof works on desktop; then make the full four-point batch interaction match the proven proof exactly.

## Preflight / CSV / metadata safety
`tools/preflight_batch.py` remains the source/crop readiness authority: source mapping, grid availability, duplicate basenames/rows, crop freshness/readability/dimensions, output collisions, tree separation and plate-level resume state. Windows case-insensitive collisions are protected.

`tools/validate_project_csvs.py` validates the real Fiji/Pillow contracts. Header names are exact but column order is header-based, so `condition_order.csv` may place `Type` and `Order` in either column order if headers are correct. Surrounding header/Filename whitespace and unsafe metadata/collision cases are rejected.

Metadata reconciliation remains conservative: existing `images.csv` is authoritative, new sources are not guessed, drafts survive rescans, malformed review schemas are refused before overwrite, review refresh is atomic, and candidate adoption is explicit/validated/backed up.

## Project layout / config
The controller can discover `grid.csv`, `images.csv` and `condition_order.csv` from one selected CSV folder using case-insensitive filename matching where the expected term may occur inside a longer filename, e.g. `15.01.21 grid.csv`. Ambiguous matches fail closed.

Automatic project layout remains explicit/confirmed: one selected image root can be moved intact, same-filesystem only, into `<PREFIX>_<original>/Raw/<original>` with sibling `Crops`, `Matrices` and `Metadata` folders. Default prefix is dd.mm.yy but arbitrary safe text such as ATTEMPT1 is accepted. Existing organised Raw projects reconnect idempotently. No giant copy fallback and no silent merge into an existing destination. CSV paths inside the moved tree are rebased; external CSV paths stay unchanged.

Global config remains useful and should stay available. A more local/project report destination, especially for preflight output, remains a future convenience rather than a blocker.

## Launchers
`start_controller.cmd` prefers an already-active named conda environment, then `call conda run` for the named environment, then Anaconda/base, then Windows `py`, then PATH `python`. `call` is required for Windows conda batch/cmd entry points so fallback execution returns to the launcher.

`start_controller_no_anaconda.cmd` deliberately skips conda/Anaconda and uses Windows `py` then PATH `python`.

Do not add an installer/environment manager unless concrete desktop evidence requires it.

## Established Pillow outputs
`tools/run_existing_pillow_from_config.py` is the supported entry for `matrices`, `all-strains`, `all-strains-dedup` and `label-individual`.

Before an established Pillow child runs it validates project/source readiness, resolves exact current crop filenames, rejects missing/duplicate/case-colliding inputs, creates/probes `matrix_output`, stages only exact crops, normalizes orientation on disposable copies, disables legacy in-place rotation, and requires actual new non-empty output. Real crop files are never rotated/rewritten by composition.

## Focused custom composition / recipes / WT control
Focused composition remains a thin adapter over the established matrix generator. It preserves authoritative CSVs, supports group/column/condition/state selection, preview, raw versus presentation-normalized output, exact recipe restoration, processing logs, and explicit user-selected WT/control Experiment/Set.

Old/saved selections that reference removed groups/columns/conditions must refuse explicitly rather than silently narrow. Presentation normalization acts only on staged copies and stale archived display ranges are rejected. Preferred WT/control is remembered only after a successful complete output; do not restore a biological default such as E2/A.

## Visibility and quantitative measurement direction
Routine visibility changes remain non-destructive. The current four-point alignment aid is whole-image CLAHE x2 on a disposable duplicate only. The separate global/presentation visibility route may continue to use robust plate/grid-derived display ranges without changing source pixels.

Do not implement a large custom scoring system yet. Future measurement should preserve multiple clearly labelled views:
- raw measurements from original grayscale pixels;
- plate-background-corrected / WT-normalized measurements for within-plate relative growth;
- optionally measurements from the same visual-adjusted representation used for inspection.

Background handling should be per plate. Nonlinear transforms such as thresholding, clipping, gamma and CLAHE are not automatically ratio-equivalent to raw data, so transformed measurements must remain explicitly labelled. The mathematical grid can provide measurement regions directly; ROI Manager population is not inherently required.

Jay Unruh/Stowers `plate analysis jru v1` remains a mature measurement candidate worth testing before custom scoring. Do not adopt its upstream batch plugin unchanged because the active source appears to write both avg and sem files from the averages array.

## Pending minimal desktop validation
Use one representative real plate for the current four-point proof and verify, in order:
1. an already-running `(Fiji Is Just) ImageJ` instance is recognized/reused rather than deliberately spawning another full Fiji UI;
2. the normal Fiji toolbar/interface becomes visible before the first placement dialog and is accessible upper-right;
3. the ROI 1-click Rotated Rectangle Click Tool, not ImageJ's built-in rotated rectangle, is active or can be selected manually;
4. the disposable alignment image receives CLAHE x2 across the **entire image**, with no central sampling rectangle;
5. click R1C1, R1C(last), R5C1 and R5C(last);
6. placement dialogs appear upper-left via immediate move plus one delayed catch-up;
7. full-grid QC follows plate rotation/skew, including the individual grid boxes;
8. Accept/Retry works; at most one sensible retry for this proof;
9. expected fixed-size crops are written from the original source and correctly positioned;
10. no persistent Fiji launch splash remains.

If that succeeds, run one second same-sized plate. Only then propagate the proven interaction to the full four-point batch. Do not return to detector tuning first.

## Highest-value next work
1. Complete the one-plate four-point desktop proof above.
2. If successful, make full four-point batch interaction match it exactly.
3. Keep crop size fixed across a job; later optionally support one-time first-image calibration followed by locked dimensions and per-image position recalculation.
4. Later add a small ROI 1-click convenience for draw-once size/preset calibration by adapting the existing plugin, not rewriting it.
5. After alignment/cropping is reliable, test mature quantitative routes and export raw + plate-normalized + clearly labelled visual-adjusted metrics.
6. Improve minor repetitive conveniences such as local/project preflight-report placement only after the core proof is stable.
