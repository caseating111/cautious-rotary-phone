# Alpha pre-release 2

This snapshot packages the current `workflow-dev` workflow for practical desktop testing. It is a pre-release, not a claim that every interactive Fiji/Windows path has been proven on the target machine.

## What is included

- Extended Tkinter controller as the normal controller surface.
- Windows launchers with robust Python fallbacks:
  - `start_controller.cmd`: active named conda environment -> named conda environment -> Anaconda `base` -> Windows `py` -> PATH `python`.
  - `start_controller.cmd`: unified Miniforge-first controller launcher with compatibility fallbacks only when Miniforge is unavailable.
  - `start_custom_matrix.cmd`: the same fallback principle for focused composition.
- Automatic project layout from one selected Image root:
  - editable prefix, defaulting to `dd.mm.yy`;
  - `<PREFIX>_<source-name>/Raw/<source-name>` plus `Crops`, `Matrices`, and `Metadata`;
  - same-filesystem directory move/rename rather than image copying or re-encoding;
  - destination preview/confirmation before a move;
  - refusal to merge into an existing conflicting destination;
  - reconnection of already-organised Raw projects;
  - configured CSV paths inside the moved source tree are rebased, while external CSV paths remain unchanged;
  - rename failure does not fall back to a giant copy.
- Existing CSV validation, conservative metadata reconciliation, batch preflight, pending-only resume behavior, and source/output/collision/freshness guards.
- Preserved four-point Fiji route as the immediate production fallback for its established 10/12-column layouts.
- Full-column first/last-column alignment route with whole-column profiles, interpolated grid, full-grid QC, explicit Accept/Retry, previous-geometry starting assists, and `GridCols >= 2` support.
- Global display-only visibility and archived display ranges; source pixels remain unchanged.
- Established Pillow matrix/label jobs behind exact-current disposable crop staging; real crops are not rotated or rewritten.
- Preview-first standard multi-output Pillow jobs.
- Focused/custom composition using the established Pillow renderer rather than a replacement renderer:
  - Experiment/Set, strain-column, condition and Top/Low selection;
  - representative preview;
  - raw or presentation-normalized output;
  - selected-crop availability and source-plate rerun reporting;
  - exact saved-selection/recipe restore checks;
  - human-readable Processing Logs plus machine JSON recipes;
  - last successful selection restoration.
- Explicit user-selectable WT/control Experiment/Set for deduplicated outputs, remembered only after successful complete Top+Low output.
- One-plate full-column proof launcher that isolates exactly one pending source without truncating the normal pending batch.
- Optional Stowers measurement proof remains present as a non-production candidate only.

## Validation status

A previous validation-only PR ran the then-current Python suite successfully on Python 3.11 and 3.14. The current direct-push tip contains additional launcher/project-layout changes and no fresh full-suite workflow result is visible through the connected GitHub interface, so this snapshot does **not** claim a new complete CI pass for the exact release tip.

Static/contract and synthetic tests cover the new project layout, launcher behavior, focused composition, preview, crop inventory, presentation normalization, recipes/logs, control-source selection, and one-plate preparation routes.

## Desktop validation still required

Three practical checks remain deliberately small:

1. **Windows launch smoke test**: confirm `start_controller.cmd` launches after the Anaconda installation. If it does not, capture the concrete console error. the launcher reports the original failure without switching Python runtimes.
2. **Project-layout smoke test**: use a disposable/small representative source folder, confirm the shown destination, and verify it moves intact into `Raw` while output paths are configured automatically. Do not use a large irreplaceable tree as the first desktop test.
3. **One representative real Fiji plate** through the full-column route: first column, last column, full-grid QC, crop handoff; allow at most one sensible retry. If native peak selection is poor after that, use the preserved four-point route and evaluate mature BAR Find Peaks rather than entering repeated custom-detector patch cycles.

If the first full-column plate succeeds, one same-sized second plate is sufficient to check the previous-geometry starting assists during normal use.

## Known limitations / intentionally deferred work

- Full-column real-plate Fiji interaction is still unproven on the target desktop; the four-point fallback remains the reliability route until that check succeeds.
- Project-layout folder movement is new and still awaiting its first desktop smoke test.
- The latest launcher changes are awaiting the user's post-fix Windows result.
- Quantitative Stowers batch measurement is not production-ready; the upstream batch plugin has a known avg/SEM export defect and must not be adopted unchanged.
- V10.2 workbook integration remains deliberately deferred until the desired human workflow is settled.
- No generic freeform figure editor is included; focused composition stays thin glue around the established renderer.

## First use

1. Try `start_controller.cmd`. If it fails, report the console output; it will not switch runtimes after a controller error.
2. Select an Image root. Review the proposed project destination before accepting the move.
3. Confirm or select the project CSVs, then run CSV validation and Batch preflight.
4. Use standard/focused Pillow outputs as needed from validated current crops.
5. For Fiji alignment, use the one-plate full-column proof for the first representative test; keep the 4-point fallback available.

Original source image pixels remain authoritative and are not modified by routine project organisation, alignment, display normalization or Pillow composition.
