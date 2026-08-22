# V10 adapter prototype handoff

Status: Planned

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

When proven, replace this section with:

- Branch:
- Commit:
- Interface: `load_v10(path) -> ProjectModel`
- Tests:
- Dependencies:
- Proven cases:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
