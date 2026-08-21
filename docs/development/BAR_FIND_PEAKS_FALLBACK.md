# BAR Find Peaks fallback

Status: researched and ready as the **first fallback**, but deliberately **not integrated** unless representative real-plate validation shows the native `Array.findMaxima()` route is unreliable.

## Why BAR first
BAR **Find Peaks** is an established ImageJ/Fiji script distributed through the BAR update site. It operates on ImageJ plots, supports peak-amplitude and minimum-distance filtering, handles flat-topped peaks at their centers, and is explicitly callable from ImageJ macros/scripts.

This fits the existing composed route: keep the manually authoritative whole-column ROI and ImageJ native wide-line profile, then substitute only the peak-selection step if needed.

## Installation
In Fiji: **Help -> Update... -> Manage update sites -> BAR**, apply changes and restart.

Do not add a Python detector or bundle another peak library merely to avoid this normal Fiji update-site dependency.

## Proven macro-call shape
ImageJ's BAR documentation gives this macro form:

```ijm
run("Find Peaks", "min._peak_amplitude=35 min._peak_distance=0 min._value=NaN max._value=NaN list");
```

The `list` option exposes the plot values table for programmatic access. BAR reports original data plus maxima/minima coordinates; maxima are ordered by peak strength.

## Intended narrow adaptation if native maxima fails
1. Keep the current first/last whole-column rectangle interaction.
2. Keep current native wide-line `getProfile()` averaging.
3. Create/use an ImageJ plot from that 1-D profile.
4. Run BAR **Find Peaks** with a minimum peak distance informed by expected row spacing and a modest amplitude threshold.
5. Read the returned maxima coordinates, take the expected number of row peaks, sort by X/row position, and continue through the existing grid interpolation + full-grid QC.
6. Preserve retry and the original four-point fallback.

## Stop-loss
Do **not** implement this pre-emptively. First perform the one representative desktop test in `MINIMAL_DESKTOP_VALIDATION.md`.

If native `Array.findMaxima()` succeeds on representative plates, keep the simpler dependency-free native route. If it fails after one sensible ROI reposition/retry, test BAR before changing tolerance heuristics further or writing custom detection code.
