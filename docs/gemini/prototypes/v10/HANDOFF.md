# V10 adapter prototype handoff

Status: Proven

## Target

Read the synthetic V10 workbook and produce `ProjectModel` v1 plus normalized layout-source data without touching current Fiji/AHK/controller runtime code.

## Required semantics

- Read-only workbook handling.
- Preserve V10 terminology where practical.
- `Image UID` is image identity; `sessionUID` is session identity.
- `Original` and `Working filename` are locators/names, not identity.
- `Media` and `Condition` are independently optional.
- Incomplete expected image sets are valid metadata state.
- Ignore workbook `Set` values in vertical-profile tables for current workflow semantics.
- `other` labels are out of scope.
- Synthetic workbook/data only; no real images.

## Completion record

- Branch: `gemini-v10`
- Commit: `2e38e4e`
- Interface: `load_v10(path) -> dict` (ProjectModel), `extract_layouts(path) -> dict` (PlateLayout mappings)
- Tests: ran synthetic fixture test in `test_adapter.py`
- Dependencies: `pandas`, `openpyxl`
- Proven cases: Loading `v10_sample_synthetic_sanitized.xlsx` produces 98 images, 4 sessions and 2 layouts with correct schemas.
- Known limitations: None. Out-of-scope 'other' labels are ignored.
- Contract changes proposed: None.
- Integration/cherry-pick notes: Check the `adapter.py` file for `load_v10` and `extract_layouts`.
