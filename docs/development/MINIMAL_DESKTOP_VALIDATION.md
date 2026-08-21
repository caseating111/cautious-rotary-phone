# Minimal desktop validation

Purpose: validate the remaining interactive Fiji uncertainty with the smallest useful amount of user testing. Do **not** expand into broad manual regression testing.

## Before Fiji interaction
1. Configure real paths in the controller.
2. Run **Batch preflight** or `tools/run_full_column_batch_from_config.py --prepare-only`.
3. Resolve only blocking preflight issues. The noninteractive validator/preflight/macro-composition and Pillow routes already have synthetic regression coverage; do not manually re-test them exhaustively.

## One representative plate
Use one ordinary representative plate first, not a deliberately difficult edge case.

1. Start **Run full-column batch**.
2. Confirm the first-column dialog shows the correct Experiment/Set/Type context.
3. Position the whole-column rectangle on the first column; press Z/OK.
4. Move the same rectangle to the last column; press Z/OK.
5. Inspect the complete proposed grid overlay.
6. If the overlay is sensible, accept once. If it is clearly wrong, retry once with a better whole-column placement.
7. Confirm the expected Top/Low crops are written and source pixels remain unchanged.

### What this single test is actually validating
- Fiji `waitForUser` interaction with the whole-column rectangle;
- native wide-line `getProfile()` behavior on a real plate;
- `Array.findMaxima()` row selection on representative real colony data;
- first/last interpolation and full-grid QC overlay;
- accepted-alignment handoff into crop export;
- AHK Z/X convenience behavior if the helper is used.

## Second image only if the first succeeds
Use one same-sized next plate to check that the previous first-column rectangle is offered only as a movable starting suggestion. Reposition it manually and keep normal QC. Do not test automatic acceptance because none exists.

## Stop-loss
- If the representative plate works, do not spend time stress-testing many plates before using the workflow normally.
- If peak selection fails once on an otherwise reasonable whole-column ROI, try one sensible reposition/retry.
- If native peak selection is still clearly unreliable, stop patching `Array.findMaxima()` and evaluate the already-identified mature BAR **Find Peaks** fallback before any custom detector.
- The original four-point production macro remains the fallback throughout.
