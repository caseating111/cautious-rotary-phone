// Apply one global display range derived from accepted grid geometry.
// Source pixels remain untouched. RGB inputs use a disposable 8-bit QC duplicate
// because ImageJ setMinAndMax() modifies RGB pixel data.

requires("1.53g");

if (nImages() == 0)
    exit("Open an aligned plate image first.");

alignmentFile = getDirectory("home") + ".cautious-rotary-phone" + File.separator + "last_alignment.txt";
if (!File.exists(alignmentFile))
    exit("No accepted alignment found. Run full_column_alignment.ijm first.");

sourceTitle = getTitle();
sourceWidth = getWidth();
sourceHeight = getHeight();
expectedTitle = readAlignmentValue(alignmentFile, "source_title", "");
expectedWidth = parseInt(readAlignmentValue(alignmentFile, "source_width", "-1"));
expectedHeight = parseInt(readAlignmentValue(alignmentFile, "source_height", "-1"));

if (expectedTitle == "" || expectedWidth < 1 || expectedHeight < 1)
    exit("Alignment geometry predates image-identity checks. Re-align this image once before applying visibility.");
if (expectedTitle != sourceTitle || expectedWidth != sourceWidth || expectedHeight != sourceHeight)
    exit("The saved alignment belongs to a different image. Re-align the current image before applying visibility.");

Dialog.create("Global visibility");
Dialog.addNumber("Outside-grid band (px)", 50);
Dialog.addNumber("Black-point offset", 3);
Dialog.addNumber("Inside-grid high percentile", 99.5, 1);
Dialog.show();

band = Dialog.getNumber();
blackOffset = Dialog.getNumber();
highPercent = Dialog.getNumber() / 100;

if (band < 1)
    exit("Background band must be at least 1 px.");
if (highPercent <= 0 || highPercent > 1)
    exit("High percentile must be >0 and <=100.");

sourceDepth = bitDepth();
run("Select None");

if (sourceDepth == 24) {
    run("Duplicate...", "title=QC_display");
    rename("QC - " + sourceTitle);
    run("8-bit");
}

imgW = getWidth();
imgH = getHeight();

rows = parseInt(readAlignmentValue(alignmentFile, "grid_rows", "-1"));
roiW = parseFloat(readAlignmentValue(alignmentFile, "roi_width", "-1"));
roiH = parseFloat(readAlignmentValue(alignmentFile, "roi_height", "-1"));
leftX = parseFloat(readAlignmentValue(alignmentFile, "left_x", "-1"));
rightX = parseFloat(readAlignmentValue(alignmentFile, "right_x", "-1"));

if (rows < 2 || roiW <= 0 || roiH <= 0 || leftX < 0 || rightX < 0)
    exit("Accepted alignment file is incomplete.");

topLeftY = parseFloat(readAlignmentValue(alignmentFile, "row_1_left_y", "-1"));
topRightY = parseFloat(readAlignmentValue(alignmentFile, "row_1_right_y", "-1"));
bottomLeftY = parseFloat(readAlignmentValue(alignmentFile, "row_" + rows + "_left_y", "-1"));
bottomRightY = parseFloat(readAlignmentValue(alignmentFile, "row_" + rows + "_right_y", "-1"));

if (topLeftY < 0 || topRightY < 0 || bottomLeftY < 0 || bottomRightY < 0)
    exit("Accepted alignment row geometry is incomplete.");

gridLeft = maxOf(0, minOf(leftX, rightX) - roiW / 2);
gridRight = minOf(imgW, maxOf(leftX, rightX) + roiW / 2);
gridTop = maxOf(0, minOf(topLeftY, topRightY) - roiH / 2);
gridBottom = minOf(imgH, maxOf(bottomLeftY, bottomRightY) + roiH / 2);

if (gridRight - gridLeft < 2 || gridBottom - gridTop < 2)
    exit("Calculated total-grid bounds are invalid.");

topMedian = sampleRectPercentile(gridLeft, maxOf(0, gridTop - band), gridRight - gridLeft, minOf(band, gridTop), 0.5);
bottomMedian = sampleRectPercentile(gridLeft, gridBottom, gridRight - gridLeft, minOf(band, imgH - gridBottom), 0.5);
leftMedian = sampleRectPercentile(maxOf(0, gridLeft - band), gridTop, minOf(band, gridLeft), gridBottom - gridTop, 0.5);
rightMedian = sampleRectPercentile(gridRight, gridTop, minOf(band, imgW - gridRight), gridBottom - gridTop, 0.5);

background = robustSideMedian(topMedian, bottomMedian, leftMedian, rightMedian);
if (isNaN(background))
    exit("No usable outside-grid background strips were available.");

xs = newArray(leftX - roiW / 2, rightX + roiW / 2, rightX + roiW / 2, leftX - roiW / 2);
ys = newArray(topLeftY - roiH / 2, topRightY - roiH / 2, bottomRightY + roiH / 2, bottomLeftY + roiH / 2);
makeSelection("polygon", xs, ys);
highPoint = selectionPercentile(highPercent);

blackPoint = background - blackOffset;
if (blackPoint < 0)
    blackPoint = 0;
if (highPoint <= blackPoint)
    highPoint = blackPoint + 1;

run("Select None");
setMinAndMax(blackPoint, highPoint);

saveDisplayRange(sourceTitle, background, blackPoint, highPoint, band, highPercent);
showStatus("Global display range: " + d2s(blackPoint, 1) + " to " + d2s(highPoint, 1));

function sampleRectPercentile(x, y, w, h, percentile) {
    if (w < 1 || h < 1)
        return NaN;
    makeRectangle(x, y, w, h);
    return selectionPercentile(percentile);
}

function selectionPercentile(percentile) {
    getHistogram(values, counts, 256);
    total = 0;
    for (i = 0; i < counts.length; i++)
        total = total + counts[i];
    if (total <= 0)
        return NaN;

    target = total * percentile;
    running = 0;
    for (i = 0; i < counts.length; i++) {
        running = running + counts[i];
        if (running >= target)
            return values[i];
    }
    return values[values.length - 1];
}

function robustSideMedian(a, b, c, d) {
    vals = newArray(0);
    if (!isNaN(a)) vals = Array.concat(vals, a);
    if (!isNaN(b)) vals = Array.concat(vals, b);
    if (!isNaN(c)) vals = Array.concat(vals, c);
    if (!isNaN(d)) vals = Array.concat(vals, d);
    if (vals.length == 0) return NaN;
    Array.sort(vals);
    n = vals.length;
    if (n % 2 == 1) return vals[floor(n / 2)];
    return (vals[n / 2 - 1] + vals[n / 2]) / 2;
}

function readAlignmentValue(path, key, fallback) {
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

function saveDisplayRange(sourceTitle, background, blackPoint, highPoint, band, highPercent) {
    dir = getDirectory("home") + ".cautious-rotary-phone" + File.separator;
    if (!File.exists(dir))
        File.makeDirectory(dir);

    text = "source=" + sourceTitle + "\n" +
           "background=" + background + "\n" +
           "black_point=" + blackPoint + "\n" +
           "high_point=" + highPoint + "\n" +
           "background_band_px=" + band + "\n" +
           "high_percentile=" + (highPercent * 100) + "\n";

    File.saveString(text, dir + "last_display_range.txt");
}
