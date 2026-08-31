# Windows image-canvas coordinates at high DPI

**Endpoint:** pointer marks on a fitted image must resolve to original-image pixels on single- and mixed-DPI Windows displays, without distorting the app UI.

## Current decision

Tk 8.6.13 is not treated as a Per-Monitor-v2 UI. Windows is allowed to scale the complete legacy Tk window uniformly. Pointer positions are converted to fractions of the live native canvas client rectangle, then those fractions are applied to the current Tk canvas geometry and rendered-image transform. This bridges device and logical coordinate domains without guessing a DPI multiplier.

The same normalized mapping is used by the project and Quick Figures canvases. Exact numeric crop sizes remain available, and accepted orientation/crop state remains resumable.

## Official and mature evidence

- Tk's own Windows tracker states Tk 8.6 is manifested system-DPI-aware rather than per-monitor-aware and records mixed-scale monitor pointer problems: <https://core.tcl-lang.org/tk/tktview/bee96b4e80c5c26763a0a09be4e57f41a1473386>.
- Tk documents that changing `tk scaling` does not guarantee existing widgets will resize dynamically: <https://www.tcl-lang.org/man/tcl8.6/TkCmd/tk.htm>.
- A current Tk Per-Monitor-v2 ticket records DPI-dependent double-scaling/native-theme defects: <https://core.tcl-lang.org/tk/tktview/a05a17866d4610341ca453c68883eccec310ce0d>.
- Microsoft documents system scaling for DPI-unaware/system-aware windows and device-unit client coordinates: <https://learn.microsoft.com/en-us/windows/win32/hidpi/dpi-awareness-context> and <https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-screentoclient>.
- Fiji/ImageJ ROI bounds are a mature source-pixel alternative, but the user explicitly prefers to avoid switching applications for whole-plate cropping. It is not the production route.

Meaningful searches on 2026-09-01 included:

- `scientific image viewer select crop rectangle original pixel coordinates regardless of zoom desktop software`
- `Tk 8.6 Windows per monitor DPI scaling mixed monitors official`
- `current recommended high DPI pointer coordinates Win32 per monitor v2 client coordinates`
- `DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED recommended mixed monitor legacy desktop app`

## Endpoint debugging / failure history

1. **Raw Tk event coordinates plus fitted-image scale — ruled out.**
   - A 2047×2047 source produced approximately 874×1004 measured bounds and an 850×850 proposal where the real plate was near 1750 pixels.
   - The resulting 850-pixel crop covered only about one quarter of the intended image area.
   - Lesson: arithmetic using only Tk event/render values was not proven to share one coordinate domain on the real 200% display.

2. **Force Per-Monitor-v2 before Tk — ruled out.**
   - A clean synthetic process made Tk and Windows both report 192 DPI, but the real calibration remained half-scale.
   - Moving the app between a 4K and roughly 1920-pixel monitor caused oversized text and broken UI scaling.
   - Lesson: process awareness telemetry did not prove Tk 8.6 rendered/event geometry was per-monitor-correct; forcing this unsupported posture created a visible regression.

3. **Direct Win32 pointer device coordinates combined with Tk offsets/scales — ruled out.**
   - Single-monitor synthetic API round trips passed, but the real four-click calibration still returned the same wrong size with either one monitor or both monitors connected.
   - The proof derived its target from Tk geometry and inverted the same Win32 APIs, so it did not prove a human-visible target shared that geometry.
   - Lesson: device coordinates cannot be mixed directly with Tk-derived geometry, and a self-consistent API round trip is insufficient endpoint evidence.

4. **Normalized live-client fractions with Windows-managed Tk scaling — active.**
   - `GetCursorPos`/`ScreenToClient` and `GetClientRect` remain within one native client domain; only their ratio crosses into Tk.
   - A factor-2 synthetic proof shows identical fractions for 820×560 logical and 1640×1120 physical client spaces.
   - A clean-process 2047×2047 pointer round trip passes within two source pixels without Per-Monitor-v2.
   - With both current displays connected (`DISPLAY1` and `DISPLAY9`), an invisible synthetic 2047×2047 canvas was placed on each display at 900×650 and 1120×780 window sizes. All four runs used `normalized_win32_client`, mapped within 1.18 source pixels, measured approximately 1749–1752 pixels, and proposed 1750 after accounting for at most one displayed pixel of quantization.
   - Human visual confirmation remains limited to UI proportion and real click placement; numeric cross-monitor mapping is automated and passing.

## Smallest next proof

On the new build, use one private real image locally: record the calibration line on the 4K monitor, move the same window to the second monitor and repeat, then repeat once with only the 4K monitor. Expected measured source-pixel bounds must remain stable and the UI must remain proportionate. This is the remaining human-visible check after the automated two-display synthetic proof. No image pixels need to leave the machine.
