// Full-column alignment using native ImageJ profile + peak tools.
// Manual first/last column placement remains authoritative.
// Optional macro argument: cols=10;rows=8;tolerance=0.08;context=E1/A/YPDA

requires("1.53f");

if (nImages() == 0)
    exit("Open a plate image first.");

sourceTitle = getTitle();
sourceWidth = getWidth();
sourceHeight = getHeight();
sourceDirectory = getInfo("image.directory");
sourceFilename = getInfo("image.filename");

arg = getArgument();
context = "";
if (lengthOf(arg) > 0) {
    gridCols = parseInt(argValue(arg, "cols", "10"));
    gridRows = parseInt(argValue(arg, "rows", "8"));
    toleranceFraction = parseFloat(argValue(arg, "tolerance", "0.08"));
    context = argValue(arg, "context", "");
} else {
    Dialog.create("Full-column alignment");
    Dialog.addNumber("Grid columns", 10);
    Dialog.addNumber("Grid rows", 8);
    Dialog.addNumber("Peak tolerance fraction", 0.08, 3);
    Dialog.show();

    gridCols = Dialog.getNumber();
    gridRows = Dialog.getNumber();
    toleranceFraction = Dialog.getNumber();
}

if (gridCols < 2 || gridRows < 2)
    exit("Grid dimensions must be at least 2 x 2.");
if (toleranceFraction <= 0)
    exit("Peak tolerance fraction must be positive.");

roiW = readPresetValue("width", 108);
roiH = readPresetValue("height", 108);
accepted = 0;
previousColumnSpan = readPreviousColumnSpan(sourceWidth, sourceHeight);
seededReference = seedPreviousReferenceROI(sourceWidth, sourceHeight);

while (accepted == 0) {
    Overlay.remove;

    contextText = "";
    if (context != "")
        contextText = "Plate: " + context + "\n\n";
    if (seededReference) {
        contextText = contextText +
            "Previous accepted whole-column box is pre-positioned as a starting point.\n" +
            "Move/resize it for this plate; it is NOT accepted automatically.\n\n";
        seededReference = 0;
    }

    waitForUser(
        "1 / 2 — First column",
        contextText +
        "Draw or position ONE tall rectangle around the entire FIRST grid column.\n" +
        "It should include all " + gridRows + " row positions.\n\n" +
        "Move/resize it as needed, then press OK (or Z with the helper)."
    );

    if (!isTallRectangle()) {
        showMessage("First-column ROI", "Use one tall axis-aligned rectangle containing the full first column, then retry.");
        continue;
    }

    getSelectionBounds(lx, ly, lw, lh);
    leftProfile = getVerticalAverageProfile(lx, ly, lw, lh);
    leftPeaks = findExpectedPeaks(leftProfile, gridRows, toleranceFraction);
    if (leftPeaks.length < gridRows) {
        showMessage("First-column profile", "Could not resolve " + gridRows + " row peaks. Retry with a better whole-column ROI or lower tolerance.");
        continue;
    }

    leftX = lx + lw / 2;
    leftRows = newArray(gridRows);
    for (r = 0; r < gridRows; r++)
        leftRows[r] = ly + leftPeaks[r] + 0.5;

    lastColumnHint = "";
    if (!isNaN(previousColumnSpan)) {
        suggestedX = lx + previousColumnSpan;
        if (suggestedX >= 0 && suggestedX + lw <= sourceWidth) {
            makeRectangle(suggestedX, ly, lw, lh);
            lastColumnHint =
                "Previous accepted first-to-last span moved this SAME rectangle near the last column as a starting point.\n" +
                "Fine-tune it for this plate; it is NOT accepted automatically.\n\n";
        }
    }

    waitForUser(
        "2 / 2 — Last column",
        lastColumnHint +
        "Move the SAME tall rectangle to the entire LAST grid column.\n" +
        "Keep all " + gridRows + " row positions inside it.\n\n" +
        "Press OK (or Z) when positioned."
    );

    if (!isTallRectangle()) {
        showMessage("Last-column ROI", "Use one tall axis-aligned rectangle containing the full last column, then retry.");
        makeRectangle(lx, ly, lw, lh);
        continue;
    }

    getSelectionBounds(rx, ry, rw, rh);
    rightProfile = getVerticalAverageProfile(rx, ry, rw, rh);
    rightPeaks = findExpectedPeaks(rightProfile, gridRows, toleranceFraction);
    if (rightPeaks.length < gridRows) {
        showMessage("Last-column profile", "Could not resolve " + gridRows + " row peaks. Retry with a better whole-column ROI or lower tolerance.");
        makeRectangle(lx, ly, lw, lh);
        continue;
    }

    rightX = rx + rw / 2;
    rightRows = newArray(gridRows);
    for (r = 0; r < gridRows; r++)
        rightRows[r] = ry + rightPeaks[r] + 0.5;

    drawGridOverlay(leftX, rightX, leftRows, rightRows, gridCols, gridRows, roiW, roiH);

    Dialog.create("Alignment QC");
    Dialog.addMessage(
        "Inspect the complete proposed grid overlay.\n\n" +
        "Accept keeps this geometry. Retry returns to first/last-column alignment."
    );
    Dialog.addChoice("Action", newArray("Accept", "Retry"), "Accept");
    Dialog.show();
    action = Dialog.getChoice();

    if (action == "Accept") {
        accepted = 1;
        saveLastAlignment(sourceTitle, sourceWidth, sourceHeight, sourceDirectory, sourceFilename, lx, ly, lw, lh, leftX, rightX, leftRows, rightRows, gridCols, gridRows, roiW, roiH);
    } else {
        Overlay.remove;
        makeRectangle(lx, ly, lw, lh);
    }
}

showStatus("Full-column alignment accepted and saved.");

function isTallRectangle() {
    if (selectionType() != 0)
        return 0;
    getSelectionBounds(x, y, w, h);
    return w > 0 && h > w;
}

function previousAlignmentPath() {
    return getDirectory("home") + ".cautious-rotary-phone" + File.separator + "last_alignment.txt";
}

function readPreviousColumnSpan(width, height) {
    path = previousAlignmentPath();
    if (!File.exists(path))
        return NaN;

    previousWidth = parseInt(readSavedValue(path, "source_width", "-1"));
    previousHeight = parseInt(readSavedValue(path, "source_height", "-1"));
    if (previousWidth != width || previousHeight != height)
        return NaN;

    previousLeftX = parseFloat(readSavedValue(path, "left_x", "NaN"));
    previousRightX = parseFloat(readSavedValue(path, "right_x", "NaN"));
    if (isNaN(previousLeftX) || isNaN(previousRightX) || previousRightX <= previousLeftX)
        return NaN;

    return previousRightX - previousLeftX;
}

function seedPreviousReferenceROI(width, height) {
    path = previousAlignmentPath();
    if (!File.exists(path))
        return 0;

    previousWidth = parseInt(readSavedValue(path, "source_width", "-1"));
    previousHeight = parseInt(readSavedValue(path, "source_height", "-1"));
    if (previousWidth != width || previousHeight != height)
        return 0;

    x = parseFloat(readSavedValue(path, "reference_roi_x", "-1"));
    y = parseFloat(readSavedValue(path, "reference_roi_y", "-1"));
    w = parseFloat(readSavedValue(path, "reference_roi_width", "-1"));
    h = parseFloat(readSavedValue(path, "reference_roi_height", "-1"));
    if (x < 0 || y < 0 || w <= 0 || h <= w)
        return 0;
    if (x + w > width || y + h > height)
        return 0;

    makeRectangle(x, y, w, h);
    return 1;
}

// ImageJ natively averages wide straight-line profiles. Convert the user's tall
// rectangle temporarily to a vertical line whose width equals the rectangle,
// retrieve the compiled ImageJ profile, then restore the rectangle. If an
// installation/image type returns an unexpectedly short profile, fall back to
// ImageJ's native ROI statistics one row at a time rather than custom pixel reads.
function getVerticalAverageProfile(x, y, w, h) {
    centerX = x + w / 2;
    lineBottom = y + h - 1;
    makeLine(centerX, y, centerX, lineBottom, w);
    profile = getProfile();
    makeRectangle(x, y, w, h);

    if (profile.length >= h - 2)
        return profile;

    return getVerticalAverageProfileFallback(x, y, w, h);
}

function getVerticalAverageProfileFallback(x, y, w, h) {
    profile = newArray(h);
    for (yy = 0; yy < h; yy++) {
        makeRectangle(x, y + yy, w, 1);
        getStatistics(area, mean);
        profile[yy] = mean;
    }
    makeRectangle(x, y, w, h);
    return profile;
}

function findExpectedPeaks(profile, expected, fraction) {
    Array.getStatistics(profile, minV, maxV, meanV, stdV);
    span = maxV - minV;
    if (span <= 0)
        return newArray();

    tol = span * fraction;
    peaks = Array.findMaxima(profile, tol);
    attempt = 0;

    while (peaks.length < expected && attempt < 6) {
        tol = tol / 2;
        peaks = Array.findMaxima(profile, tol);
        attempt++;
    }

    if (peaks.length < expected)
        return newArray();

    peaks = Array.trim(peaks, expected);
    Array.sort(peaks);
    return peaks;
}

function drawGridOverlay(leftX, rightX, leftRows, rightRows, cols, rows, boxW, boxH) {
    Overlay.remove;
    setLineWidth(1);
    setColor("cyan");

    for (r = 0; r < rows; r++) {
        for (c = 0; c < cols; c++) {
            u = c / (cols - 1);
            cx = leftX + u * (rightX - leftX);
            cy = leftRows[r] + u * (rightRows[r] - leftRows[r]);
            Overlay.drawRect(cx - boxW / 2, cy - boxH / 2, boxW, boxH);
        }
    }

    setColor("yellow");
    Overlay.drawLine(leftX, leftRows[0], rightX, rightRows[0]);
    Overlay.drawLine(leftX, leftRows[rows - 1], rightX, rightRows[rows - 1]);
    Overlay.drawLine(leftX, leftRows[0], leftX, leftRows[rows - 1]);
    Overlay.drawLine(rightX, rightRows[0], rightX, rightRows[rows - 1]);
    Overlay.show;
}

function readPresetValue(key, fallback) {
    presetFile = getDirectory("home") + ".cautious-rotary-phone" + File.separator + "active_roi_preset.txt";
    if (!File.exists(presetFile))
        return fallback;

    saved = readSavedValue(presetFile, key, "");
    if (saved == "")
        return fallback;
    value = parseFloat(saved);
    if (isNaN(value) || value <= 0)
        return fallback;
    return value;
}

function readSavedValue(path, key, fallback) {
    text = File.openAsString(path);
    lines = split(text, "\n");
    prefix = key + "=";

    for (i = 0; i < lines.length; i++) {
        line = replace(lines[i], "\r", "");
        if (startsWith(line, prefix))
            return substring(line, lengthOf(prefix));
    }
    return fallback;
}

function saveLastAlignment(sourceTitle, sourceWidth, sourceHeight, sourceDirectory, sourceFilename, referenceX, referenceY, referenceW, referenceH, leftX, rightX, leftRows, rightRows, cols, rows, boxW, boxH) {
    dir = getDirectory("home") + ".cautious-rotary-phone" + File.separator;
    if (!File.exists(dir))
        File.makeDirectory(dir);

    text = "source_title=" + sourceTitle + "\n" +
           "source_width=" + sourceWidth + "\n" +
           "source_height=" + sourceHeight + "\n" +
           "source_directory=" + sourceDirectory + "\n" +
           "source_filename=" + sourceFilename + "\n" +
           "reference_roi_x=" + referenceX + "\n" +
           "reference_roi_y=" + referenceY + "\n" +
           "reference_roi_width=" + referenceW + "\n" +
           "reference_roi_height=" + referenceH + "\n" +
           "grid_cols=" + cols + "\n" +
           "grid_rows=" + rows + "\n" +
           "roi_width=" + boxW + "\n" +
           "roi_height=" + boxH + "\n" +
           "left_x=" + leftX + "\n" +
           "right_x=" + rightX + "\n";

    for (r = 0; r < rows; r++)
        text = text + "row_" + (r + 1) + "_left_y=" + leftRows[r] + "\n" +
                      "row_" + (r + 1) + "_right_y=" + rightRows[r] + "\n";

    File.saveString(text, dir + "last_alignment.txt");
}

function argValue(arg, key, fallback) {
    parts = split(arg, ";");
    prefix = key + "=";
    for (i = 0; i < parts.length; i++) {
        part = String.trim(parts[i]);
        if (startsWith(part, prefix))
            return substring(part, lengthOf(prefix));
    }
    return fallback;
}