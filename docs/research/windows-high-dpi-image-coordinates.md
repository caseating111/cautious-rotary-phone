# Windows image-canvas coordinates at high DPI

**Endpoint:** pointer marks on a fitted image must resolve to original-image pixels so accepted orientation/crop work can be resumed and reused accurately.

## Evidence and decision

- Failure: a 2047×2047 source reported an 874×1004 boundary measurement and proposed 850×850 despite an expected crop near 1750 pixels.
- Local non-image telemetry showed Windows `AppliedDPI=192` (200%) while Tk 8.6.13 reported 96 pixels/inch. This exact 2× disagreement explains the endpoint failure; Pillow did not resize the source.
- Microsoft documents Per-Monitor-v2 as the current programmatic DPI-awareness context and requires setting it before creating UI/HWNDs. Tk documents `canvasx`/`canvasy` as the supported window-to-canvas coordinate conversion.
- An isolated proof called `SetProcessDpiAwarenessContext(-4)` before `Tk()`: Tk then reported 192 pixels/inch, matching Windows.

## Adopted route

1. Enable Windows Per-Monitor-v2 before the V10 applet creates its Tk root.
2. On Windows, read the pointer in the canvas client area's device-pixel coordinates with the documented `GetCursorPos` + `ScreenToClient` route, then apply the recorded rendered-image scales. Microsoft documents `ScreenToClient` coordinates as device units. If that route is unavailable, reconcile `GetDpiForWindow` against Tk pixels-per-inch before using `canvasx`/`canvasy`.
3. Retain a direct exact-final-side calibration so a user can enter a known crop size without pointer measurement.
4. Resume from accepted project state and existing `2. Cropped/Orientation` outputs; never require orientation replay merely to repair crop calibration.

The first Per-Monitor-v2-only release still produced an exact approximately 2× underestimate in the user's real controller runtime. That showed process awareness alone was not a sufficient guarantee. Direct device-unit client coordinates are now the primary route, and the GUI reports both the coordinate source and DPI ratio with every calibration proposal.

Revisit only if direct `win32_device_pixels` calibration remains incorrect or a mixed-monitor move produces a new mismatch. Prefer a manifest if the application is later packaged as a native executable.
