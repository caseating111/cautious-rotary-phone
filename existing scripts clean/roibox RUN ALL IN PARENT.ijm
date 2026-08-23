// ============================================================
// BATCH YEAST PLATE CROP EXPORTER
//
// Input structure:
// INPUT_ROOT/
//   exp1_0/
//   exp2A/
//   exp2B/
//
// Output structure mirrors the immediate input subfolder:
// OUTPUT_ROOT/
//   exp1_0/
//   exp2A/
//   exp2B/
//
// Calibration per image:
// R1C1, R1C(last), R5C1, R5C(last)
//
// Uses active movable rectangle ROI (e.g. ROI 1-click 108x108).
//
// grid.csv:
// Experiment,Set,GridCols,Column,Strain
//
// images.csv:
// Filename,Experiment,Set,Type
// ============================================================


// ============================================================
// HARD-CODE PATHS HERE
// Use forward slashes on Windows.
// ============================================================
gridFile   = "path here";
imagesFile = "path here";
stateFile  = "path here";
replacementManifest = "path here";
 

inputRoot  = "path here";
outputRoot = "path here"; 

inputRoot  = inputRoot  + File.separator;
outputRoot = outputRoot + File.separator;


// Tested 4-row crop dimensions
CROP_W = 130;
CROP_H = 546;


// ============================================================
// LOAD CSVs ONCE
// ============================================================

imgText = File.openAsString(imagesFile);
imgLines = split(imgText, "\n");

gridText = File.openAsString(gridFile);
gridLines = split(gridText, "\n");


// ============================================================
// PROCESS IMMEDIATE SUBFOLDERS
// ============================================================

folders = getFileList(inputRoot);

processedImages = 0;
notListedImages = 0;
skippedImages = 0;

for (folderIndex = 0; folderIndex < folders.length; folderIndex++) {

    folderName = folders[folderIndex];

    // ImageJ denotes directories with trailing separator
    if (!endsWith(folderName, "/"))
    	continue;

    inputDir = inputRoot + folderName;

    // Remove trailing separator for output folder name
	cleanFolderName = substring(
	    folderName,
	    0,
	    lengthOf(folderName) - 1
	);

    outDir = outputRoot + cleanFolderName + File.separator;

    if (!File.exists(outDir))
        File.makeDirectory(outDir);

    files = getFileList(inputDir);


    // ========================================================
    // PROCESS IMAGES IN THIS SET FOLDER
    // ========================================================

    for (fileIndex = 0; fileIndex < files.length; fileIndex++) {

        fileName = files[fileIndex];

        if (!isImageFile(fileName))
            continue;


        // ====================================================
        // LOOK UP IMAGE IN images.csv BEFORE OPENING IT
        // Handles quoted filenames containing commas.
        // In controller use, images.csv is the pending-only preflight file,
        // so completed images are skipped without paying the Fiji open/close cost.
        // ====================================================

        experiment = "";
        setName = "";
        typeName = "";

        for (i = 1; i < imgLines.length; i++) {

            line = replace(imgLines[i], "\r", "");

            if (lengthOf(line) == 0)
                continue;

            // Windows filename identity is case-insensitive. Match on normalized
            // keys while preserving the original physical and CSV display values.
            lowerLine = toLowerCase(line);
            lowerFileName = toLowerCase(fileName);
            quotedPrefix = "\"" + lowerFileName + "\",";
            plainPrefix  = lowerFileName + ",";

            if (startsWith(lowerLine, quotedPrefix)) {

                rest = substring(line, lengthOf(quotedPrefix));
                f = split(rest, ",");

                if (f.length >= 3) {
                    experiment = clean(f[0]);
                    setName    = clean(f[1]);
                    typeName   = clean(f[2]);
                }
            }

            else if (startsWith(lowerLine, plainPrefix)) {

                rest = substring(line, lengthOf(plainPrefix));
                f = split(rest, ",");

                if (f.length >= 3) {
                    experiment = clean(f[0]);
                    setName    = clean(f[1]);
                    typeName   = clean(f[2]);
                }
            }
        }


        // In controller use, absence normally means this source is already
        // complete and therefore not in the pending-only metadata file.
        if (experiment == "") {

            stateKey = cleanFolderName + "/" + fileName;
            previousRun = recordedRun(stateKey);
            if (previousRun > 0)
                print("DONE / NOT SELECTED - run " + previousRun + ": " + stateKey);
            else
                print("NOT PENDING - no recorded completed run: " + stateKey);

            notListedImages++;

            continue;
        }

        fullPath = inputDir + fileName;
        open(fullPath);
        sourceTitle = getTitle();


        // ====================================================
        // FIND GRID CONFIG
        // ====================================================

        nWanted = 0;
        gridCols = -1;

        for (i = 1; i < gridLines.length; i++) {

            line = replace(gridLines[i], "\r", "");

            if (lengthOf(line) == 0)
                continue;

            f = split(line, ",");

            if (f.length >= 5) {

                gExp = clean(f[0]);
                gSet = clean(f[1]);

                if (gExp == experiment && gSet == setName) {

                    nWanted++;
                    gridCols = parseInt(clean(f[2]));
                }
            }
        }


        if (nWanted == 0) {

            print(
                "SKIPPED - no grid configuration: " +
                sourceTitle
            );

            close();
            skippedImages++;

            continue;
        }


        if (gridCols != 10 && gridCols != 12) {

            print(
                "SKIPPED - invalid GridCols: " +
                sourceTitle
            );

            close();
            skippedImages++;

            continue;
        }


        columns = newArray(nWanted);
        strains = newArray(nWanted);

        j = 0;

        for (i = 1; i < gridLines.length; i++) {

            line = replace(gridLines[i], "\r", "");

            if (lengthOf(line) == 0)
                continue;

            f = split(line, ",");

            if (f.length >= 5) {

                gExp = clean(f[0]);
                gSet = clean(f[1]);

                if (gExp == experiment && gSet == setName) {

                    columns[j] = parseInt(clean(f[3]));
                    strains[j] = clean(f[4]);

                    j++;
                }
            }
        }


        // ====================================================
        // IDENTIFY CURRENT PLATE
        // ====================================================

        showMessage(
            "Next plate",
            "Folder: " + cleanFolderName + "\n\n" +
            "Image: " + sourceTitle + "\n\n" +
            "Experiment: " + experiment + "\n" +
            "Set: " + setName + "\n" +
            "Type: " + typeName + "\n" +
            "Grid: 8 x " + gridCols + "\n" +
            "Exports: " + (nWanted * 2) + "\n\n" +
            "Next: centre your 108x108 box four times."
        );


        // ====================================================
        // CALIBRATION
        //
        // For each:
        // reposition your 108x108 ROI until centred,
        // leave ROI active, press OK.
        // ====================================================


        // ---------- R1C1 ----------

        waitForUser(
            "1 / 4 - R1C1",
            sourceTitle + "\n\n" +
            "Centre box on ROW 1, COLUMN 1.\n\n" +
            "Reposition as needed, then click OK."
        );

        getSelectionBounds(x, y, w, h);

        if (w <= 0 || h <= 0)
            exit("No rectangle ROI found for R1C1.");

        R1LX = x + w / 2;
        R1LY = y + h / 2;


        // ---------- R1C(last) ----------

        waitForUser(
            "2 / 4 - R1C" + gridCols,
            sourceTitle + "\n\n" +
            "Centre box on ROW 1, COLUMN " +
            gridCols + ".\n\n" +
            "Reposition as needed, then click OK."
        );

        getSelectionBounds(x, y, w, h);

        if (w <= 0 || h <= 0)
            exit("No rectangle ROI found for row 1 right.");

        R1RX = x + w / 2;
        R1RY = y + h / 2;


        // ---------- R5C1 ----------

        waitForUser(
            "3 / 4 - R5C1",
            sourceTitle + "\n\n" +
            "Centre box on ROW 5, COLUMN 1.\n\n" +
            "Reposition as needed, then click OK."
        );

        getSelectionBounds(x, y, w, h);

        if (w <= 0 || h <= 0)
            exit("No rectangle ROI found for R5C1.");

        R5LX = x + w / 2;
        R5LY = y + h / 2;


        // ---------- R5C(last) ----------

        waitForUser(
            "4 / 4 - R5C" + gridCols,
            sourceTitle + "\n\n" +
            "Centre box on ROW 5, COLUMN " +
            gridCols + ".\n\n" +
            "Reposition as needed, then click OK."
        );

        getSelectionBounds(x, y, w, h);

        if (w <= 0 || h <= 0)
            exit("No rectangle ROI found for row 5 right.");

        R5RX = x + w / 2;
        R5RY = y + h / 2;


        // ====================================================
        // EXPORT CROPS
        //
        // R1 -> R5 = four row intervals.
        //
        // Top rows 1-4 centre = row 2.5:
        // (2.5-1)/4 = 0.375
        //
        // Low rows 5-8 centre = row 6.5:
        // (6.5-1)/4 = 1.375
        // ====================================================

        TOP_FACTOR = 0.375;
        LOW_FACTOR = 1.375;

        setBatchMode(true);


        for (i = 0; i < nWanted; i++) {

            col = columns[i];
            strain = strains[i];

            u = (col - 1) / (gridCols - 1);


            // ================================================
            // TOP
            // ================================================

            leftX =
                R1LX +
                TOP_FACTOR * (R5LX - R1LX);

            leftY =
                R1LY +
                TOP_FACTOR * (R5LY - R1LY);

            rightX =
                R1RX +
                TOP_FACTOR * (R5RX - R1RX);

            rightY =
                R1RY +
                TOP_FACTOR * (R5RY - R1RY);

            cx =
                leftX +
                u * (rightX - leftX);

            cy =
                leftY +
                u * (rightY - leftY);


            outputName =
                experiment + "_" +
                setName + "_" +
                typeName + "_" +
                pad2(col) + "_Top_" +
                safeName(strain);


            exportCrop(
                sourceTitle,
                cx,
                cy,
                outputName,
                outDir
            );


            // ================================================
            // LOW
            // ================================================

            leftX =
                R1LX +
                LOW_FACTOR * (R5LX - R1LX);

            leftY =
                R1LY +
                LOW_FACTOR * (R5LY - R1LY);

            rightX =
                R1RX +
                LOW_FACTOR * (R5RX - R1RX);

            rightY =
                R1RY +
                LOW_FACTOR * (R5RY - R1RY);

            cx =
                leftX +
                u * (rightX - leftX);

            cy =
                leftY +
                u * (rightY - leftY);


            outputName =
                experiment + "_" +
                setName + "_" +
                typeName + "_" +
                pad2(col) + "_Low_" +
                safeName(strain);


            exportCrop(
                sourceTitle,
                cx,
                cy,
                outputName,
                outDir
            );
        }


        setBatchMode(false);

        selectWindow(sourceTitle);
        close();

        processedImages++;
        stateKey = cleanFolderName + "/" + fileName;
        runNumber = recordedRun(stateKey) + 1;
        File.append(stateKey + "\t" + runNumber + "\n", stateFile);

        print(
            "DONE - run " + runNumber + ": " + stateKey +
            " -> " + outDir
        );
    }
}


// ============================================================
// FINISHED
// ============================================================

showMessage(
    "ALL DONE",
    "Processed images: " + processedImages + "\n" +
    "Not listed / not pending: " + notListedImages + "\n" +
    "Skipped after metadata match: " + skippedImages + "\n\n" +
    "Outputs saved under:\n" +
    outputRoot
);


// ============================================================
// FUNCTIONS
// ============================================================

function clean(s) {

    s = String.trim(s);
    s = replace(s, "\"", "");

    return s;
}


function exportCrop(sourceTitle, cx, cy, outputName, outDir) {

    selectWindow(sourceTitle);

    x = round(cx - CROP_W / 2);
    y = round(cy - CROP_H / 2);

    makeRectangle(
        x,
        y,
        CROP_W,
        CROP_H
    );

    run(
        "Duplicate...",
        "title=[" + outputName + "]"
    );

    // Intentionally NOT rotated yet.
    saveAs(
        "PNG",
        outDir + outputName + ".png"
    );

    close();
}

function requireCropFits(cx, cy, cropW, cropH, imageW, imageH, title, col, band) {
    x = round(cx - cropW / 2);
    y = round(cy - cropH / 2);
    if (x < 0 || y < 0 || x + cropW > imageW || y + cropH > imageH)
        exit(
            "Crop would cross source bounds before any existing crops were archived or outputs written: " +
            title + ", column " + col + " " + band +
            ". Re-align or reduce crop dimensions."
        );
}



function pad2(n) {

    if (n < 10)
        return "0" + n;

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


function recordedRun(key) {

    if (!File.exists(stateFile))
        return 0;

    entries = split(File.openAsString(stateFile), "\n");
    prefix = key + "\t";
    for (entryIndex = entries.length - 1; entryIndex >= 0; entryIndex--) {
        entry = replace(entries[entryIndex], "\r", "");
        if (startsWith(entry, prefix))
            return parseInt(substring(entry, lengthOf(prefix)));
    }
    return 0;
}


function archiveReplacementCrops(folderName, fileName) {
    if (replacementManifest == "" || !File.exists(replacementManifest))
        return;
    entries = split(File.openAsString(replacementManifest), "\n");
    for (entryIndex = 1; entryIndex < entries.length; entryIndex++) {
        fields = split(replace(entries[entryIndex], "\r", ""), "\t");
        if (fields.length != 8 || fields[0] != folderName || fields[1] != fileName)
            continue;
        sourceCrop = fields[2];
        targetCrop = fields[3];
        if (!File.exists(sourceCrop))
            exit("Expected crop disappeared before replacement: " + sourceCrop);
        targetDir = substring(targetCrop, 0, lastIndexOf(targetCrop, "/"));
        eval("script", "var f=new java.io.File('" + escapeJavaScript(targetDir) + "'); f.mkdirs(); '';");
        if (!File.rename(sourceCrop, targetCrop))
            exit("Could not archive existing crop before replacement: " + sourceCrop);
        updateDiscardManifest(
            fields[6], fields[4], fields[7], fields[5],
            folderName, fileName, sourceCrop, targetCrop
        );
    }
}


function updateDiscardManifest(manifestPath, strain, archivedAt, originalCropTime, folderName, fileName, sourceCrop, targetCrop) {
    separator = "======================================================================\n";
    marker = "STRAIN: " + strain + "\n";
    columnHeader = "archived_at\toriginal_crop_time\tsource_folder\tsource_plate\toriginal_crop\tdiscarded_crop\n";
    row = archivedAt + "\t" + originalCropTime + "\t" + folderName + "\t" + fileName + "\t" + sourceCrop + "\t" + targetCrop + "\n";
    group = separator + marker + "----------------------------------------------------------------------\n" + columnHeader + row;

    if (!File.exists(manifestPath)) {
        File.saveString(group, manifestPath);
        return;
    }

    existing = File.openAsString(manifestPath);
    groupStart = indexOf(existing, marker);
    if (groupStart < 0) {
        if (!endsWith(existing, "\n"))
            existing = existing + "\n";
        File.saveString(existing + group, manifestPath);
        return;
    }

    groupAndAfter = substring(existing, groupStart);
    nextGroupOffset = indexOf(groupAndAfter, "\n======================================================================\n");
    if (nextGroupOffset < 0)
        File.saveString(existing + row, manifestPath);
    else
        File.saveString(
            substring(existing, 0, groupStart + nextGroupOffset + 1) + row +
            substring(existing, groupStart + nextGroupOffset + 1),
            manifestPath
        );
}


function escapeJavaScript(value) {
    value = replace(value, "\\", "\\\\");
    return replace(value, "'", "\\'");
}


function isImageFile(name) {

    lower = toLowerCase(name);

    return
        endsWith(lower, ".jpg") ||
        endsWith(lower, ".jpeg") ||
        endsWith(lower, ".png") ||
        endsWith(lower, ".tif") ||
        endsWith(lower, ".tiff");
}
