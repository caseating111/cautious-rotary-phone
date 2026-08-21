# Aligned crop helper

`fiji/export_crops_from_alignment.ijm` is a small callable adapter between accepted full-column geometry and the existing crop/export semantics.

It validates that `last_alignment.txt` belongs to the current image, reads the matching experiment/set rows from `grid.csv`, and exports the established `Top` and `Low` PNG crops using the same default crop size (`130 x 546`) and naming pattern as the existing production macro.

Top is centered between fitted rows 2/3; Low between fitted rows 6/7, matching the old row-2.5/row-6.5 convention directly from the 8-row fit.

It is intended to be called by the existing batch macro with ImageJ `runMacro(..., args)` rather than becoming a second batch system.