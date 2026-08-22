# Grid/layout derivation prototype handoff

Status: Planned

## Target

Derive `PlateLayout` v1 from synthetic canonical metadata without depending on Fiji or the current controller.

## Required current cases

- 8x12 single strain band spanning all rows.
- 8x10 two strain bands: order 1 rows 1-4, order 2 rows 5-8 when metadata makes that deterministic.
- One vertical profile only.
- Ignore vertical-profile `Set` values.
- Widest strain band defines `grid_cols`.
- Ambiguous band assignment must be reported rather than guessed.

## Completion record

- Branch:
- Commit:
- Interface: `derive_plate_layout(project, image_uid) -> PlateLayout`
- Tests:
- Dependencies:
- Proven cases:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
