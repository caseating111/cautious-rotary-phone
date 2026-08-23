# Current state

## Durable line
`workflow-C` is the active integration/product development line. Routine integrated work goes directly here; do not advance `workflow-dev` in parallel as a second production line.

`workflow-dev` is a pre-Codex development snapshot/line retained for history. `main` is the clean shared baseline. `geminimain` is the shared Gemini specification baseline, and isolated prototype implementation belongs on dedicated child/domain branches such as the existing `gemini-v10`. See `docs/development/MULTI_AGENT_CONTRACT.md` for current ownership and integration rules rather than relying on older branch lists.

Binding rules: root `AGENTS.md`, `docs/development/IMPLEMENTATION_DECISION_POLICY.md`, and the advisory cost boundary in `docs/development/AGENT_MODEL_ROUTING.md`. Optimize total user time-to-reliable-result, reuse mature tools first, preserve source pixels/manual alignment authority, prove small routes, avoid tunnel vision, and stop patch/retest escalation early.

## Current target environment
The current required runtime environment is **Windows with Python 3.14**. The normal Python installation and Anaconda environment are both Python 3.14. Treat Windows + Python 3.14 as the authoritative compatibility/CI target for current development and release validation. Linux compatibility and Python 3.11 compatibility are not current requirements and must not delay routine implementation or desktop debugging. Preserve broader compatibility when it comes essentially for free, but do not spend development/user time maintaining or repeatedly validating it unless requirements change.

## Current alignment priority
The established production-facing alignment route is the four-point mathematical alignment, not the experimental full-column detector. The four authoritative colony-centre references are R1C1, R1C(last), R5C1 and R5C(last) for the current basic CSV layouts. The complete 8 x N grid is interpolated mathematically from those four centres; there is no colony/peak detection in this route.

The four-click -> grid -> Accept -> export -> DONE/reset flow has now worked manually on multiple real images across two experiment folders. The four-click interaction itself is no longer the main blocker. Preserve it while changing only the surrounding Fiji ownership/control architecture when needed.

For the current route, the mature ROI 1-click toolset supplies the click ROI. The workflow uses the plugin's custom **Rotated Rectangle Click Tool**, not ImageJ's built-in rotated-rectangle tool, and must not create its own 108x108 click box. Saved ROI 1-click dimensions remain authoritative for click convenience. The local ROI 1-click patch restores saved rectangle/shared click preferences on fresh Fiji sessions and optional workflow presets may override only width/height/angle.

The temporary alignment view is a disposable duplicate. **There is no central sampling ROI anymore.** The current visibility aid applies CLAHE to the **whole disposable image twice**, using block size approximately `3.3 * max(rect.width, rect.height)`, histogram bins 256 and maximum slope 1000. Source pixels remain unchanged and crops are exported from the original source image.

The four-point generator now emits that ROI 1-click/CLAHE/rotated-QC interaction directly. The former second-stage string-replacement adapter and its dead `Enhance Contrast` intermediate block have been removed.

After the four clicks, QC uses the same mathematical plate vectors as the grid: both centres and the displayed grid boxes/lines rotate or skew with the clicked plate geometry. Axis-aligned QC boxes at rotated centres are not acceptable.

The old full-column detector/route is superseded for normal user-facing operation. Preserve useful historical code/evidence in retired/legacy areas where appropriate, but do not expose or reinvest in that route unless new evidence or an explicit task justifies it.

## Fiji ownership/control endpoint
The actual Fiji main-window title observed on the user's desktop is `(Fiji Is Just) ImageJ`.

The unresolved endpoint is **one reliable interactive Fiji session controlled/orchestrated from the Python workflow**, retaining the normal Fiji GUI and existing IJ1/plugin/manual interaction while avoiding duplicate Fiji/ImageJ windows, delayed launcher state, or fragile custom process attachment.

The user has repeatedly observed that running while Fiji is already open can still create a separate regular ImageJ/Fiji-like instance. Earlier custom existing-instance routes—including indirect window inference, legacy single-instance/socket/direct `ij.ImageJ` behavior, and the later RMI bridge—did not reliably satisfy the real endpoint. Direct `ij.ImageJ` is ruled out for production because it created the wrong separate GUI; the RMI route failed against the user's real open Fiji instance.

**Architecture reset is required before another launcher/IPC repair.** Do not add another RMI/socket/legacy-launcher fallback merely because those mechanisms already exist. Read `docs/research/fiji-four-point-runtime.md`, research/prove the current supported architecture, and preserve the working four-click logic around it.

Current bounded candidates to prove include modern Fiji/Jaunch behavior, PyImageJ with Python as host in interactive GUI mode, Fiji/Jaunch Python mode, direct modern Fiji script/command entry points, and Appose only where its separate-worker model is actually advantageous. These are candidates, not preselected answers.

The Fiji toolbar should retain its native/default useful dimensions. Window-management code may restore it onscreen and position it upper-right, but should not impose arbitrary size clamping that hides tools.

## AHK v2
**Hard runtime contract: AutoHotkey v2 only. AutoHotkey v1 compatibility is not required or desired.** Every repository AHK helper must use valid v2 syntax and must run under an AutoHotkey v2 executable. Do not copy v1 syntax, do not write v1/v2 hybrid code, and do not spend time preserving v1 behavior.

Keep the helper thin: Z advances/accepts recognized alignment dialogs, X selects Retry on either `Alignment QC` or `Full-grid QC`, Esc exits, placement dialogs go upper-left, and the visible Fiji toolbar is positioned upper-right. A bounded three-second catch-up scan handles delayed Java dialog titles. The same helper hides and lowers the Jaunch `Launching Fiji...` status window as a display workaround; this does not establish reliable Fiji ownership/control.

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

Source pixels are not modified by crop export.

Accepted grid coordinates are a durable reusable project asset rather than merely an immediate crop-export intermediate. Future processed-crop export, visibility, annotation and composition should consume saved geometry where their true prerequisites are satisfied instead of forcing repeated alignment.

## Batch + fallback
Current production work should preserve the proven four-point path and avoid reviving superseded detector/fallback UI routes merely because historical scripts remain in the repository.

Where legacy batch scripts remain, treat them as compatibility/history unless `CURRENT_STATE`, the controller, or an explicit task identifies them as active. Do not broaden an obsolete route while the supported four-point path and Fiji ownership endpoint are the actual priorities.

## Preflight / CSV / metadata safety
`tools/preflight_batch.py` remains the source/crop readiness authority: source mapping, grid availability, duplicate basenames/rows, crop freshness/readability/dimensions, output collisions, tree separation and plate-level resume state. Windows case-insensitive collisions are protected.

`tools/validate_project_csvs.py` validates the real Fiji/Pillow contracts. Header names are exact but column order is header-based, so `condition_order.csv` may place `Type` and `Order` in either column order if headers are correct. Surrounding header/Filename whitespace and unsafe metadata/collision cases are rejected.

Metadata reconciliation remains conservative: existing `images.csv` is authoritative, new sources are not guessed, drafts survive rescans, malformed review schemas are refused before overwrite, review refresh is atomic, and candidate adoption is explicit/validated/backed up.

The current basic CSV path is intentionally simpler and does not need V10 annotation-set/profile/Set semantics retrofitted into it. V10 is a separate richer metadata integration path being prototyped through shared contracts.

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

## Current validation gate
The four-point geometry/crop interaction has already passed representative manual use across multiple images/folders. Do not ask the user to repeat that entire validation merely because the Fiji ownership/control layer changes.

The next smallest discriminating proof is image-blind/synthetic and architecture-focused:
1. use the user's installed/current Fiji through one current supported candidate architecture;
2. show one real interactive Fiji GUI;
3. retain IJ1 legacy/plugin access needed by the existing route;
4. support a harmless synthetic/manual GUI interaction or macro marker;
5. confirm one GUI/JVM and no duplicate regular ImageJ/Fiji instance;
6. only after that succeeds, adapt the proven production four-click launch/control boundary and request one bounded desktop validation.

Follow the mandatory pre-next-attempt checkpoint and prior route history in `docs/research/fiji-four-point-runtime.md`. Do not spend another long session repairing the same launcher assumption.

## Highest-value next work
1. Prove the modern supported Fiji/Python ownership/control boundary with the smallest synthetic/manual interaction proof, without rewriting production geometry.
2. If one route succeeds, remove/bypass obsolete launcher/RMI/socket glue where it is no longer needed and integrate the smallest working boundary.
3. Run one bounded manual validation confirming one Fiji GUI plus the already-proven four-click interaction.
4. Keep grid coordinates durable/reusable and continue separating registration from later export/annotation/visibility work.
5. Consume V10/prototype work only through `MULTI_AGENT_CONTRACT.md`, `PROTOTYPE_HANDOFF_STANDARD.md`, and `contracts/`, after the prototype is `READY FOR INTEGRATION` rather than merely `PROOF PASSED`.
6. Later add the planned independent preprocessing/annotation/visibility applets and mature quantitative routes without blocking the working four-click path.
