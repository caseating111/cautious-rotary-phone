# Gemini prototype index

Compact index of completed or active isolated prototypes on Gemini branches. Keep entries short; detailed evidence belongs in each prototype HANDOFF.

| Prototype | Status | Branch/commit | Interface | Handoff |
| --- | --- | --- | --- | --- |
| V10 adapter | Planned | `gemini-prototypes` | `load_v10(path) -> ProjectModel` | `docs/gemini/prototypes/v10/HANDOFF.md` |
| Grid/layout derivation | Planned | `gemini-prototypes` | `derive_plate_layout(project, image_uid) -> PlateLayout` | `docs/gemini/prototypes/layout/HANDOFF.md` |
| Annotation/composition | Planned | `gemini-prototypes` | shared metadata/layout -> annotation result | `docs/gemini/prototypes/annotation/HANDOFF.md` |
| Whole-plate rotation | Planned | `gemini-prototypes` | `estimate_plate_rotation(path) -> RotationResult` | `docs/gemini/prototypes/plate_rotation/HANDOFF.md` |

## Index rules

- Update only at coherent prototype checkpoints, not after every edit/test.
- Use `Planned`, `In progress`, `Proven`, `Rejected`, or `Integrated` as status.
- Record the exact successful commit SHA when a prototype becomes `Proven`.
- `Integrated` means the active `workflow-C` owner intentionally reviewed and integrated/cherry-picked it; prototype completion alone does not imply integration.
