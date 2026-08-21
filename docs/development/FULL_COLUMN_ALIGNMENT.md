# Full-column alignment slice

Purpose: reduce four precision colony references to two manually positioned whole-column references without introducing bespoke colony detection.

Route:
1. User positions one tall rectangle around the full first column. In batch mode, Experiment/Set/Type context appears in this already-required first-column dialog rather than in a separate `Next plate` confirmation.
2. If a previous accepted whole-column reference exists for an image with the same dimensions, that rectangle is pre-positioned only as a starting suggestion. The user must still move/resize it for the current first column; it is never accepted automatically.
3. The macro temporarily converts the rectangle to a vertical straight-line ROI with the same width. ImageJ `getProfile()` uses native wide-line profile machinery (`Line.getPixels()` / `Straightener`) to average across the column. The rectangle is immediately restored; the explicit macro pixel average remains fallback only.
4. ImageJ `Array.findMaxima()` supplies candidate row peaks; tolerance is reduced automatically only if too few peaks are found.
5. If the previous accepted alignment came from a same-sized image, its first-to-last horizontal span is applied to the **current manually confirmed first-column rectangle** to move that same rectangle near the last column. This is only a starting suggestion; bounds are checked and the user still fine-tunes/positions the last column and explicitly confirms it.
6. The last-column profile is measured from that manually confirmed current ROI.
7. Known `GridCols` interpolates columns; paired row centers interpolate row tilt across the plate.
8. Fiji draws the complete non-destructive grid overlay using the active per-culture ROI preset size.
9. User accepts or retries. Accepted geometry, source identity and the first-column reference rectangle are written to `~/.cautious-rotary-phone/last_alignment.txt`.

Manual first/last placement remains authoritative. Previous-reference and previous-span seeding are only conveniences to reduce repeated resizing and long-distance dragging on similarly framed images; neither can bypass either manual placement or full-grid QC.

`fiji/create_synthetic_grid_plate.ijm` provides an 8x10 tilted test image. `ahk/full_column_alignment_hotkeys.ah2` keeps Z=advance/accept and X=retry; placement dialogs are moved once to a predictable corner by the same lightweight shell-hook pattern used by the original helper.

The existing four-point production crop macro remains unchanged as fallback until this route is desktop-validated.
