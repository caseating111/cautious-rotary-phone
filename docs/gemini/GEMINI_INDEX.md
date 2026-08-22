# Gemini prototype index

Compact routing index for isolated prototype work. Keep this file short; detailed requirements and evidence belong in each prototype HANDOFF.

| Prototype | Status | Branch/commit | Interface | Handoff |
| --- | --- | --- | --- | --- |
| V10 adapter | Planned | `geminimain` baseline; implementation normally on `gemini-v10` | `load_v10(path) -> ProjectModel` | `docs/gemini/prototypes/v10/HANDOFF.md` |
| Grid/layout derivation | Planned | `geminimain` baseline; use a dedicated child branch when implementation begins | `derive_plate_layout(project, image_uid) -> PlateLayout` | `docs/gemini/prototypes/layout/HANDOFF.md` |
| Annotation/composition | Planned | `geminimain` baseline; use a dedicated child branch when implementation begins | shared metadata/layout -> annotation/composition result | `docs/gemini/prototypes/annotation/HANDOFF.md` |
| Whole-plate rotation | Planned | `geminimain` baseline; use a dedicated child branch when implementation begins | `estimate_plate_rotation(path) -> RotationResult` | `docs/gemini/prototypes/plate_rotation/HANDOFF.md` |

## Index rules

- `geminimain` is the common Gemini baseline/specification branch. Feature implementation should normally happen on a dedicated child branch so parallel work does not collide.
- Update only at coherent prototype checkpoints, not after every edit/test.
- Use `Planned`, `In progress`, `Proven`, `Rejected`, or `Integrated` as status.
- Record the exact successful child branch and commit SHA when a prototype becomes `Proven`.
- `Integrated` means the active `workflow-C` owner intentionally reviewed and integrated/cherry-picked/adapted it; prototype completion alone does not imply integration.
- Do not duplicate the detailed functional specification here; read the linked HANDOFF for the assigned prototype.
