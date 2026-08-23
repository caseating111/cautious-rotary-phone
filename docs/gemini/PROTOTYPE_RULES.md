# Gemini prototype rules

This branch is for isolated future-facing prototypes only. `workflow-C` remains the integration branch and must have one active writer at a time.

## Branch discipline

- Do not write directly to `workflow-C` from Gemini prototype work.
- Do not modify the current Fiji/AHK/controller runtime while another agent owns it.
- Prefer new standalone modules, tests, focused applets, schemas and synthetic fixtures.
- Completed prototype work is never merged automatically. The current `workflow-C` owner reviews and cherry-picks/adapts useful commits.
- Keep each prototype independently runnable/testable where practical.
- Parallelize investigation and bounded independent artifacts; serialize mutation of the production integration surface.

## Architecture posture

The intended end state is a lightweight overall controller that owns project selection/shared status and launches focused mini-apps for distinct jobs. Do **not** assume every capability belongs inside one large GUI.

A mini-app is a real independently runnable tool, not merely a dialog that only works when launched from the main controller. Except for genuine data prerequisites such as an existing accepted grid asset, each applet should be able to start directly, receive/select a project root or project-state reference, discover the assets it needs, perform its task, and save/update only its own result.

The main controller should call the **same underlying callable/API path** that standalone mode uses. Do not create separate controller-only and standalone implementations of the same operation.

A useful mini-app should:

- consume a narrow shared contract or explicit project/file input;
- perform one coherent job;
- expose core work through callable functions rather than GUI-only logic;
- support one-image and selected-batch operation through the same core implementation where useful;
- return/save an explicit result that later steps can consume;
- check only its true prerequisites instead of enforcing the entire workflow order;
- avoid duplicating V10 parsing, project discovery or global state already represented in shared project state;
- be launchable by the overall controller later without being rewritten into the controller.

Examples of prerequisite behavior:

- annotation: require metadata/layout + accepted grid coordinates + a compatible source image;
- processed crop export: require accepted grid coordinates + a compatible processed image;
- matrix/composition: require the selected crop assets;
- visibility adjustment: require a compatible whole-plate image + accepted grid asset;
- plate crop: require an image and, when reusing size, a compatible `CropSizeCalibration`;
- grid registration: eventually becomes its own applet and produces `GridCoordinateAsset`; it should not own later crop/annotation/visibility workflows.

If a prerequisite is missing, report exactly what is missing (`GRID_REQUIRED`, compatible processed image missing, etc.) rather than forcing the user through steps that are irrelevant to that applet.

Optimize for the actual workflow and user time. Mature packages, Fiji/ImageJ features, Pillow, OpenCV/scikit-image, small scripts and modest manual confirmation are preferable to large bespoke systems when they reach the endpoint more reliably.

## Research posture — avoid tunnel vision

Prototype isolation is **not** permission to tunnel into the first architecture chosen. After the first meaningful failure toward a prototype's user-visible endpoint, follow the endpoint-first rule in `IMPLEMENTATION_DECISION_POLICY.md` before another architectural attempt.

- Restate the endpoint without the failed library/tool/protocol terminology.
- Check `docs/research/INDEX.md` and the matching endpoint history first.
- Search current official/mature end-to-end solutions and architectural alternatives before repair-specific searches.
- At least one search must omit the failing technology names and at least one must ask for the current supported/recommended way to accomplish the endpoint.
- Consider replacing, bypassing, composing, or inverting the current design; prototype code is sunk cost and may be discarded.
- Stop broad research once one candidate clearly looks viable and prove the smallest uncertain property with a targeted synthetic/public test.
- Do not create another fallback chain merely because the prototype already contains code for the failed route.

If **two meaningful implementation attempts relying on substantially the same architectural assumption** fail, stop patching that route. Do not attempt a third cosmetic variation unless materially new evidence changes the underlying assumption. This circuit breaker is intended to stop implementation-token waste; it does not automatically authorize a more expensive model. Follow `docs/development/AGENT_MODEL_ROUTING.md` for the cost/escalation boundary.

A prototype is more useful when it proves a mature integration boundary cleanly than when it accumulates custom compatibility machinery.

## Shared project-state / manifest posture

Shared project state is the interoperability layer between standalone applets and the eventual overall controller. Machine-readable state should map canonical image identity to relevant assets/results (raw, working, orientation, crop, grid, processed, annotation, crop exports, matrices) without requiring one process to remain open.

Human-readable mapping/status/log files remain useful QC aids but should not become the machine API between applets.

Applets should update only the state they own. Geometry-changing applets must mark dependent geometry stale when required; display-only/presentation applets must not invalidate unrelated geometric state.

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

Follow `docs/development/PROTOTYPE_HANDOFF_STANDARD.md`. Each coherent prototype checkpoint must update:

1. `docs/gemini/GEMINI_INDEX.md` with a compact status entry.
2. Its own `docs/gemini/prototypes/<name>/HANDOFF.md` with the exact branch/commit, endpoint, what was and was not proven, interface/contracts, fixtures/tests, dependencies, limitations, manual validation, integration notes, and any contract changes.

Use the explicit status vocabulary: `EXPLORATORY`, `PROOF PASSED`, `READY FOR INTEGRATION`, `INTEGRATED`, or `ROUTE FAILED`. Do not use an unqualified `Proven` label.

Do not keep a development diary or reasoning transcript. Handoffs should stay compact and evidence-based after implementation; specifications may be detailed enough to prevent rediscovery or semantic confusion.

## Integration posture

Gemini prototypes should be designed so the overall controller can later orchestrate them without absorbing their implementation details. Favor narrow entry points such as:

- `load_v10(path) -> ProjectModel`
- `prepare_working_copy(...) -> RenameResult`
- `derive_plate_layout(project, image_uid) -> PlateLayout`
- `capture_plate_orientation(...) -> RotationResult`
- `derive_plate_crop(...) -> CropResult`
- `register_plate_grid(...) -> GridCoordinateAsset` (future divestment of the current production grid route)
- `adjust_plate_visibility(...) -> AdjustmentResult`
- `render_plate_annotation(...) -> AnnotationResult`
- `compose_matrix(...) -> CompositionResult`

`PROOF PASSED` means the isolated interface works for the explicitly documented targeted proof. It does not mean current full requirements have been audited. `READY FOR INTEGRATION` is a separate status requiring an explicit audit against the current shared contracts and current component requirements; production integration remains a separate decision by the `workflow-C` owner.
