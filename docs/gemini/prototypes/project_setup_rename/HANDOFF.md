# Project setup / UID-safe working-copy renaming handoff

Status: READY FOR INTEGRATION
Endpoint: Prepare project directory tree, reconcile physical raw files to V10 metadata/UIDs, and create optional UID-safe renamed working copies and human conversion audit logs.
Branch: `gemini-project-setup-rename`
Commit: `3fd3c55`

## What was proven

1. **Untouched Raw Sources**:
   - Generic camera names (`image1.jpg`, `image2.jpg`, etc.) in `raw/` remain bit-for-bit untouched and unmodified.
2. **Optional Renamed Working Copies**:
   - When `enable_rename=True`, working copies are placed in `working/` using exact V10 working filenames (e.g. `14.08.26_SetA_24h_YPDA, 1.jpg`).
3. **Rename-Disabled Mode**:
   - When `enable_rename=False`, working copies keep original camera names in `working/` while maintaining valid structured `Image UID` -> working path mapping.
4. **Session Disambiguation**:
   - Repeated camera names (`image1.jpg`) across different sessions (e.g. 24h vs 48h) resolve to distinct UIDs (`E1_14.08.26_24h_I001` vs `E1_15.08.26_48h_I001`) and distinct working destinations without collision.
5. **Collision Detection & Disambiguation**:
   - Case-insensitive Windows collisions (e.g. `SAMPLE_PLATE.jpg` vs `sample_plate.jpg`) are detected and flagged as `TARGET_COLLISION` under `'error'` policy, or deterministically disambiguated with UID suffixes under `'disambiguate_with_uid'`.
6. **Human Conversion Audit Log**:
   - `image_name_conversions.txt` is generated at project root with clean Experiment and Set dividers, relative paths only, UID and session context, and disposition tracking.
7. **Idempotence & Safety**:
   - Rerunning setup on an existing project tree is idempotent, reporting `UNCHANGED_CURRENT` for existing matching files without duplicate file copies or rename chains.
8. **Incomplete Expected Sets**:
   - Missing physical files for expected V10 records are marked `EXPECTED_NOT_PRESENT` without blocking the copying and processing of present files.
9. **Ambiguous Source Detection**:
   - Multiple candidate files matching one image record are flagged as `AMBIGUOUS_SOURCE` and blocked from copying rather than guessed.
10. **Preview Mode**:
    - When `preview_only=True`, zero filesystem writes occur while returning the complete planned `RenameResult` and conversion text.
11. **Project Directory Tree Initialization**:
    - Standard directory layout (`raw/`, `working/`, `processed/`, `annotated/`, `crops/unprocessed/`, `crops/processed/`, `matrices/`, `state/`) is created cleanly and compatibly for downstream mini-apps.

## What was NOT proven

- Image pixel processing, plate orientation/rotation, and grid alignment (out of scope; handled by downstream mini-apps).
- Multi-user concurrent filesystem modifications (local single-process execution tested).

## Public interface

- `initialize_project_tree(project_root: str, create_subdirs: bool = True) -> dict[str, str]`
- `generate_conversion_map_text(project_model: dict, rename_results: list[dict], project_root: Optional[str] = None) -> str`
- `prepare_working_copy(project_model: dict, project_root: str, raw_root: Optional[str] = None, working_root: Optional[str] = None, options: Optional[dict] = None) -> dict`

## Input contract

- `project_model`: Canonical `ProjectModel` v1 dict (from `load_v10`).
- `project_root`: Root directory path for the project.
- `options`:
  - `enable_rename`: bool (default True)
  - `preview_only`: bool (default False)
  - `write_conversion_map`: bool (default True)
  - `collision_policy`: `'error'` | `'disambiguate_with_uid'` (default `'error'`)
  - `provenance_map`: Optional dict mapping `image_uid` -> accepted physical file
  - `custom_session_folders`: Optional dict mapping `session_uid` -> folder path

## Output contract / Shared schemas used

- Returns `RenameResult` dictionary containing:
  - `contract_version`: 1
  - `project_root`: str
  - `raw_root`: str
  - `working_root`: str
  - `conversion_map_path`: str
  - `conversion_map_text`: str
  - `summary`: dict with counts (`total_expected`, `copied_renamed_count`, `copied_original_count`, `unchanged_current_count`, `expected_not_present_count`, `ambiguous_source_count`, `target_collision_count`, `skipped_count`)
  - `images`: list of dicts (`image_uid`, `session_uid`, `raw_path`, `working_path`, `disposition`, `disposition_detail`)
  - `unmapped_files`: list of physical files not mapped to any expected image.

## Fixture(s)

- `fixtures/v10/v10_sample_synthetic_sanitized.xlsx`

## Verification command(s)

```powershell
.\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\project_setup_rename\test_setup_rename.py
# or: python docs/gemini/prototypes/project_setup_rename/test_setup_rename.py
```

## Verification result

```text
[PASS] test_generic_raw_names_untouched
[PASS] test_optional_renamed_working_copies
[PASS] test_rename_disabled_mode
[PASS] test_session_disambiguation
[PASS] test_windows_case_collision_detection
[PASS] test_conversion_map_formatting
[PASS] test_idempotence
[PASS] test_incomplete_datasets
[PASS] test_ambiguous_source_detection
[PASS] test_preview_mode_zero_writes
[PASS] test_project_tree_initialization

ALL 11 PROJECT SETUP & RENAME PROOF TESTS PASSED.
```

## Dependencies & external software

- Tested & verified runtime: **Python 3.11 (Miniforge Conda `workflow-c` environment)** and **Python 3.14**
- Python packages: `pandas`, `openpyxl` (standard standard library: `os`, `shutil`, `tempfile`, `sys`, `typing`)
- Internal dependency: `docs/gemini/prototypes/v10/adapter.py` (`load_v10`, `reconcile_image_files`)
- External software/plugins required: None.

## Known limitations

- Filesystem copy performance on extremely large datasets (e.g. 10,000+ files) will depend on disk I/O; fast size-based checks are used for idempotence.

## Failed / abandoned routes relevant to integration

- *In-place raw renaming*: Renaming source files in-place was considered in historical scripts, but firmly abandoned in favor of non-destructive working copies to preserve raw source integrity.

## Human / manual validation still required

- None for filesystem setup; users can visually inspect `image_name_conversions.txt` at `project_root`.

## Files the integrator should inspect

- `docs/gemini/prototypes/project_setup_rename/setup_rename.py`: Core setup and rename implementation.
- `docs/gemini/prototypes/project_setup_rename/test_setup_rename.py`: 11 unit tests covering all edge cases and collision policies.

## Files the integrator normally should NOT need to inspect

- `fixtures/v10/`: Test fixtures.

## Recommended integration / adaptation

- Can be imported directly by CLI, AHK launcher, or GUI controller:
  ```python
  from setup_rename import prepare_working_copy
  from adapter import load_v10
  
  pm = load_v10("path/to/v10.xlsx")
  res = prepare_working_copy(pm, project_root="path/to/project")
  ```

## Contract changes proposed

- None. Conforms directly to `contracts/project_model.schema.json` and `docs/development/PROJECT_ASSET_CONTRACT.md`.
