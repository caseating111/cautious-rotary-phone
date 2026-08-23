# Plate crop preprocessing handoff

Status: READY FOR INTEGRATION
Endpoint: Calibrate reusable square crop dimensions (rounded down to 50 px) across similar plates, and place per-image crops using 2 independent anchor clicks (left-edge X anchor and top-edge Y anchor).
Branch: `gemini-plate-crop`
Commit: pending

## What was proven

1. **Four-Boundary Crop-Size Calibration**:
   - 4 boundary points derive square side = `floor(min(w, h) / increment) * increment`.
2. **Default 50 px Floor Rounding**:
   - Side length rounds down to nearest 50 px by default (e.g. 1980 -> 1950, 1999 -> 1950, 2049 -> 2000).
3. **Configurable Rounding Increments**:
   - Supports custom increments (e.g. 10 px, 100 px, 25 px).
4. **Decoupled Size Reuse vs Per-Image Placement**:
   - Image 1 (offset at (120, 80)) and Image 2 (offset at (210, 150)) reuse the same calibration size (1950 px) while yielding distinct per-image crop boxes.
5. **Exact Corner Clicking Not Required**:
   - Left-edge click provides the authoritative $X$ anchor, and top-edge click provides the authoritative $Y$ anchor, anywhere along the respective edge.
6. **Non-Destructive Operations**:
   - Applying crop generates working cropped derivatives in `working/` while preserving raw source image bytes 100% bit-for-bit unchanged.
7. **Placement Retry**:
   - Fast retry of placement anchors does not require recalibrating size.
8. **Size Recalibration**:
   - Explicit recalibration cleanly updates the active `CropSizeCalibration` without corrupting previous records.
9. **State Distinction**:
   - `CropSizeCalibration` (reusable size) and `CropResult` (per-image translation/box) data structures and lifecycles are decoupled.
10. **Invertible Coordinate Transforms**:
    - `transform_point_to_crop` and `transform_point_from_crop_to_source` correctly map spot coordinates between whole-plate and cropped coordinate spaces.
11. **Skip Mode Compatibility**:
    - Skipping crop preprocessing returns `status="SKIPPED"`, allowing downstream four-click grid registration to run directly on the whole plate image without blocking.
12. **Explicit Validation & Error Reporting**:
    - Invalid boundaries or non-positive increments raise descriptive `ValueError`s.

## What was NOT proven

- Fixed-size colony spot cropping (out of scope; owned by colony extraction).
- Automatic culture-grid spot alignment (out of scope; owned by the four-click grid registration applet).

## Public interface

- `calibrate_crop_size(left_pt, right_pt, top_pt, bottom_pt, increment=50, calibration_id=None) -> dict`: Returns `CropSizeCalibration`.
- `place_plate_crop(calibration, left_edge_pt, top_edge_pt, image_geometry=None, inset_offset=(0, 0), options=None) -> dict`: Returns `CropResult`.
- `apply_plate_crop(source_image: Union[str, Any], crop_result: dict, output_path: Optional[str] = None) -> Any`
- `transform_point_to_crop(x, y, crop_result) -> tuple[float, float]`
- `transform_point_from_crop_to_source(crop_x, crop_y, crop_result) -> tuple[float, float]`

## Input contract

- `left_pt`, `right_pt`, `top_pt`, `bottom_pt`: 2-tuples `(x, y)`.
- `left_edge_pt`, `top_edge_pt`: 2-tuples `(x, y)`.
- `calibration`: `CropSizeCalibration` dict.
- `options`: Optional dict (`skip: bool`, `image_uid: str`, `output_path: str`).

## Output contract / Shared schemas used

- `CropSizeCalibration` v1
- `CropResult` v1

## Fixture(s)

- Synthetic generated image files in memory / temporary directories (privacy compliant, image-blind testing).

## Verification command(s)

```powershell
.\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\plate_crop\test_crop.py
# or: python docs/gemini/prototypes/plate_crop/test_crop.py
```

## Verification result

```text
[PASS] test_four_boundary_calibration_square_size
[PASS] test_default_rounding_down_50_px
[PASS] test_configurable_rounding_increment
[PASS] test_two_image_size_reuse_different_offsets
[PASS] test_exact_corners_not_required
[PASS] test_non_destructive_preview_and_apply
[PASS] test_retry_placement_preserves_calibration
[PASS] test_recalibration_replaces_size
[PASS] test_crop_size_and_per_image_state_distinction
[PASS] test_coordinate_transforms
[PASS] test_skip_mode_preserves_four_click_route
[PASS] test_invalid_and_edge_inputs_fail_clearly

ALL 12 PLATE CROP PREPROCESSING PROOF TESTS PASSED.
```

## Dependencies & external software

- Tested & verified runtime: **Python 3.11 (Miniforge Conda `workflow-c` environment)** and **Python 3.14**
- Python standard library (`math`, `os`, `shutil`, `typing`, `tempfile`) + `Pillow`
- External software/plugins required: None.

## Known limitations

- Only rectangular/square crops are supported.

## Failed / abandoned routes relevant to integration

- *Colony ROI 108x108 plugin*: Discarded for whole-plate crop because it is designed for spot-level measurement rather than physical plate bounding boxes.
- *Forcing top-left corner clicking*: Discarded in favor of independent left-edge X and top-edge Y clicks because identifying exact plate corners on rounded Petri dishes is difficult and error-prone.

## Human / manual validation still required

- None for calibration math and image cropping. Visual QC of crop placement is available in the interactive GUI preview.

## Files the integrator should inspect

- `docs/gemini/prototypes/plate_crop/crop.py`: Core crop calibration and placement module.
- `docs/gemini/prototypes/plate_crop/test_crop.py`: 12 unit tests covering boundary calculations, rounding, placement, and transforms.

## Files the integrator normally should NOT need to inspect

- Synthetic temp fixtures.

## Recommended integration / adaptation

- Can be imported directly by CLI or GUI controller:
  ```python
  from crop import calibrate_crop_size, place_plate_crop, apply_plate_crop
  
  # Step 1: Calibrate size once
  calib = calibrate_crop_size(left_pt, right_pt, top_pt, bottom_pt)
  
  # Step 2: Place per-image crop
  res = place_plate_crop(calib, left_edge_pt, top_edge_pt, options={"image_uid": "IMG_01"})
  
  # Step 3: Apply non-destructive crop
  cropped_path = apply_plate_crop("working/plate_straight.jpg", res, output_path="working/plate_crop.jpg")
  ```

## Contract changes proposed

- None. Conforms to `docs/development/PROJECT_ASSET_CONTRACT.md`.
