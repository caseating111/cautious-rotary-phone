# Full-column alignment slice

Purpose: reduce four precision colony references to two manually positioned whole-column references without introducing bespoke colony detection.

Route:
1. User positions one tall rectangle around the full first column. In batch mode, Experiment/Set/Type context appears in this already-required first-column dialog rather than in a separate `Next plate` confirmation.
2. If a previous accepted whole-column reference exists for an image with the same dimensions, that rectangle is pre-positioned only as a starting suggestion. The user must still move/resize it for the current plate; it is never accepted automatically.
3. The macro temporarily converts the rectangle to a vertical straight-line ROI with the same width. ImageJ `getProfile()` uses native wide-line profile machinery (`Line.getPixels()` / `Straightener`) to average across the column. The rectangle is immediately restored; the explicit macro pixel average remains fallback only.
4. ImageJ `Array.findMaxima()` supplies candidate row peaks; tolerance is reduced automatically only if too few peaks are found.
5. The same rectangle is moved manually to the last column and repeated.
6. Known `GridCols` interpolates columns; paired row centers interpolate row tilt across the plate.
7. Fiji draws the complete non-destructive grid overlay using the active per-culture ROI preset size.
8. User accepts or retries. Accepted geometry, source identity and the first-column reference rectangle are written to `~/.cautious-rotary-phone/last_alignment.txt`.

Manual first/last placement remains authoritative. Previous-reference seeding is only a convenience to reduce repeated resizing/positioning on similarly framed images, and full-grid QC remains mandatory.

`fiji/create_synthetic_grid_plate.ijm` provides an 8x10 tilted test image. `ahk/full_column_alignment_hotkeys.ah2` keeps Z=advance/accept and X=retry; it no longer watches for the removed `Next plate` dialog.

The existing four-point production crop macro remains unchanged as fallback until this route is desktop-validated.
