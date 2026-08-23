# Gemini prototype index

Compact routing index for isolated prototype work. Keep this file short; detailed requirements and evidence belong in each prototype HANDOFF. The end-to-end intended sequence is in `docs/gemini/FUTURE_WORKFLOW.md`.

| Prototype | Status | Branch/commit | Interface | Handoff |
| --- | --- | --- | --- | --- |
| V10 adapter | Proven | `gemini-v10` (`5e8078f`) | `load_v10(path) -> ProjectModel` | `docs/gemini/prototypes/v10/HANDOFF.md` |
| Project setup / working-copy rename | Planned | `geminimain` baseline; dedicated child branch when implementation begins | `prepare_working_copy(...) -> RenameResult` | `docs/gemini/prototypes/project_setup_rename/HANDOFF.md` |
| Grid/layout derivation | Planned | `geminimain` baseline; dedicated child branch when implementation begins | `derive_plate_layout(project, image_uid) -> PlateLayout` | `docs/gemini/prototypes/layout/HANDOFF.md` |
| Whole-plate orientation | Planned | `geminimain` baseline; dedicated child branch when implementation begins | one horizontal-edge line drag -> `OrientationResult` | `docs/gemini/prototypes/plate_rotation/HANDOFF.md` |
| Plate crop preprocessing | Planned | `geminimain` baseline; dedicated child branch when implementation begins | reusable `CropSizeCalibration` + per-image `CropResult` | `docs/gemini/prototypes/plate_crop/HANDOFF.md` |
| Visibility adjustment / review | Planned | `geminimain` baseline; dedicated child branch when implementation begins | `adjust_plate_visibility(...) -> AdjustmentResult` | `docs/gemini/prototypes/visibility_adjustment/HANDOFF.md` |
| Annotation/composition | Planned | `geminimain` baseline; dedicated child branch when implementation begins | saved grid + metadata/layout -> annotation/composition result | `docs/gemini/prototypes/annotation/HANDOFF.md` |
| Grid registration applet | Future divestment | production route currently lives on `workflow-C` | `register_plate_grid(...) -> GridCoordinateAsset` | extract only after current route remains proven |

## Index rules

- `geminimain` is the common Gemini baseline/specification branch. Feature implementation should normally happen on a dedicated child branch so parallel work does not collide.
- Read `FUTURE_WORKFLOW.md` before implementing a prototype whose inputs/outputs depend on other workflow stages.
- Read `docs/development/PROJECT_ASSET_CONTRACT.md` when the prototype creates, consumes, invalidates or transforms reusable project geometry/state.
- Mini-apps are intended to remain independently runnable. The eventual main controller is an orchestrator/convenience layer, not a required parent process.
- Applets should check only their true prerequisites from shared project state rather than enforce the preferred full workflow order.
- The same callable/core path should support standalone and controller-launched operation where practical.
- Update only at coherent prototype checkpoints, not after every edit/test.
- Use `Planned`, `In progress`, `Proven`, `Rejected`, or `Integrated` as status.
- Record the exact successful child branch and commit SHA when a prototype becomes `Proven`.
- `Integrated` means the active `workflow-C` owner intentionally reviewed and integrated/cherry-picked/adapted it; prototype completion alone does not imply integration.
