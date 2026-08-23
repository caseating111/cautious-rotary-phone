# Grid/layout derivation prototype handoff

Status: READY FOR INTEGRATION
Endpoint: Derive canonical PlateLayout v1 from normalized V10 project metadata or specification dictionaries without image pixels or Fiji dependencies.
Branch: `gemini-layout`
Commit: pending

## What was proven

1. **8x12 Single-Band Derivation**:
   - Vertical profile positions 1–8 determine `grid_rows=8`.
   - Strain profile positions 1–12 determine `grid_cols=12`.
   - 1 strain band spanning all 8 physical rows with distinct column positions 1..12.
2. **8x10 Two-Band Even Row Allocation**:
   - `Order=1` maps upper strain band to rows 1–4.
   - `Order=2` maps lower strain band to rows 5–8.
   - Overall grid width remains 10 columns without multiplying or distorting geometry.
3. **Manual / Explicit Row-Band Overrides**:
   - Explicit `row_band_overrides` (e.g. rows 1–2 for Band 1, rows 3–8 for Band 2) cleanly override default even splitting without altering column labels.
4. **Widest-Band-Wins Global Column Width**:
   - When strain bands have unequal widths (e.g. Band 1 width 10, Band 2 width 4), overall `grid_cols` is set to 10 (max width).
5. **Preservation of Local vs Global Dimensions**:
   - Shorter bands retain their local occupied column count (4 labels) without padding or shrinking the global grid.
6. **Pos Authority & Repeated Labels**:
   - Vertical labels with repeated display values (e.g. `0, -1, -2, -3, 0, -1, -2, -3`) produce distinct physical rows indexed 1..8 based strictly on `Pos`.
7. **Explicit Validation & Error Reporting**:
   - Ambiguous row splits (e.g. 7 rows across 2 bands without override), duplicate within-band `Pos` values, overlapping row allocations, or missing labels raise descriptive `ValueError`s rather than silently guessing.
8. **Schema Conformance**:
   - Validated strictly against `contracts/plate_layout.schema.json` v1.

## What was NOT proven

- Multiple vertical profiles per annotation set (out of scope for current workflow).
- Out-of-scope `other` annotation profiles (ignored).

## Public interface

- `derive_plate_layout(project_or_path: Union[dict, str], image_uid: Optional[str] = None, layout_id: Optional[str] = None, row_band_overrides: Optional[Any] = None) -> dict`: Returns `PlateLayout` v1 dict.
- `derive_plate_layout_from_spec(layout_id: str, vertical_labels: list[dict], strain_bands_spec: list[dict], row_band_overrides: Optional[list] = None) -> dict`: Derives `PlateLayout` v1 from raw specification lists.
- `validate_plate_layout(layout: dict) -> bool`: Validates dictionary against `plate_layout.schema.json` v1.

## Input contract

- `project_model` dictionary or path to V10 Excel workbook (`.xlsm` / `.xlsx`).
- Optional `image_uid` or `layout_id` string locator.
- Optional `row_band_overrides` list of `(row_start, row_end)` tuples.

## Output contract / Shared schemas used

- `contracts/plate_layout.schema.json` (version 1)

## Fixture(s)

- `fixtures/v10/v10_sample_synthetic_sanitized.xlsx`

## Verification command(s)

```powershell
.\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\layout\test_derive_layout.py
# or: python docs/gemini/prototypes/layout/test_derive_layout.py
```

## Verification result

```text
[PASS] test_single_profile_8x12
[PASS] test_two_profile_8x10_even_split
[PASS] test_manual_row_band_override
[PASS] test_widest_band_wins_overall_cols
[PASS] test_unequal_band_widths_local_vs_global
[PASS] test_repeated_vertical_labels_distinct_pos
[PASS] test_ambiguous_and_invalid_inputs_fail_clearly
[PASS] test_contract_schema_conformance

ALL 8 PLATE LAYOUT DERIVATION PROOF TESTS PASSED.
```

## Dependencies & external software

- Tested & verified runtime: **Python 3.11 (Miniforge Conda `workflow-c` environment)** and **Python 3.14**
- Python standard library (`os`, `sys`, `typing`)
- Internal dependency: `docs/gemini/prototypes/v10/adapter.py`
- External software/plugins required: None.

## Known limitations

- Only single vertical profile per annotation set is supported (current contract standard).

## Failed / abandoned routes relevant to integration

- Inferring row count from unique label strings: Discarded because repeated dilution labels (`0, -1, -2, -3`) represent multiple distinct physical rows.
- Summing column widths across multi-band strain profiles: Discarded because bands represent top-to-bottom row splits, not side-by-side columns.

## Human / manual validation still required

- None for logical layout derivation. Downstream visual validation applies when rendering annotations onto images.

## Files the integrator should inspect

- `docs/gemini/prototypes/layout/derive_layout.py`: Core standalone PlateLayout derivation module.
- `docs/gemini/prototypes/layout/test_derive_layout.py`: 8 unit tests covering all required single, multi-band, override, and edge cases.
- `contracts/plate_layout.schema.json`: PlateLayout v1 schema.

## Files the integrator normally should NOT need to inspect

- `fixtures/v10/`: Test fixtures.

## Recommended integration / adaptation

- `derive_layout.py` can be imported directly by downstream applets (`annotation`, `visibility_adjustment`, `crops`, `controller`):
  ```python
  from derive_layout import derive_plate_layout
  
  layout = derive_plate_layout(project_model, image_uid="E1_14.08.26_24h_I001")
  ```

## Contract changes proposed

- None. Strictly conforms to `plate_layout.schema.json` v1.
