# Whole-plate orientation prototype handoff

Status: READY FOR INTEGRATION
Endpoint: One straight-line drag along a long top or bottom physical plate edge calculates observed tilt and applies a non-destructive counter-rotation transform to produce a straightened working plate image.
Branch: `gemini-plate-rotation`
Commit: pending

## What was proven

1. **Modest Clockwise Tilt Straightening**:
   - Line with positive downward slope (e.g. $(100, 100) \rightarrow (1000, 150)$, $+3.18^\circ$) produces exact counter-clockwise correction angle.
   - Point transform around center maps both line endpoints to identical $y'$ coordinates (horizontal line).
2. **Modest Counter-Clockwise Tilt Straightening**:
   - Line with negative upward slope (e.g. $(100, 150) \rightarrow (1000, 100)$, $-3.18^\circ$) produces exact clockwise correction angle.
3. **Near-Zero Tilt**:
   - A horizontal edge line produces an exact $0.0^\circ$ correction.
4. **Top and Bottom Edge Equivalence**:
   - Top-edge lines and bottom-edge lines with the same physical slope yield identical correction angles, removing the need for separate dialogue branches.
5. **Non-Destructive Preview and Application**:
   - Applying orientation generates a rotated working derivative in `working/` while preserving raw source image bytes 100% bit-for-bit unchanged.
6. **Point Transformation for Downstream Coordinates**:
   - `transform_point_around_center` maps coordinates between raw and straightened coordinate spaces so downstream crop/grid tools can consume them accurately.
7. **Per-Image Isolation**:
   - Orientation transforms remain strictly per-image and do not pollute or assume crop translations for other images.
8. **Skip Mode Compatibility**:
   - Skipping orientation returns `angle_degrees=0.0` with `status="SKIPPED"` and `needs_manual_review=False`, allowing four-click grid registration to proceed immediately without blocking.
9. **Strict Schema Conformance**:
   - Outputs validate strictly against `contracts/rotation_result.schema.json` v1.

## What was NOT proven

- Culture-grid spot alignment (out of scope; owned by the four-click grid registration applet).
- Whole-plate bounding box cropping (out of scope; owned by `plate_crop` mini-app).

## Public interface

- `compute_line_angle(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]`
- `transform_point_around_center(x: float, y: float, cx: float, cy: float, angle_degrees: float) -> tuple[float, float]`
- `capture_plate_orientation(line: Optional[Union[dict, tuple, list]] = None, image_geometry: Optional[dict] = None, options: Optional[dict] = None) -> dict`: Returns `OrientationResult` conforming to `rotation_result.schema.json` v1.
- `apply_plate_orientation(source_image: Union[str, Any], orientation_result: dict, output_path: Optional[str] = None) -> Any`

## Input contract

- `line`: Line endpoints dictionary `{'x1': float, 'y1': float, 'x2': float, 'y2': float}` or 4-tuple `(x1, y1, x2, y2)`.
- `image_geometry`: Optional dict with `width`, `height`, `image_uid`.
- `options`: Optional dict (`skip: bool`, `method: str`, `edge_used: str`).

## Output contract / Shared schemas used

- `contracts/rotation_result.schema.json` (version 1)

## Fixture(s)

- Synthetic generated image files in memory / temporary directories (privacy compliant, image-blind testing).

## Verification command(s)

```powershell
.\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\plate_rotation\test_orientation.py
# or: python docs/gemini/prototypes/plate_rotation/test_orientation.py
```

## Verification result

```text
[PASS] test_modest_clockwise_tilt
[PASS] test_modest_counter_clockwise_tilt
[PASS] test_near_zero_tilt
[PASS] test_top_and_bottom_edge_equivalence
[PASS] test_non_destructive_preview_and_apply
[PASS] test_coordinate_transform_for_downstream_use
[PASS] test_per_image_isolation
[PASS] test_skip_mode_preserves_four_click_compatibility
[PASS] test_contract_schema_conformance

ALL 9 WHOLE-PLATE ORIENTATION PROOF TESTS PASSED.
```

## Dependencies & external software

- Tested & verified runtime: **Python 3.11 (Miniforge Conda `workflow-c` environment)** and **Python 3.14**
- Python standard library (`math`, `os`, `shutil`, `typing`, `tempfile`) + `Pillow`
- External software/plugins required: None.

## Known limitations

- Extreme 90/180/270 degree whole-image upside-down orientations should be handled by orientation pre-check rather than fine edge straightening.

## Failed / abandoned routes relevant to integration

- *ROI 1-click rotated-rectangle / 108x108 colony plugin*: Discarded for whole-plate orientation because it solves colony-level spot extraction rather than macroscopic physical dish straightening.
- *Two-click point mode with prompt*: Discarded in favor of a single continuous straight-line drag tool.

## Human / manual validation still required

- None for angle math and non-destructive image rotation. Users interact via one line drag in GUI/Fiji when running the interactive applet.

## Files the integrator should inspect

- `docs/gemini/prototypes/plate_rotation/orientation.py`: Core orientation measurement, point transformation, and image straightening module.
- `docs/gemini/prototypes/plate_rotation/test_orientation.py`: 9 unit tests covering tilt angles, point transformation, non-destructive file operations, and schema validation.
- `contracts/rotation_result.schema.json`: Schema governing `RotationResult` v1.

## Files the integrator normally should NOT need to inspect

- Synthetic temp fixtures.

## Recommended integration / adaptation

- Can be imported directly by CLI or GUI controller, or called within an interactive line-drag tool:
  ```python
  from orientation import capture_plate_orientation, apply_plate_orientation
  
  res = capture_plate_orientation(line=(x1, y1, x2, y2), image_geometry={"width": w, "height": h})
  straightened_path = apply_plate_orientation("raw/plate.jpg", res, output_path="working/plate_straight.jpg")
  ```

## Contract changes proposed

- None. Strictly conforms to `rotation_result.schema.json` v1.
