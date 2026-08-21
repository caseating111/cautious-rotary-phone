// Full-column alignment prototype using native ImageJ profile + peak tools.
// Manual first/last column placement remains authoritative.

requires("1.53f");

if (nImages() == 0)
    exit("Open a plate image first.");

Dialog.create("Full-column alignment");
Dialog.addNumber("Grid columns", 10);
Dialog.addNumber("Grid rows", 8);
Dialog.addNumber("Peak tolerance fraction", 0.08, 3);
Dialog.show();

gridCols = Dialog.getNumber();
gridRows = Dialog.getNumber();
toleranceFraction = Dialog.getNumber();

if (gridCols < 2 || gridRows < 2)
    exit("Grid dimensions must be at least 2 x 2.");
if (toleranceFraction <= 0)
    exit("Peak tolerance fraction must be positive.");

roiW = readPresetValue("width", 108);
roiH = readPresetValue("height", 108);
accepted = 0;

while (accepted == 0) {
    Overlay.remove;

    waitForUser(
        "1 / 2 — First column",
        "Draw or position ONE tall rectangle around the entire FIRST grid column.\n" +
        "It should include all " + gridRows + " row positions.\n\n" +
        "Move/resize it as needed, then press OK (or Z with the helper)."
    );

    requireTallRectangle("first column");
    getSelectionBounds(lx, ly, lw, lh);
    leftProfile = getProfile();
    leftPeaks = findExpectedPeaks(leftProfile, gridRows, toleranceFraction);
    if (leftPeaks.length < gridRows) {
        showMessage("First-column profile", "Could not resolve " + gridRows + " row peaks. Retry with a better whole-column ROI or lower tolerance.");
        continue;
    }

    leftX = lx + lw / 2;
    leftRows = newArray(gridRows);
    for (r = 0; r < gridRows; r++)
        leftRows[r] = ly + leftPeaks[r] + 0.5;

    waitForUser(
        "2 / 2 — Last column",
        "Move the SAME tall rectangle to the entire LAST grid column.\n" +
        "Keep all " + gridRows + " row positions inside it.\n\n" +
        "Press OK (or Z) when positioned."
    );

    requireTallRectangle("last column");
    getSelectionBounds(rx, ry, rw, rh);
    rightProfile = getProfile();
    rightPeaks = findExpectedPeaks(rightProfile, gridRows, toleranceFraction);
    if (rightPeaks.length < gridRows) {
        showMessage("Last-column profile", "Could not resolve " + gridRows + " row peaks. Retry with a better whole-column ROI or lower tolerance.");
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
        saveLastAlignment(leftX, rightX, leftRows, rightRows, gridCols, gridRows, roiW, roiH);
    } else {
        Overlay.remove;
    }
}

showStatus("Full-column alignment accepted and saved.");

function requireTallRectangle(label) {
    if (selectionType() != 0)
        exit("Use an axis-aligned rectangular ROI for the " + label + ".");
    getSelectionBounds(x, y, w, h);
    if (w <= 0 || h <= 0)
        exit("No rectangle ROI found for the " + label + ".");
    if (h <= w)
        exit("The whole-column ROI should be taller than it is wide.");
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

    text = File.openAsString(presetFile);
    lines = split(text, "\n");
    prefix = key + "=";

    for (i = 0; i < lines.length; i++) {
        line = replace(lines[i], "\r", "");
        if (startsWith(line, prefix))
            return parseFloat(substring(line, lengthOf(prefix)));
    }
    return fallback;
}

function saveLastAlignment(leftX, rightX, leftRows, rightRows, cols, rows, boxW, boxH) {
    dir = getDirectory("home") + ".cautious-rotary-phone" + File.separator;
    if (!File.exists(dir))
        File.makeDirectory(dir);

    text = "grid_cols=" + cols + "\n" +
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
