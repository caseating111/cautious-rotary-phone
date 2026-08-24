# Gemini prototype index

Compact routing index for isolated prototype work. Keep this file short; detailed requirements and evidence belong in each prototype HANDOFF. The end-to-end intended sequence is in `docs/gemini/FUTURE_WORKFLOW.md`.

| Prototype | Status | Branch/commit | Interface | Handoff |
| --- | --- | --- | --- | --- |
| V10 adapter | INTEGRATED | `workflow-integrated` (`246efcb`) | `load_v10(path) -> ProjectModel` | `docs/gemini/prototypes/v10/HANDOFF.md` |
| Project setup / working-copy rename | INTEGRATED | `workflow-integrated` (`c31d4f1`) | `prepare_working_copy(...) -> RenameResult` | `docs/gemini/prototypes/project_setup_rename/HANDOFF.md` |
| Grid/layout derivation | INTEGRATED | `workflow-integrated` (`246efcb`) | `derive_plate_layout(project, image_uid) -> PlateLayout` | `docs/gemini/prototypes/layout/HANDOFF.md` |
| Whole-plate orientation | INTEGRATED | `workflow-integrated` (`c31d4f1`) | one horizontal-edge line drag -> `OrientationResult` | `docs/gemini/prototypes/plate_rotation/HANDOFF.md` |
| Plate crop preprocessing | INTEGRATED | `workflow-integrated` (`c31d4f1`) | reusable `CropSizeCalibration` + per-image `CropResult` | `docs/gemini/prototypes/plate_crop/HANDOFF.md` |
| Visibility adjustment / review | INTEGRATED | `workflow-integrated` (`c31d4f1`) | `adjust_plate_visibility(...) -> AdjustmentResult` | `docs/gemini/prototypes/visibility_adjustment/HANDOFF.md` |
| Annotation/composition | INTEGRATED | `workflow-integrated` (`c31d4f1`, `fdac0df`) | saved grid + metadata/layout/crops -> annotation or mixed-tier matrix | `docs/gemini/prototypes/annotation/HANDOFF.md` |
| Four-point grid registration | INTEGRATED | `workflow-integrated` (`8fabf35`, `cfdd806`) | accepted four-click route -> `GridCoordinateAsset`; optional register-only | production route intentionally retained |

## Index rules

- `geminimain` is the common Gemini baseline/specification branch. Feature implementation should normally happen on a dedicated child branch so parallel work does not collide.
- Read `FUTURE_WORKFLOW.md` before implementing a prototype whose inputs/outputs depend on other workflow stages; do not duplicate the full sequence inside every handoff.
- Read `docs/development/PROJECT_ASSET_CONTRACT.md` when the prototype creates, consumes, invalidates or transforms reusable project geometry/state.
- Read `docs/development/PROTOTYPE_HANDOFF_STANDARD.md` for the authoritative prototype status vocabulary and handoff evidence requirements.
- Mini-apps are intended to remain independently runnable. The eventual main controller is an orchestrator/convenience layer, not a required parent process.
- Applets should check only their true prerequisites from shared project state rather than enforce the preferred full workflow order.
- The same callable/core path should support standalone and controller-launched operation where practical.
- Update only at coherent prototype checkpoints, not after every edit/test.
- `PROOF PASSED` means the documented narrow proof succeeded; it is not automatically `READY FOR INTEGRATION`.
- `READY FOR INTEGRATION` requires an explicit audit against the current shared contracts and current component requirements.
- `INTEGRATED` means the active `workflow-C` owner intentionally reviewed and integrated/cherry-picked/adapted it; prototype completion alone does not imply integration.
- Do not duplicate the detailed functional specification here; read the linked HANDOFF for the assigned prototype.
