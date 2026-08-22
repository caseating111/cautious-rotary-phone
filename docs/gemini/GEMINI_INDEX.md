# Gemini prototype index

Compact routing index for isolated prototype work. Keep this file short; detailed requirements and evidence belong in each prototype HANDOFF. The end-to-end intended sequence is in `docs/gemini/FUTURE_WORKFLOW.md`.

| Prototype | Status | Branch/commit | Interface | Handoff |
| --- | --- | --- | --- | --- |
| V10 adapter | Planned | `geminimain` baseline; implementation normally on `gemini-v10` | `load_v10(path) -> ProjectModel` | `docs/gemini/prototypes/v10/HANDOFF.md` |
| Project setup / working-copy rename | Planned | dedicated child branch when implementation begins | `prepare_working_copy(...) -> RenameResult` | `docs/gemini/prototypes/project_setup_rename/HANDOFF.md` |
| Grid/layout derivation | Planned | dedicated child branch when implementation begins | `derive_plate_layout(project, image_uid) -> PlateLayout` | `docs/gemini/prototypes/layout/HANDOFF.md` |
| Whole-plate orientation | Planned | dedicated child branch when implementation begins | two-click/manual-first `RotationResult`; optional automatic estimator later | `docs/gemini/prototypes/plate_rotation/HANDOFF.md` |
| Plate crop preprocessing | Planned | dedicated child branch when implementation begins | `derive_plate_crop(...) -> CropResult` | `docs/gemini/prototypes/plate_crop/HANDOFF.md` |
| Visibility adjustment / review | Planned | dedicated child branch when implementation begins | `adjust_plate_visibility(...) -> AdjustmentResult` | `docs/gemini/prototypes/visibility_adjustment/HANDOFF.md` |
| Annotation/composition | Planned | dedicated child branch when implementation begins | saved grid + metadata/layout -> annotation/composition result | `docs/gemini/prototypes/annotation/HANDOFF.md` |

## Index rules

- `geminimain` is the common Gemini baseline/specification branch. Feature implementation should normally happen on a dedicated child branch so parallel work does not collide.
- Read `FUTURE_WORKFLOW.md` before implementing a prototype whose inputs/outputs depend on other workflow stages; do not duplicate the full sequence inside every handoff.
- Update only at coherent prototype checkpoints, not after every edit/test.
- Use `Planned`, `In progress`, `Proven`, `Rejected`, or `Integrated` as status.
- Record the exact successful child branch and commit SHA when a prototype becomes `Proven`.
- `Integrated` means the active `workflow-C` owner intentionally reviewed and integrated/cherry-picked/adapted it; prototype completion alone does not imply integration.
- Do not duplicate the detailed functional specification here; read the linked HANDOFF for the assigned prototype.
