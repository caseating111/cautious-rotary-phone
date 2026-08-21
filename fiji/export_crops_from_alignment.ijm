// Export Top/Low strain crops from the current image using accepted full-column geometry.
// Thin adapter around the existing crop naming/dimensions; alignment remains in full_column_alignment.ijm.
// Argument format:
// grid_csv=C:/.../grid.csv;output_dir=C:/.../out;experiment=E1;set=0;type=YPDA;crop_w=130;crop_h=546

if (nImages() == 0)
    exit("Open and align an image first.");

arg = getArgument();
if (lengthOf(arg) == 0)
    exit("This helper expects macro arguments from a controller/batch macro.");

gridFile = argValue(arg, "grid_csv", "");
outDir = argValue(arg, "output_dir", "");
experiment = argValue(arg, "experiment", "");
setName = argValue(arg, "set", "");
typeName = argValue(arg, "type", "");
CROP_W = parseInt(argValue(arg, "crop_w", "130"));
CROP_H = parseInt(argValue(arg, "crop_h", "546"));

if (!File.exists(gridFile))
    exit("grid.csv not found: " + gridFile);
if (lengthOf(outDir) == 0 || lengthOf(experiment) == 0 || lengthOf(typeName) == 0)
    exit("Missing output_dir, experiment or type macro argument.");
if (CROP_W <= 0 || CROP_H <= 0)
    exit("Crop width and height must be positive.");
if (!endsWith(outDir, File.separator))
    outDir = outDir + File.separator;
if (!File.exists(outDir))
    File.makeDirectory(outDir);

alignmentFile = getDirectory("home") + ".cautious-rotary-phone" + File.separator + "last_alignment.txt";
if (!File.exists(alignmentFile))
    exit("No accepted alignment found.");

sourceTitle = getTitle();
sourceWidth = getWidth();
sourceHeight = getHeight();
if (!alignmentMatchesCurrentImage(alignmentFile, sourceTitle, sourceWidth, sourceHeight))
    exit("Saved alignment does not belong to the current image. Re-align before exporting crops.");

rows = parseInt(readValue(alignmentFile, "grid_rows", "-1"));
gridCols = parseInt(readValue(alignmentFile, "grid_cols", "-1"));
leftX = parseFloat(readValue(alignmentFile, "left_x", "-1"));
rightX = parseFloat(readValue(alignmentFile, "right_x", "-1"));
if (rows < 8 || gridCols < 2 || leftX < 0 || rightX < 0)
    exit("Alignment geometry is incomplete or does not contain 8 rows.");

// Existing crop workflow centers Top between rows 2/3 and Low between rows 6/7.
leftTopY = (parseFloat(readValue(alignmentFile, "row_2_left_y", "-1")) + parseFloat(readValue(alignmentFile, "row_3_left_y", "-1"))) / 2;
rightTopY = (parseFloat(readValue(alignmentFile, "row_2_right_y", "-1")) + parseFloat(readValue(alignmentFile, "row_3_right_y", "-1"))) / 2;
leftLowY = (parseFloat(readValue(alignmentFile, "row_6_left_y", "-1")) + parseFloat(readValue(alignmentFile, "row_7_left_y", "-1"))) / 2;
rightLowY = (parseFloat(readValue(alignmentFile, "row_6_right_y", "-1")) + parseFloat(readValue(alignmentFile, "row_7_right_y", "-1"))) / 2;

if (leftTopY < 0 || rightTopY < 0 || leftLowY < 0 || rightLowY < 0)
    exit("Alignment row geometry is incomplete.");

gridText = File.openAsString(gridFile);
gridLines = split(gridText, "\n");
matched = 0;
seenCols = newArray(gridCols);

// Validate every intended crop before writing the first file. This avoids a
// late bad rectangle leaving a plausible-looking but incomplete output set.
for (i = 1; i < gridLines.length; i++) {
    line = replace(gridLines[i], "\r", "");
    if (lengthOf(line) == 0)
        continue;

    fields = split(line, ",");
    if (fields.length < 5)
        continue;

    gExp = clean(fields[0]);
    gSet = clean(fields[1]);
    if (gExp != experiment || gSet != setName)
        continue;

    declaredCols = parseInt(clean(fields[2]));
    col = parseInt(clean(fields[3]));
    if (declaredCols != gridCols || col < 1 || col > gridCols)
        continue;
    if (seenCols[col - 1] != 0)
        exit("Duplicate grid column " + col + " for experiment " + experiment + " set " + setName + ". No crops were exported.");
    seenCols[col - 1] = 1;

    u = (col - 1) / (gridCols - 1);
    cx = leftX + u * (rightX - leftX);
    topY = leftTopY + u * (rightTopY - leftTopY);
    lowY = leftLowY + u * (rightLowY - leftLowY);

    if (!cropFitsImage(cx, topY, sourceWidth, sourceHeight) || !cropFitsImage(cx, lowY, sourceWidth, sourceHeight))
        exit("Crop bounds exceed the source image for grid column " + col + ". Re-align or reduce crop dimensions; no crops were exported.");
    matched++;
}

if (matched != gridCols)
    exit("Expected " + gridCols + " matching grid rows but found " + matched + ". Fix grid.csv or re-run project validation; no crops were exported.");

exported = 0;
setBatchMode(true);
for (i = 1; i < gridLines.length; i++) {
    line = replace(gridLines[i], "\r", "");
    if (lengthOf(line) == 0)
        continue;

    fields = split(line, ",");
    if (fields.length < 5)
        continue;

    gExp = clean(fields[0]);
    gSet = clean(fields[1]);
    if (gExp != experiment || gSet != setName)
        continue;

    declaredCols = parseInt(clean(fields[2]));
    col = parseInt(clean(fields[3]));
    strain = clean(fields[4]);

    if (declaredCols != gridCols || col < 1 || col > gridCols)
        continue;

    u = (col - 1) / (gridCols - 1);
    cx = leftX + u * (rightX - leftX);

    topY = leftTopY + u * (rightTopY - leftTopY);
    lowY = leftLowY + u * (rightLowY - leftLowY);

    exportCrop(sourceTitle, cx, topY, experiment + "_" + setName + "_" + typeName + "_" + pad2(col) + "_Top_" + safeName(strain), outDir);
    exportCrop(sourceTitle, cx, lowY, experiment + "_" + setName + "_" + typeName + "_" + pad2(col) + "_Low_" + safeName(strain), outDir);
    exported = exported + 2;
}
setBatchMode(false);

selectWindow(sourceTitle);
run("Select None");
showStatus("Exported " + exported + " crops from accepted alignment.");

function cropFitsImage(cx, cy, width, height) {
    x = round(cx - CROP_W / 2);
    y = round(cy - CROP_H / 2);
    return x >= 0 && y >= 0 && x + CROP_W <= width && y + CROP_H <= height;
}

function exportCrop(sourceTitle, cx, cy, outputName, outDir) {
    selectWindow(sourceTitle);
    x = round(cx - CROP_W / 2);
    y = round(cy - CROP_H / 2);
    makeRectangle(x, y, CROP_W, CROP_H);
    run("Duplicate...", "title=[" + outputName + "]");
    saveAs("PNG", outDir + outputName + ".png");
    close();
}

function alignmentMatchesCurrentImage(path, title, width, height) {
    return readValue(path, "source_title", "") == title &&
           parseInt(readValue(path, "source_width", "-1")) == width &&
           parseInt(readValue(path, "source_height", "-1")) == height;
}

function readValue(path, key, fallback) {
    text = File.openAsString(path);
    lines = split(text, "\n");
    prefix = key + "=";
    for (j = 0; j < lines.length; j++) {
        candidate = replace(lines[j], "\r", "");
        if (startsWith(candidate, prefix))
            return substring(candidate, lengthOf(prefix));
    }
    return fallback;
}

function argValue(arg, key, fallback) {
    parts = split(arg, ";");
    prefix = key + "=";
    for (j = 0; j < parts.length; j++) {
        part = String.trim(parts[j]);
        if (startsWith(part, prefix))
            return substring(part, lengthOf(prefix));
    }
    return fallback;
}

function clean(s) {
    s = String.trim(s);
    return replace(s, "\"", "");
}

function pad2(n) {
    if (n < 10) return "0" + n;
    return "" + n;
}

function safeName(s) {
    s = replace(s, "/", "-");
    s = replace(s, "\\", "-");
    s = replace(s, ":", "-");
    s = replace(s, "*", "-");
    s = replace(s, "?", "");
    s = replace(s, "\"", "");
    s = replace(s, "<", "(");
    s = replace(s, ">", ")");
    s = replace(s, "|", "-");
    return s;
}
