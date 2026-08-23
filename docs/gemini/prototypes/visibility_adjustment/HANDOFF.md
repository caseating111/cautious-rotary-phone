# Visibility adjustment / manual-review preprocessing handoff

Status: READY FOR INTEGRATION
Endpoint: Calculate robust background black point from outside-grid margin and foreground white point from inside-grid ROI, applying a whole-plate visibility enhancement for visual inspection, with fast approve or manual-review queue flagging.
Branch: `gemini-visibility-adjustment`
Commit: `f068a55`

## What was proven

1. **Grid-Guided Foreground ROI**:
   - Spot coordinates derive a padded bounding box bounding only the culture spots for accurate foreground statistics.
2. **Outside-Grid Background Isolation**:
   - Border annulus around the grid ROI samples true dish background, preventing colony density from distorting the black point.
3. **Whole-Plate Visibility Transform**:
   - Contrast/stretch and gamma curve apply to the entire image for global visual consistency.
4. **Non-Destructive Operations**:
   - Raw source images remain 100% bit-for-bit unchanged; processed images are saved in `processed/`.
5. **Approve Workflow**:
   - `status="APPROVED"` calculates and logs reproducible parameters (`black_point`, `white_point`, `gamma`).
6. **Manual-Review Queue Integration**:
   - `status="MANUAL_REVIEW"` flags difficult images and logs them to a persistent `ReviewQueue` without crashing or blocking batch progression.
7. **Queue Lifecycle**:
   - `ReviewQueue` supports add, inspect pending, and mark reviewed operations.
8. **Reusable Presets**:
   - Supports `background_aware_linear`, `gamma_boost`, `high_contrast_clahe`, and custom preset dictionaries.
9. **Geometric Invariance**:
   - Intensity-only adjustments preserve image width, height, and coordinates, allowing existing `GridCoordinateAsset`s to be reused directly for processed crop exports without realignment.
10. **Folder Structure Preservation**:
    - Image UID and relative folder paths are preserved.

## What was NOT proven

- Quantitative pixel measurement (out of scope; presentation adjustments are strictly for human QC/inspection).
- Four-click grid alignment (out of scope; consumed as an input).

## Public interface

- `calculate_grid_roi(grid_coordinates: list[tuple[float, float]], padding: float = 20.0, max_width=None, max_height=None) -> dict`
- `compute_visibility_statistics(image_array, grid_roi, margin=50.0) -> dict`
- `adjust_plate_visibility(source_image: Union[str, Any], grid_coordinates: list[tuple[float, float]], preset=None, options=None) -> dict`: Returns `AdjustmentResult`.
- `apply_visibility_adjustment(source_image: Union[str, Any], adjustment_result: dict, output_path: Optional[str] = None) -> Any`
- `ReviewQueue`: Class managing persistent JSON manual-review queue.

## Input contract

- `source_image`: Path or image array.
- `grid_coordinates`: List of `(x, y)` float tuples from registered grid.
- `preset`: Preset name string or dict.
- `options`: Optional dict (`image_uid`, `status`, `manual_review_reason`, `output_path`).

## Output contract / Shared schemas used

- `AdjustmentResult` (conforming to `docs/development/PROJECT_ASSET_CONTRACT.md`)

## Fixture(s)

- Synthetic generated image files in memory / temporary directories (privacy compliant, image-blind testing).

## Verification command(s)

```powershell
.\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\visibility_adjustment\test_visibility.py
# or: python docs/gemini/prototypes/visibility_adjustment/test_visibility.py
```

## Verification result

```text
[PASS] test_saved_grid_derives_foreground_roi
[PASS] test_outside_grid_derives_robust_background_stats
[PASS] test_display_transform_applies_to_entire_image
[PASS] test_non_destructive_preview_and_apply
[PASS] test_approve_saves_processed_output
[PASS] test_mark_for_manual_creates_review_queue_entry
[PASS] test_review_queue_persistence_and_resolution
[PASS] test_presets_reusability
[PASS] test_processed_crop_integration_geometry_invariance
[PASS] test_subfolder_and_uid_identity_preservation

ALL 10 VISIBILITY ADJUSTMENT PROOF TESTS PASSED.
```

## Dependencies & external software

- Tested & verified runtime: **Python 3.11 (Miniforge Conda `workflow-c` environment)** and **Python 3.14**
- Python standard library (`json`, `math`, `os`, `shutil`, `typing`, `tempfile`) + `Pillow` + `numpy`
- External software/plugins required: None.

## Known limitations

- For human visual inspection only; not for quantitative densitometry.

## Failed / abandoned routes relevant to integration

- *Using 2x CLAHE alignment settings as the final presentation image*: Discarded because extreme CLAHE parameters optimize spot boundary detection for clicking rather than clean visual colony presentation.
- *Blocking batch on difficult images*: Discarded in favor of an asynchronous `ReviewQueue` so difficult images can be examined later without stopping the batch.

## Human / manual validation still required

- Visual aesthetic check on real plate series when adjusting presentation presets.

## Files the integrator should inspect

- `docs/gemini/prototypes/visibility_adjustment/visibility.py`: Core visibility adjustment and review queue module.
- `docs/gemini/prototypes/visibility_adjustment/test_visibility.py`: 10 unit tests.

## Files the integrator normally should NOT need to inspect

- Synthetic temp fixtures.

## Recommended integration / adaptation

- Can be called directly in batch processing:
  ```python
  from visibility import adjust_plate_visibility, apply_visibility_adjustment, ReviewQueue
  
  res = adjust_plate_visibility("working/plate.png", grid_spots, preset="background_aware_linear", options={"image_uid": "IMG_01"})
  if res["needs_manual_review"]:
      ReviewQueue("project/review_queue.json").add_entry(res["image_uid"], "working/plate.png", res["manual_review_reason"])
  else:
      apply_visibility_adjustment("working/plate.png", res, output_path="processed/plate.png")
  ```

## Contract changes proposed

- None. Conforms to `docs/development/PROJECT_ASSET_CONTRACT.md`.
