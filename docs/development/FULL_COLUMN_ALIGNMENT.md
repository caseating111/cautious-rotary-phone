# Full-column alignment slice

Purpose: reduce four precision colony references to two manually positioned whole-column references without introducing bespoke colony detection.

Route:
1. User positions one tall rectangle around the full first column.
2. ImageJ `getProfile()` supplies the native top-to-bottom row-average profile.
3. ImageJ `Array.findMaxima()` supplies candidate row peaks; tolerance is reduced automatically only if too few peaks are found.
4. The same rectangle is moved to the last column and repeated.
5. Known `GridCols` interpolates columns; paired row centers interpolate row tilt across the plate.
6. Fiji draws the complete non-destructive grid overlay using the active per-culture ROI preset size.
7. User accepts or retries. Accepted geometry is written to `~/.cautious-rotary-phone/last_alignment.txt` for later crop/visibility integration.

`fiji/create_synthetic_grid_plate.ijm` provides an 8x10 tilted test image. `ahk/full_column_alignment_hotkeys.ah2` keeps Z=advance/accept and X=retry.

The existing four-point production crop macro remains unchanged as fallback until this route is desktop-validated.