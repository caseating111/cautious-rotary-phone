// Thin wrapper around apply_global_visibility.ijm.
// Keeps the mature display-range calculation unchanged, then archives the accepted
// range by source filename so Pillow presentation outputs can reuse it later.

requires("1.53g");

if (nImages() == 0)
    exit("Open an aligned plate image first.");

sourceDirectory = getInfo("image.directory");
sourceFilename = getInfo("image.filename");
sourceTitle = getTitle();
sourceWidth = getWidth();
sourceHeight = getHeight();

inner = getDirectory("startup") + "macros" + File.separator + "__missing__";
// The controller launches this repository macro directly, so resolve its companion
// from the same repository-relative path passed through the macro interpreter.
thisPath = getInfo("macro.filepath");
if (thisPath == "")
    exit("Could not determine this macro's path.");
macroDir = File.getParent(thisPath) + File.separator;
inner = macroDir + "apply_global_visibility.ijm";
if (!File.exists(inner))
    exit("Global visibility macro not found beside archive wrapper: " + inner);

runMacro(inner, getArgument());

appDir = getDirectory("home") + ".cautious-rotary-phone" + File.separator;
lastRange = appDir + "last_display_range.txt";
if (!File.exists(lastRange))
    exit("Visibility completed without a saved display range; archive not written.");

lastText = File.openAsString(lastRange);
if (readValue(lastText, "source", "") != sourceTitle)
    exit("Saved display range does not belong to the source image that started this wrapper.");

archiveDir = appDir + "display-ranges" + File.separator;
if (!File.exists(archiveDir))
    File.makeDirectory(archiveDir);

identity = sourceFilename;
if (identity == "")
    identity = sourceTitle;
archiveName = safeFileName(identity) + ".txt";
archiveText = "source_directory=" + sourceDirectory + "\n" +
              "source_filename=" + sourceFilename + "\n" +
              "source_title=" + sourceTitle + "\n" +
              "source_width=" + sourceWidth + "\n" +
              "source_height=" + sourceHeight + "\n" +
              lastText;
File.saveString(archiveText, archiveDir + archiveName);
showStatus("Display range archived for " + identity);

function readValue(text, key, fallback) {
    lines = split(text, "\n");
    prefix = key + "=";
    for (i = 0; i < lines.length; i++) {
        line = replace(lines[i], "\r", "");
        if (startsWith(line, prefix))
            return substring(line, lengthOf(prefix));
    }
    return fallback;
}

function safeFileName(value) {
    value = replace(value, "\\", "-");
    value = replace(value, "/", "-");
    value = replace(value, ":", "-");
    value = replace(value, "*", "-");
    value = replace(value, "?", "");
    value = replace(value, "\"", "");
    value = replace(value, "<", "(");
    value = replace(value, ">", ")");
    value = replace(value, "|", "-");
    return value;
}
