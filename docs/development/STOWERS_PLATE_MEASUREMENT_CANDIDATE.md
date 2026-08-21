# Stowers yeast-plate measurement candidate

Status: **researched with an optional one-plate geometry adapter; not a production/controller stage**. Do not add batch/controller integration before the core full-column Fiji route works on one representative real plate and the plugin produces scientifically sensible output on one representative accepted plate.

## Why this is the first measurement candidate

Stowers/Jay Unruh `plate analysis jru v1` is an established Fiji/ImageJ plugin specifically documented for yeast growth-defect/rescue plates. Its source is public in `jayunruh/Jay_Plugins`; the source header is GPL v2, and published yeast studies have used the plugin to quantify colony pixel intensity and normalize growth to plate controls.

Relevant upstream sources:
- tutorial: `https://research.stowers.org/imagejplugins/plate_analysis.html`
- plugin repository: `https://github.com/jayunruh/Jay_Plugins`
- registered ImageJ command: `plate analysis jru v1`
- single-plate source: `plate_analysis_jru_v1.java`
- batch source: `batch_plate_analysis_jru_v1.java`

## Fit to the current workflow

The plugin uses a four-corner polygon, ordered upper-left -> upper-right -> lower-right -> lower-left, then bilinearly interpolates the full rectangular colony grid. The batch plugin can load a saved ROI and recurse through a directory.

Current accepted full-column geometry already supplies the required corner colony centres without another detection system:
- upper-left: `(leftX, leftRows[0])`
- upper-right: `(rightX, rightRows[0])`
- lower-right: `(rightX, rightRows[gridRows-1])`
- lower-left: `(leftX, leftRows[gridRows-1])`

For the current 8-row layouts, plugin `#_of_spots` is `8 * GridCols` and XY ratio is `GridCols / 8`: 10 columns -> 80 spots / 1.25, 12 columns -> 96 spots / 1.5.

The plugin measures circular spot regions and supports circular local-background subtraction. This is a better first quantitative-growth route than inventing a new pixel-scoring implementation.

ImageJ's documented `GenericDialog` behavior is macro-recordable and `run("command", "options")` can auto-fill plugin dialog values. That means a later validated adapter can remain thin rather than reimplementing the plugin.

## Important upstream batch bug

Do **not** treat the upstream `batch plate analysis jru v1` table output as production-ready without a patch/verification step.

In the current upstream `analyzeDirectory()` implementation:
- `_avg.xls` is written from `stats2[0]` as expected;
- `_sem.xls` is also written from `stats2[0]`, even though the plotting path correctly uses `stats2[1]` for errors.

So the file named `_sem.xls` appears to duplicate the averages rather than contain the computed error array. The single-plate plugin's on-screen `Plate Errors` table uses `stats2[1]` correctly.

If the single-plate proof succeeds and batch measurement is later worthwhile, prefer a tiny verified patch/wrapper around the mature plugin (changing the batch SEM write to the error array) rather than custom measurement code. Re-test that one patched handoff on representative data before controller exposure.

## Optional one-plate proof adapter

`fiji/stowers_measure_current_alignment.ijm` exists only to reduce proof-test clicking. It:
1. requires an accepted `last_alignment.txt`;
2. verifies saved directory/filename/dimensions belong to the current image;
3. derives the four required polygon vertices from the accepted first/last-column row geometry;
4. creates that polygon on the **unmodified current source image**;
5. displays the geometry-derived spot count and XY ratio;
6. launches the installed `plate analysis jru v1` command with its own native options dialog unchanged.

It deliberately does **not** script spot radius, replicate grouping, background mode or any other assay-specific measurement setting. `tests/test_stowers_measurement_adapter.py` also protects that it is not exposed as a controller production action yet.

## Minimal proof route if/when measurement is needed

1. Finish the existing minimal real-plate alignment validation first.
2. Install/enable the Stowers plugin using its published Fiji route.
3. On **one** representative accepted plate, run `fiji/stowers_measure_current_alignment.ijm` instead of manually redrawing the four corners.
4. Enter the displayed spot-count/XY-ratio values in the plugin dialog; choose radius/replicate/background settings from the actual analysis requirement rather than blindly accepting defaults.
5. Inspect the plugin's ROI placement/table against visible colonies and compare a few obvious strong/weak/control colonies.
6. Only if that output is sensible, record the proven plugin options and consider a thin macro/controller adapter.
7. If batch output is then needed, patch/verify the upstream `_sem.xls` write before using the batch plugin. Do not reimplement its measurement algorithm.

## Stop-loss / non-goals

- Do not replace current manual first/last alignment with this plugin; it is a downstream measurement candidate.
- Do not assume its intensity metric is automatically the correct biological score for every assay. Control normalization/replicate handling must follow the actual experimental analysis requirement.
- Do not build custom segmentation/scoring before testing this mature route (or another clearly better established tool).
- Do not expose the upstream batch plugin unchanged while its SEM table write is suspect.
- If the plugin requires repeated compatibility surgery on the current Fiji/image type, abandon it rather than entering a patch/retest cycle.
- Keep quantitative measurement on unmodified source pixels, not visibility-enhanced or annotated outputs.
