# V10 adapter prototype handoff

Status: READY FOR INTEGRATION
Endpoint: Read-only V10 workbook adapter producing canonical ProjectModel v1, PlateLayout v1 derivation, file reconciliation and legacy projections.
Branch: `gemini-v10`
Commit: `0c654d1`

## What was proven

1. **Read-only Workbook Parsing**:
   - Parses `.xlsm` and `.xlsx` workbooks directly using `pandas` with `openpyxl` engine without modifying or stripping formulas/VBA.
2. **Canonical Identities & Disambiguation**:
   - `Image UID` is canonical image identity; `sessionUID*` is canonical acquisition session identity.
   - `Image #` restarts per session (1..24, 1..24, 1..25, 1..25), correctly scoping repeated camera basenames (`image1.jpg`) across sessions without collision.
   - `Original` and `Working filename` remain locators/names, not identity.
3. **Machine vs Sparse Human Field Resolution**:
   - Programmatic consumption utilizes resolved machine-readable `*` columns (`Exp*`, `Date*`, `Set*`, `sessionUID*`, `Profile*`, `Set*`, etc.) to expand sparse human entry blocks without requiring repeated manual entry.
4. **Independently Optional Media & Condition**:
   - Supported combinations: Media-only (`YPDA`, `None`), Condition-only (`None`, `sugar`), Media+Condition (`YPDA`, `heat`; `YPDA`, `salt`), and Replicate integer/string identifiers.
5. **Strain Profile & Label Band Interpretation**:
   - Distinct `Set` blocks inside the strain profile table are parsed as ordered top-to-bottom label bands (Band A, Band B), NOT filters against Master Registry image `Set`.
   - Master Registry images with `Set=A` and `Set=B` under `annotationSet 2` both correctly receive the full multi-band layout.
   - Global `grid_cols` is determined by the widest band; shorter bands retain their true occupied logical columns without shrinking the global grid.
6. **Physical Row Band Allocation**:
   - Vertical profile: 1 assigned per annotation set; `Set` inside vertical profile table is ignored; `grid_rows` = max vertical `Pos`.
   - Physical rows divide evenly across bands when deterministic ($8 \div 2 = 4$ rows/band -> Band A rows 1–4, Band B rows 5–8).
   - Non-deterministic row counts raise a clear validation `ValueError` unless explicit `row_band_overrides` are supplied.
7. **Physical File Reconciliation (`reconcile_image_files`)**:
   - Validated against controlled evidence hierarchy:
     1. Accepted `provenance_map`
     2. Exact `Original` basename inside the connected session folder
     3. Exact `Working filename`
     4. Controlled derivatives (e.g. `PROCESSED ` prefix, `.tif` extension change)
     5. Ambiguity / unmapped detection
   - Supported reconciliation states: `READY`, `EXPECTED_NOT_PRESENT`, `AMBIGUOUS`, `UNMAPPED_FILE`.
   - Incomplete expected image sets are represented as a normal valid metadata state.
8. **Legacy Projections**:
   - `project_to_legacy_images_rows(project_model)` and `project_to_legacy_grid_rows(plate_layout)` generate legacy CSV-shaped views on demand without creating a second metadata authority.

## What was NOT proven

- Parsing workbooks with multiple vertical profiles per annotation set (explicitly deferred/out of scope).
- Handling of `other` label profiles (explicitly deferred/out of scope).
- Live desktop Excel COM/VBA interaction (not required; openpyxl read-only parsing is fully headless and sufficient).

## Public interface

- `load_v10(excel_path: str) -> dict`: Produces `ProjectModel` v1.
- `extract_layouts(excel_path: str, row_band_overrides: Optional[dict] = None) -> dict[str, dict]`: Produces `PlateLayout` v1 mappings.
- `derive_plate_layout(project_model: dict, image_uid: str, layouts: Optional[dict] = None, v10_path: Optional[str] = None) -> dict`: Returns `PlateLayout` for a specific image.
- `reconcile_image_files(project_model: dict, files_by_session: Optional[dict] = None, provenance_map: Optional[dict] = None) -> dict`: Reconciles expected images to physical files.
- `project_to_legacy_images_rows(project_model: dict) -> list[dict]`: Generates legacy `images.csv` rows.
- `project_to_legacy_grid_rows(plate_layout: dict) -> list[dict]`: Generates legacy `grid.csv` rows.

## Input contract

- Path to a valid V10 Excel workbook (`.xlsm` or `.xlsx`) containing sheets: `Overview`, `Master Registry`, `Annotations`, and optionally `Arrangements`.

## Output contract / Shared schemas used

- `contracts/project_model.schema.json` (version 1)
- `contracts/plate_layout.schema.json` (version 1)

## Fixture(s)

- `fixtures/v10/v10_sample_synthetic_sanitized.xlsx` (synthetic, non-confidential, sanitized test workbook containing 98 images across 4 sessions and 2 annotation sets).

## Verification command(s)

```powershell
python docs/gemini/prototypes/v10/test_adapter.py
```

## Verification result

```text
[PASS] test_load_v10_contract_and_schemas
[PASS] test_sessions_and_image_uids
[PASS] test_sparse_human_vs_resolved_machine_fields
[PASS] test_media_and_condition_combinations
[PASS] test_extract_layouts_single_and_multi_band
[PASS] test_strain_set_not_matched_to_master_registry_set
[PASS] test_vertical_profile_set_ignored
[PASS] test_derive_plate_layout_api
[PASS] test_unequal_band_widths_synthetic
[PASS] test_non_deterministic_band_allocation_validation
[PASS] test_reconcile_image_files
[PASS] test_legacy_projections

ALL 12 V10 ADAPTER AUDIT TESTS PASSED.
```

## Dependencies & external software

- Python packages: `pandas`, `openpyxl`
- External software/plugins required: None (pure Python).

## Known limitations

- Only single vertical profile per annotation set is supported (sufficient for all current use cases).
- Out-of-scope `other` profiles in the Annotations sheet are ignored.

## Failed / abandoned routes relevant to integration

- *Single-band grouping for multi-Set strain tables*: An earlier prototype attempt ignored strain-table `Set` column grouping, causing `Strain 2` (10 cols Set A + 10 cols Set B) to merge into a single 20-col band. That route was discarded in favor of explicit `Set` band block parsing and top-to-bottom row splitting.

## Human / manual validation still required

- None for metadata parsing. Downstream visual validation applies to rendering tools consuming these layouts.

## Files the integrator should inspect

- `docs/gemini/prototypes/v10/adapter.py`: Core standalone implementation.
- `docs/gemini/prototypes/v10/test_adapter.py`: Targeted unit tests and contract validation.

## Files the integrator normally should NOT need to inspect

- `fixtures/v10/`: Test fixtures only.

## Recommended integration / adaptation

- `adapter.py` can be cherry-picked directly or copied into tools/adapters as a standalone module. Downstream mini-apps (`project_setup_rename`, `annotation`, `layout`) can import `load_v10`, `derive_plate_layout`, and `reconcile_image_files` directly.

## Contract changes proposed

- None. Strictly conforms to `project_model.schema.json` v1 and `plate_layout.schema.json` v1.
