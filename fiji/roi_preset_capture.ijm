// Capture the current axis-aligned rectangle ROI as the active ROI preset.
// The lightweight Python GUI can import this file and save it as a named preset.

if (nImages() == 0)
    exit("Open an image and draw/select a rectangle ROI first.");

if (selectionType() != 0)
    exit("ROI preset capture currently expects an axis-aligned rectangle ROI.");

Roi.getBounds(x, y, width, height);

presetDir = getDirectory("home") + ".cautious-rotary-phone" + File.separator;
if (!File.exists(presetDir))
    File.makeDirectory(presetDir);

presetFile = presetDir + "active_roi_preset.txt";
text = "width=" + width + "\n" +
       "height=" + height + "\n" +
       "angle=0\n";

File.saveString(text, presetFile);
showStatus("Captured ROI preset: " + width + " x " + height);
print("ROI preset captured to: " + presetFile);