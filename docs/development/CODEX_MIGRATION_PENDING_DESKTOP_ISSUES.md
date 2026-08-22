# Codex migration — pending desktop issues

Documentation-only checkpoint. **Do not treat this file as authorization to implement fixes yet.** The user is still collecting issues before migrating the active work to Codex.

## Desktop test state — 2026-08-22

The current one-plate four-point proof reaches the real Fiji interaction and the four ROI 1-click placements, but the desktop route is not yet working end-to-end.

### 1. Fiji main GUI/window sizing and placement is still unstable

Observed after the recent program-side visibility rescue:

- Fiji/ImageJ can initially appear as an **extremely small/minimal window**, effectively just a tiny title bar/window chrome rather than the usable normal toolbar GUI.
- After cancelling out of alignment, the main `(Fiji Is Just) ImageJ` toolbar can appear in the corner at a more normal size, but its placement is inconsistent.
- Sometimes the Fiji toolbar is partly or wholly off-screen by default; sometimes it is not.
- Therefore the latest Python-side Win32 visibility/position rescue has **not** solved the real desktop behavior reliably.
- Do not assume that merely finding/restoring/moving the top-level Fiji frame guarantees that Java/AWT has finished sizing/layout of the main toolbar.
- AHK v2 remains a convenience layer and must not become the sole mechanism by which Fiji exists/appears, but current program-side positioning is still not reliable enough.

### 2. Placement/confirmation dialogs are no longer being moved upper-left reliably

The four placement dialogs (`1 / 4 — R1C1`, etc.) are appearing large/centrally positioned rather than being moved to the intended upper-left location.

This is a regression relative to the desired AHK v2 behavior. Current AHK design is shell-hook based with one ~120 ms catch-up pass and no permanent polling. Before changing it, inspect whether:

- the Java dialog title is assigned later than the one delayed pass;
- title matching is affected by the rendered title/encoding (desktop showed text similar to `1 / 4 â R1C1` rather than a clean en-dash title);
- the window is created/reparented/resized again after the shell event;
- or the helper is not running/receiving the expected shell event at that point.

Do not blindly return to continuous polling unless desktop evidence requires it.

### 3. Macro parse error after the fourth point blocks QC/export

After successfully placing all four authoritative points and confirming the fourth placement, Fiji reports:

`Error: ';' expected in line 388`

at generated macro code equivalent to:

`halfW = QC_W / 2;`

The debug window shows `halfW` already present as `"108"`, and the parser highlights the division operator. This is a generated ImageJ-macro-language problem and must be diagnosed before QC can run.

Important values immediately before the failure:

- `viewW = 1750`
- `viewH = 1750`
- `roiBoxW = "108"`
- `roiBoxH = "108"`
- `roiBoxSize = 108`
- `QC_W = "108"`
- `QC_H = "108"`
- `gridCols = 12`
- `R1LX = 122`, `R1LY = 540`
- `R1RX = 1558`, `R1RY = 480`
- `R5LX = 142`, `R5LY = 1062`
- `R5RX = 1582`, `R5RY = 1002`
- `gridHX = 1438`, `gridHY = -60`
- `gridVX = 22`, `gridVY = 522`
- `hLen = 1439.2512`
- `vLen = 522.4634`
- `hux = 0.9991`, `huy = -0.0417`
- `vux = 0.0421`, `vuy = 0.9991`

The four-point geometry itself therefore appears to have been calculated sensibly before the parse failure.

Likely investigation area for Codex: `QC_W`/`QC_H` are coming from `call("ij.Prefs.get", ...)` and appear in the debug window as quoted string-like values (`"108"`), whereas `roiBoxSize` became numeric through `maxOf`. The generated ImageJ macro must use unambiguous numeric values before arithmetic. Do not implement this inference yet without inspecting the exact generated macro around line 388.

### 4. CLAHE settings now appear correctly encoded in the generated runtime state

The debug output from this failed run is useful positive evidence. It shows:

- `roiBoxW = "108"`
- `roiBoxH = "108"`
- `roiBoxSize = 108`
- `claheBlock = 356`
- `claheOptions = "blocksize=356 histogram=256 maximum=1000 mask=*None* fast_(less_accurate)"`

This matches the user's requested current settings closely:

- block size approximately 3.3× the one-click ROI dimension; 108 × 3.3 gives ~356 (user described ~355 and requires >3×);
- histogram bins 256;
- maximum slope 1000;
- mask None;
- Fast / less accurate enabled.

The previous issue where CLAHE looked unlike the intended settings should not be assumed to be an option-string mismatch based on this debug state. Whole-image application still matters; the current generated proof explicitly clears an ROI before the CLAHE calls.

### 5. ROI 1-click tool selection worked in this run

Positive evidence from the debug output:

- `roiToolsetPath` resolves to the installed `Roi 1-Click Tools.ijm`;
- `roiClickToolFound = 1`;
- `toolCandidate = 17`;
- all four clicked ROI bounds were 108 × 108.

So automatic discovery/selection of the custom ROI 1-click Rotated Rectangle Click Tool appears to have worked in this desktop run.

### 6. Four-point interaction itself reached all four placements

The user successfully placed:

- R1C1;
- R1C(last);
- R5C1;
- R5C(last).

The failure happened **after** the fourth placement when generated QC geometry code began. Do not regress or replace the authoritative four-point interaction while addressing the later failure.

## Current migration posture

- Do **not** fix these issues yet; the user has more issues to report before migration.
- Preserve the current code and evidence until the user says to begin implementation/Codex migration.
- When migration begins, Codex should read `AGENTS.md`, `docs/development/IMPLEMENTATION_DECISION_POLICY.md`, `docs/development/CURRENT_STATE.md`, and this file first.
- Runtime target remains Windows + Python 3.14.
- AutoHotkey requirement remains **AHK v2 only**; no AHK v1 compatibility is needed.
- Continue to prefer the mature four-point Fiji + ROI 1-click route rather than returning to detector development.
- Fix desktop failures narrowly and verify the generated ImageJ macro itself before asking the user for another test.
