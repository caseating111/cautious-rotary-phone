# Minimal desktop validation

Purpose: validate the remaining interactive Fiji uncertainty with the smallest useful amount of user testing. Do **not** expand into broad manual regression testing.

## Before Fiji interaction
1. Configure real paths in the controller.
2. Run **Batch preflight** or `tools/run_full_column_batch_from_config.py --prepare-only`.
3. Resolve only blocking preflight issues. The noninteractive validator/preflight/macro-composition and Pillow routes already have synthetic regression coverage; do not manually re-test them exhaustively.

## One representative plate
Use one ordinary representative plate first, not a deliberately difficult edge case.

Use **Run one-plate full-column proof (first pending image only)** in the extended controller instead of starting the normal full batch. This proof route first runs the same authoritative `--prepare-only` path, so the normal complete pending list and normal configured production macro are refreshed exactly as they would be for a real batch. It then copies only the first pending metadata row into a **separate** proof CSV, patches only a **separate** proof macro's `imagesFile` path, and launches that proof copy. The production pending list is not truncated/replaced by the one-row proof list, so a successful first plate cannot accidentally roll straight into plate two.

If the first pending image is not a sensible representative plate, the same thin helper supports an explicit exact filename from the command line:

`python tools/run_one_plate_validation.py --filename "plate-name.ext"`

Then:

1. Confirm the first-column dialog shows the correct Experiment/Set/Type context.
2. Position the whole-column rectangle on the first column; press Z/OK. If only a tiny correction is needed, use ImageJ's native arrow-key ROI nudge (Alt+arrow resizes a rectangle one pixel) instead of precision dragging.
3. Move the same rectangle to the last column; use the same native fine adjustment if useful, then press Z/OK.
4. Inspect the complete proposed grid overlay.
5. If the overlay is sensible, accept once. If it is clearly wrong, retry once with a better whole-column placement.
6. Visually confirm the source image itself was not altered. Do **not** manually inspect every expected crop one by one.
7. After Fiji finishes that plate, run **Batch preflight** once. The authoritative preflight should now classify that source as complete/not pending; if it does not, use the saved report to identify the exact missing/stale/incompatible crop rather than doing a manual file audit.

The native arrow-key behavior is only an operating convenience; it is not a separate validation requirement and the AHK helper does not forward or reinterpret those keys.

### What this single test is actually validating
- Fiji `waitForUser` interaction with the whole-column rectangle;
- native wide-line `getProfile()` behavior on a real plate;
- `Array.findMaxima()` row selection on representative real colony data;
- first/last interpolation and full-grid QC overlay;
- accepted-alignment handoff into crop export;
- AHK Z/X convenience behavior if the helper is used.

## Second image only if the first succeeds
Use one same-sized next plate for both previous-geometry conveniences at once. At that point use the normal batch route during real work, or run the one-plate proof against an explicit second filename if you specifically want to keep validation isolated.

1. Confirm the previous accepted first-column rectangle appears only as a movable starting suggestion. Reposition/resize it manually for the current first column and confirm it normally.
2. After first-column confirmation, confirm the **same current rectangle** is moved near the last column using the previous accepted first-to-last horizontal span. Fine-tune it manually and confirm it normally.
3. Keep the usual full-grid QC and explicit Accept/Retry step.

Neither suggestion is accepted automatically; the second-image check should not add any separate validation pass beyond the normal alignment interaction.

## Stop-loss / immediate fallback
- If the representative plate works, do not spend time stress-testing many plates before using the workflow normally.
- If peak selection fails once on an otherwise reasonable whole-column ROI, try one sensible reposition/retry.
- If native peak selection is still clearly unreliable, stop patching `Array.findMaxima()` and evaluate the already-identified mature BAR **Find Peaks** fallback before any custom detector.
- The original four-point production macro is directly available as **Run 4-point fallback** in the controller. It uses the same CSV validation, batch preflight, pending-image list, configured paths/crop dimensions and alignment hotkey helper, but its original four-point calibration/export block remains unchanged.
- The preserved four-point macro only supports its original 10- or 12-column grids; the adapter blocks unsupported widths before Fiji rather than letting the old macro skip them.
- Do not manually compare every output from both routes. Use the four-point route only when a plate/workset needs the known fallback or while the new route is being evaluated.
