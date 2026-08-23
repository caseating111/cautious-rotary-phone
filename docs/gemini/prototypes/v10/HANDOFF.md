# V10 adapter prototype handoff

Status: Proven

## Target

Read synthetic V10 workbook (.xlsm or .xlsx) and produce `ProjectModel` v1 plus normalized layout-source data (`PlateLayout` v1), layout derivation, physical file reconciliation, and legacy CSV compatibility projections without touching current Fiji/AHK/controller runtime code.

## Required semantics

- Read-only workbook handling (.xlsm or .xlsx via openpyxl).
- Preserve V10 terminology where practical.
- `Image UID` is canonical image identity; `sessionUID*` is canonical acquisition/session identity.
- `Original` and `Working filename` are locators/names, not identity.
- `Image #` restarts per session; raw names (e.g. `image1.jpg`) across sessions are scoped by `sessionUID`.
- Sparse human-entered cells resolve correctly from machine-readable `*` fields (`Exp*`, `Date*`, `Set*`, `sessionUID*`, etc.).
- `Media` and `Condition` are independently optional (support Media-only, Condition-only, both, or neither).
- Incomplete expected image sets are valid metadata state.
- Physical file reconciliation with controlled evidence order (provenance -> exact original -> exact working -> controlled derivatives -> ambiguous/unmapped).
- Vertical profile: 1 assigned per annotation set; `Set` inside vertical profile table is ignored; `grid_rows` = max vertical `Pos`.
- Strain profile: distinct `Set` blocks in strain profile table are label-band grouping markers (NOT filters against image Set).
- `grid_cols` = maximum `Pos` across all strain-label bands.
- Row distribution: even division across strain bands when deterministic (e.g. 8 rows / 2 bands -> rows 1-4, 5-8); validation error if non-deterministic unless explicit `row_band_overrides` provided.
- `other` labels remain out of scope and are ignored.
- Synthetic workbook/data only; no real images.

## Completion record

- Branch: `gemini-v10`
- Commit: `9648bed`
- Interfaces:
  - `load_v10(path) -> dict` (ProjectModel v1)
  - `extract_layouts(path, row_band_overrides=None) -> dict[str, dict]` (PlateLayout v1 mappings)
  - `derive_plate_layout(project_model, image_uid, layouts=None, v10_path=None) -> dict` (PlateLayout v1)
  - `reconcile_image_files(project_model, files_by_session=None, provenance_map=None) -> dict` (Reconciliation status)
  - `project_to_legacy_images_rows(project_model) -> list[dict]` (Legacy images.csv projection)
  - `project_to_legacy_grid_rows(plate_layout) -> list[dict]` (Legacy grid.csv projection)
- Tests: 12 comprehensive unit tests in `test_adapter.py` passing cleanly.
- Dependencies: `pandas`, `openpyxl`
- Proven cases:
  - Loading `v10_sample_synthetic_sanitized.xlsx` produces 98 images, 4 unique sessions, 2 complete layouts.
  - `annotationSet 1` produces 8x12 layout (1 strain band spanning rows 1-8).
  - `annotationSet 2` produces 8x10 layout (2 strain bands: Band A rows 1-4, Band B rows 5-8).
  - Master Registry images with `Set=A` and `Set=B` under `annotationSet 2` both correctly receive the full 2-band 8x10 layout.
  - Media-only, Condition-only (sugar), and Media+Condition (heat, salt) combinations resolve properly.
  - Controlled file reconciliation verifies READY, EXPECTED_NOT_PRESENT, AMBIGUOUS, and UNMAPPED_FILE states.
- Known limitations: None for current V10 contract scope.
- Contract changes proposed: None (strictly conforms to version 1 schemas).
- Integration/cherry-pick notes: `adapter.py` is fully standalone and can be consumed directly by downstream prototypes and controllers.
