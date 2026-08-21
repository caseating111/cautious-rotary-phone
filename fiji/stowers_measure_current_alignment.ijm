// Optional one-plate proof adapter for Jay Unruh/Stowers "plate analysis jru v1".
// Reuses the accepted full-column geometry only to create the plugin's required
// four-corner polygon. The mature plugin remains responsible for measurement.
// This macro does not modify source pixels and deliberately does not guess
// assay-specific spot radius, replicate grouping, or background settings.

if (nImages() == 0)
    exit("Open an already aligned plate image first.");

alignmentFile = getDirectory("home") + ".cautious-rotary-phone" + File.separator + "last_alignment.txt";
if (!File.exists(alignmentFile))
    exit("No accepted full-column alignment found. Align this plate first.");

sourceTitle = getTitle();
sourceWidth = getWidth();
sourceHeight = getHeight();
if (!alignmentMatchesCurrentImage(alignmentFile, sourceTitle, sourceWidth, sourceHeight))
    exit("Saved alignment does not belong to the current image. Re-align this plate before measurement.");

gridCols = parseInt(readValue(alignmentFile, "grid_cols", "-1"));
gridRows = parseInt(readValue(alignmentFile, "grid_rows", "-1"));
leftX = parseFloat(readValue(alignmentFile, "left_x", "-1"));
rightX = parseFloat(readValue(alignmentFile, "right_x", "-1"));
leftTopY = parseFloat(readValue(alignmentFile, "row_1_left_y", "-1"));
rightTopY = parseFloat(readValue(alignmentFile, "row_1_right_y", "-1"));
leftBottomY = parseFloat(readValue(alignmentFile, "row_" + gridRows + "_left_y", "-1"));
rightBottomY = parseFloat(readValue(alignmentFile, "row_" + gridRows + "_right_y", "-1"));

if (gridCols < 2 || gridRows < 2)
    exit("Accepted alignment has invalid grid dimensions.");
if (!pointInside(leftX, leftTopY, sourceWidth, sourceHeight) ||
    !pointInside(rightX, rightTopY, sourceWidth, sourceHeight) ||
    !pointInside(rightX, rightBottomY, sourceWidth, sourceHeight) ||
    !pointInside(leftX, leftBottomY, sourceWidth, sourceHeight))
    exit("Accepted corner geometry falls outside the current image. Re-align before measurement.");

// Stowers plugin source expects vertices in UL, UR, LR, LL order.
makePolygon(
    leftX, leftTopY,
    rightX, rightTopY,
    rightX, rightBottomY,
    leftX, leftBottomY
);

spots = gridCols * gridRows;
xyRatio = gridCols / gridRows;
showMessage(
    "Stowers one-plate measurement proof",
    "Accepted alignment has been converted to the four-corner polygon expected by plate analysis jru v1.\n\n" +
    "Use these geometry values in the plugin dialog:\n" +
    "# of spots: " + spots + "\n" +
    "XY ratio: " + xyRatio + "\n\n" +
    "Spot radius, replicate grouping and background settings are assay-specific. Do not accept those defaults blindly.\n\n" +
    "This proof uses the current unmodified source image."
);

// GenericDialog plugins are macro-recordable, but keep this proof interactive
// until one representative plate confirms scientifically sensible settings.
run("plate analysis jru v1");

function pointInside(x, y, width, height) {
    return x >= 0 && y >= 0 && x < width && y < height;
}

function alignmentMatchesCurrentImage(path, title, width, height) {
    savedDirectory = readValue(path, "source_directory", "");
    savedFilename = readValue(path, "source_filename", "");
    dimensionsMatch = parseInt(readValue(path, "source_width", "-1")) == width &&
                      parseInt(readValue(path, "source_height", "-1")) == height;

    if (savedDirectory != "" && savedFilename != "")
        return dimensionsMatch && savedDirectory == getInfo("image.directory") && savedFilename == getInfo("image.filename");

    return dimensionsMatch && readValue(path, "source_title", "") == title;
}

function readValue(path, key, fallback) {
    text = File.openAsString(path);
    lines = split(text, "\n");
    prefix = key + "=";
    for (i = 0; i < lines.length; i++) {
        candidate = replace(lines[i], "\r", "");
        if (startsWith(candidate, prefix))
            return substring(candidate, lengthOf(prefix));
    }
    return fallback;
}
