# Stowers yeast-plate measurement candidate

Status: **researched, not integrated**. Do not add installation/controller code before the core full-column Fiji route works on one representative real plate and there is a concrete need for quantitative colony-growth output.

## Why this is the first measurement candidate

Stowers/Jay Unruh `plate analysis jru v1` is an established Fiji/ImageJ plugin specifically documented for yeast growth-defect/rescue plates. Its source is public in `jayunruh/Jay_Plugins`, and published yeast studies have used it to quantify colony pixel intensity and normalize growth to plate controls.

The Stowers Fiji update site remains the preferred installation route. Check the current Stowers licensing/academic-use terms before deployment.

Relevant upstream sources:
- tutorial: `https://research.stowers.org/imagejplugins/plate_analysis.html`
- plugin repository: `https://github.com/jayunruh/Jay_Plugins`
- single-plate source: `plate_analysis_jru_v1.java`
- batch source: `batch_plate_analysis_jru_v1.java`

## Fit to the current workflow

The plugin uses a four-corner polygon, ordered upper-left -> upper-right -> lower-right -> lower-left, then bilinearly interpolates the full rectangular colony grid. The batch plugin can load a saved ROI, recurse through a directory and write per-image average/error tables.

Current accepted full-column geometry already supplies the required corner colony centres without another detection system:
- upper-left: `(leftX, leftRows[0])`
- upper-right: `(rightX, rightRows[0])`
- lower-right: `(rightX, rightRows[gridRows-1])`
- lower-left: `(leftX, leftRows[gridRows-1])`

For the current 8-row layouts, plugin `#_of_spots` would be `8 * GridCols` and XY ratio would be `GridCols / 8` (for example 10 columns -> 1.25; 12 columns -> 1.5).

The plugin measures circular spot regions and can apply circular local-background subtraction. This is a better first quantitative-growth route than inventing a new pixel-scoring implementation.

## Minimal proof route if/when measurement is needed

1. Finish the existing minimal real-plate alignment validation first.
2. Install/enable the Stowers Fiji plugin using its published update-site route.
3. On **one** representative accepted plate, construct the four-corner polygon from `last_alignment.txt` rather than manually redrawing geometry.
4. Run `plate analysis jru v1` once with a conservative spot radius and circular background enabled.
5. Inspect the plugin's ROI placement/table against the visible colonies and compare a few obvious strong/weak/control colonies.
6. Only if that output is sensible, add a thin macro/controller adapter and consider its batch plugin. Do not reimplement its measurement algorithm.

## Stop-loss / non-goals

- Do not replace current manual first/last alignment with this plugin; it is a downstream measurement candidate.
- Do not assume its intensity metric is automatically the correct biological score for every stress assay. Control normalization/replicate handling must follow the actual experimental analysis requirement.
- Do not build custom segmentation/scoring before testing this mature route (or another clearly better established tool).
- If the plugin requires repeated compatibility surgery on the current Fiji/image type, abandon it rather than entering a patch/retest cycle.
- Keep quantitative measurement on unmodified source pixels, not visibility-enhanced or annotated outputs.
