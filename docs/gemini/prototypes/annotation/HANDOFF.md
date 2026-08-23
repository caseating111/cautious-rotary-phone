# Annotation/composition prototype handoff

Status: READY FOR INTEGRATION
Endpoint: Automatically position and render strain/vertical annotations onto whole plates using registered spot coordinates and PlateLayout, and compose multi-crop matrices with mixed crop-tier support headlessly without Photoshop.
Branch: `gemini-annotation`
Commit: pending

## What was proven

1. **Automatic 8x12 Whole-Plate Annotation**:
   - 8 vertical row labels and 12 strain column labels position automatically from measured grid coordinates without manual repositioning.
2. **Automatic 8x10 Two-Strain-Band Annotation**:
   - Band 1 strain labels position above row 1; Band 2 strain labels position above row 5.
3. **Repeated Vertical Labels Mapped by Physical Row Pos**:
   - Dilution labels `['0', '-1', '-2', '-3', '0', '-1', '-2', '-3']` map to distinct, increasing $Y$ coordinates corresponding to physical rows 1..8.
4. **90-Degree Clockwise Strain Label Rotation**:
   - Strain text rotated 90 degrees clockwise with text facing right as default presentation preset.
5. **Non-Destructive In-Memory Preview**:
   - `render_plate_annotation` previews layout changes in memory without modifying source files or writing to disk.
6. **Deterministic Metadata Headers**:
   - Date, plate, media, condition, and session headers render cleanly along configured top margins.
7. **Matrix Composition with Structured Headers**:
   - `compose_matrix` tiles individual colony crops into clean matrices with row and column headers.
8. **Mixed Crop-Tier Matrix Selection**:
   - Different strains/conditions can use different crop tiers (e.g. `top` and `low`) in the same composite image.
9. **Bit-for-Bit Non-Destructive Integrity**:
   - Source image files remain 100% untouched when saving annotated output.
10. **Headless Python/Pillow Execution**:
    - Entire rendering and composition pipeline runs headlessly without GUI / windowing dependencies.
11. **Strict Contract Schema Conformance**:
    - Conforms to `contracts/annotation_request.schema.json` v1.

## What was NOT proven

- Interactive GUI dragging of individual label boxes (manual override fallback).

## Public interface

- `derive_annotation_positions(plate_layout, grid_coordinates, preset=None) -> dict`
- `render_plate_annotation(source_image, plate_layout, grid_coordinates, annotation_request=None, preset=None, output_path=None) -> dict`
- `compose_matrix(crop_items: list[dict], matrix_layout: dict, output_path: Optional[str] = None) -> dict`
- `DEFAULT_ANNOTATION_PRESET`: Standard 90-degree rotated strain preset.

## Input contract

- `plate_layout`: `PlateLayout` v1 dict.
- `grid_coordinates`: `{(r, c): (x, y)}` or list of `(x, y)` tuples.
- `annotation_request`: Conforming to `contracts/annotation_request.schema.json` v1.
- `preset`: Optional preset dict.

## Output contract / Shared schemas used

- `contracts/annotation_request.schema.json` (version 1)
- `contracts/plate_layout.schema.json` (version 1)

## Fixture(s)

- Synthetic generated image files in memory / temporary directories (privacy compliant, image-blind testing).

## Verification command(s)

```powershell
.\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\annotation\test_annotate.py
# or: python docs/gemini/prototypes/annotation/test_annotate.py
```

## Verification result

```text
[PASS] test_automatic_8x12_whole_plate_annotation
[PASS] test_automatic_8x10_two_strain_band_annotation
[PASS] test_repeated_vertical_labels_distinct_pos
[PASS] test_strain_labels_rotated_90deg_clockwise_preset
[PASS] test_fast_non_destructive_preview
[PASS] test_deterministic_metadata_headers
[PASS] test_matrix_composition_with_structured_labels
[PASS] test_mixed_crop_tier_matrix_support
[PASS] test_source_image_non_destructive_integrity
[PASS] test_headless_callable_interface
[PASS] test_contract_schema_conformance

ALL 11 ANNOTATION AND MATRIX COMPOSITION PROOF TESTS PASSED.
```

## Dependencies & external software

- Tested & verified runtime: **Python 3.11 (Miniforge Conda `workflow-c` environment)** and **Python 3.14**
- Python standard library (`json`, `math`, `os`, `shutil`, `typing`, `tempfile`) + `Pillow`
- External software/plugins required: None.

## Known limitations

- Custom font file paths default to standard sans-serif system fallback if TrueType font file is missing.

## Failed / abandoned routes relevant to integration

- *Photoshop-style manual text templates*: Discarded because automatic grid-derived coordinate mapping eliminates manual template alignment overhead.

## Human / manual validation still required

- Visual check of font sizes and aesthetics on real plate crops.

## Files the integrator should inspect

- `docs/gemini/prototypes/annotation/annotate.py`: Core annotation and matrix composition module.
- `docs/gemini/prototypes/annotation/test_annotate.py`: 11 unit tests.
- `contracts/annotation_request.schema.json`: Schema governing `AnnotationRequest` v1.

## Files the integrator normally should NOT need to inspect

- Synthetic temp fixtures.

## Recommended integration / adaptation

- Can be imported directly by controller or standalone applet:
  ```python
  from annotate import render_plate_annotation, compose_matrix
  
  # Annotate whole plate
  res = render_plate_annotation("processed/plate.png", layout, grid_coords, req, output_path="annotated/plate.png")
  
  # Compose matrix
  comp = compose_matrix(crop_list, matrix_cfg, output_path="compositions/matrix_24h.png")
  ```

## Contract changes proposed

- None. Conforms to `annotation_request.schema.json` v1.
