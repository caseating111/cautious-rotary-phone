# Global visibility slice

`fiji/apply_global_visibility.ijm` uses the accepted `last_alignment.txt` geometry.

- background: median from each top/bottom/left/right strip immediately outside the total-grid bounds, then median-of-side-medians;
- white/high point: configurable percentile (default 99.5%) from the tilted total-grid quadrilateral;
- one resulting black/high range is applied uniformly to the whole displayed image;
- values are persisted to `~/.cautious-rotary-phone/last_display_range.txt`.

For 8/16/32-bit grayscale, ImageJ `setMinAndMax()` changes display range only. For RGB, ImageJ documents that `setMinAndMax()` alters pixels, so the macro creates an 8-bit `QC - ...` duplicate and adjusts that instead; the original RGB source stays open and untouched.

This remains a QC/display path only. Quantitative scoring should continue from unmodified source pixels.