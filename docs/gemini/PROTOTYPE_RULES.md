# Gemini prototype rules

This branch is for isolated future-facing prototypes only. `workflow-C` remains the integration branch and must have one active writer at a time.

## Branch discipline

- Do not write directly to `workflow-C` from Gemini prototype work.
- Do not modify the current Fiji/AHK/controller runtime while another agent owns it.
- Prefer new standalone modules, tests, focused applets, schemas and synthetic fixtures.
- Completed prototype work is never merged automatically. The current `workflow-C` owner reviews and cherry-picks/adapts useful commits.
- Keep each prototype independently runnable/testable where practical.

## Architecture posture

The intended end state may be a lightweight overall controller that owns project/file selection and shared state, then launches focused mini-apps for distinct jobs. Do **not** assume every capability belongs inside one large GUI.

A useful mini-app should:

- consume a narrow shared contract or explicit file/project input;
- perform one coherent job;
- expose its core work through callable functions rather than GUI-only logic;
- return/save an explicit result that later steps can consume;
- avoid duplicating V10 parsing, project discovery or other global state already owned elsewhere.

Optimize for the actual workflow and user time. Mature packages, Fiji/ImageJ features, Pillow, OpenCV/scikit-image, small scripts and modest manual confirmation are preferable to large bespoke systems when they reach the endpoint more reliably.

## CSV baseline versus V10 semantics

The currently working basic CSV workflow is intentionally a simpler baseline. It does **not** need V10-style annotation-set/profile-order/Set semantics retrofitted into it.

V10 is the richer structured metadata source for future integrated behavior. Prototypes should consume the canonical V10-derived model where relevant without treating missing V10 semantics in the basic CSV mode as a defect.

## Current allowed prototype areas

1. V10 read-only adapter and canonical metadata model.
2. Project setup / UID-safe working-copy renaming.
3. Grid/layout derivation from normalized V10 metadata.
4. Whole-plate orientation preprocessing.
5. Plate crop preprocessing.
6. Visibility-adjustment / human-review preprocessing.
7. Whole-plate annotation and lightweight composition using grid coordinates.
8. Future focused applets that consume shared contracts rather than controller internals.

Do not replace or redesign the currently working four-click grid route merely because a prototype could theoretically automate it. New preprocessing helpers must remain optional and non-blocking for that route.

## Shared-contract rule

Cross-component prototypes must consume/produce the versioned schemas under `contracts/` rather than inventing incompatible ad-hoc interfaces.

If a prototype genuinely needs a new shared field, do not silently change semantics. Record the proposed contract change in that prototype's HANDOFF with the reason and keep the change narrow.

The grid/coordinate result should be treated as reusable project state, not as something that only exists during crop export. Later steps such as visibility adjustment, annotation and processed-image crop export should be able to consume saved coordinates without rerunning alignment.

## Data/privacy

- Use synthetic workbook/data fixtures only unless the branch-specific handoff explicitly permits public non-confidential images.
- Never inspect or ingest real/sample image pixels during Gemini prototype work.
- Do not add real experiment data, real source paths, screenshots or pixel-bearing outputs to the branch.
- Synthetic/public images may be used only for isolated image-processing prototypes when needed.

## Prototype checkpoint output

Each coherent successful prototype checkpoint must update:

1. `docs/gemini/GEMINI_INDEX.md` with a 1-3 line entry.
2. Its own `docs/gemini/prototypes/<name>/HANDOFF.md` with:
   - exact branch and commit SHA;
   - status and what is actually proven;
   - narrow public/API interface;
   - tests run;
   - dependencies added;
   - known limitations;
   - integration/cherry-pick notes;
   - shared-contract changes, if any.

Do not keep a development diary or reasoning transcript. Handoffs should stay compact and evidence-based after implementation; specifications may be detailed enough to prevent rediscovery or semantic confusion.

## Integration posture

Gemini prototypes should be designed so the overall controller can later orchestrate them without absorbing their implementation details. Favor narrow entry points such as:

- `load_v10(path) -> ProjectModel`
- `prepare_working_copy(...) -> RenameResult`
- `derive_plate_layout(project, image_uid) -> PlateLayout`
- `estimate_or_capture_plate_rotation(...) -> RotationResult`
- `derive_plate_crop(...) -> CropResult`
- `adjust_plate_visibility(...) -> AdjustmentResult`
- `render_plate_annotation(...) -> AnnotationResult`

Prototype `Proven` status means the isolated interface works with targeted evidence. It does not mean production integration is automatic or that the current `workflow-C` implementation should be rewritten around it.