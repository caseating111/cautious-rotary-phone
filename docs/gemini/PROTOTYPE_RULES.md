# Gemini prototype rules

This branch is for isolated future-facing prototypes only. `workflow-C` remains the integration branch and must have one active writer at a time.

## Branch discipline

- Do not write directly to `workflow-C` from Gemini prototype work.
- Do not modify the current Fiji/AHK/controller runtime while Codex is stabilizing it.
- Prefer new standalone modules, tests, small applets, schemas and synthetic fixtures.
- Completed prototype work is never merged automatically. The current `workflow-C` owner reviews and cherry-picks/adapts useful commits.
- Keep each prototype independently runnable/testable where practical.

## Current allowed prototype areas

1. V10 read-only adapter and canonical metadata model.
2. Grid/layout derivation from synthetic V10-like metadata.
3. Whole-plate annotation/composition using Pillow/Fiji overlays and synthetic inputs.
4. Whole-plate physical rotation/alignment research and isolated proof-of-concept work.
5. Future lightweight focused applets that consume the shared contract rather than controller internals.

Do not work on the current four-click Fiji launcher, current AHK v2 runtime, current CSV controller stabilization, or other files actively owned by the `workflow-C` integrator.

## Shared-contract rule

Cross-component prototypes must consume/produce the versioned schemas under `contracts/` rather than inventing incompatible ad-hoc interfaces.

If a prototype genuinely needs a new shared field, do not silently change semantics. Record the proposed contract change in that prototype's HANDOFF with the reason and keep the change narrow.

## Data/privacy

- Use synthetic workbook/data fixtures only.
- Never inspect or ingest real/sample image pixels.
- Do not add real experiment data, real source paths, screenshots or pixel-bearing outputs to the branch.
- Synthetic/public images may be used only for isolated computer-vision prototypes when needed.

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

Do not keep a development diary or reasoning transcript. Handoffs should stay compact and evidence-based.

## Integration posture

Gemini prototypes should be designed so the main controller can later orchestrate them without absorbing their implementation details. Favor narrow entry points such as:

- `load_v10(path) -> ProjectModel`
- `derive_plate_layout(project, image_uid) -> PlateLayout`
- `render_plate_annotation(...) -> AnnotationResult`
- `estimate_plate_rotation(path) -> RotationResult`

The eventual UI may remain one lightweight controller that owns file/project selection and launches focused tools/applets. Do not refactor the failing current controller to achieve that architecture during prototype work.