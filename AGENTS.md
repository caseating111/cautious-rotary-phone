# Agent control

This repository exists to make the user's real image-processing/experimental workflow faster, easier, less tiring, and easier to validate. **The software is not the product.** Processed images, crops, matrices, annotations, measurements, and reduced user workload are the product. Scripts, macros, plugins, GUIs, and glue code are means to that end.

Repository state, executable behavior, accepted contracts, and current checked-in documentation outrank reconstructed chat history.

## Mandatory decision policy

Before any substantial implementation decision, read and follow `docs/development/IMPLEMENTATION_DECISION_POLICY.md`. It is authoritative for mature-tool-first decisions, endpoint-first research, anti-tunnel-vision behavior, testing budget, stop-loss rules, research memory, and when custom implementation is justified.

Core rules:

- optimize total user time-to-reliable-result, including setup, testing, debugging, validation, and maintenance;
- prefer mature/tested/published tools, plugins, packages, built-in scripting/APIs, composition, wrappers, and thin glue over bespoke replacements;
- an approximate multi-tool route or a small manual/QC step is acceptable when it removes most of the burden reliably;
- prove the smallest useful end-to-end slice before expanding a speculative architecture;
- do not treat sunk code or previous effort as a reason to preserve a poor route;
- substantial bespoke code requires evidence that mature-tool composition/adaptation cannot provide a practical result.

## Avoid tunnel vision

**Avoid tunnel vision.** After the first meaningful failure toward a user-visible endpoint, do not assume the failing architecture/library/protocol/launcher/integration mechanism should be repaired.

Restate the actual endpoint without the failing implementation's terminology, check prior endpoint memory, research current official/mature end-to-end solutions and architectural alternatives, and only then consider repairing the existing mechanism. At least one search should be technology-independent and at least one should ask for the current officially supported/recommended route.

Different errors blocking the same user outcome are one continuing endpoint failure. After repeated endpoint failures, do not add another fallback, IPC layer, compatibility workaround, retry path, or custom abstraction until the solution space has been reopened and the next route has a small isolated proof.

Ordinary component defects inside an otherwise-proven route—syntax errors, typos, malformed arguments, narrow regressions—may be fixed locally. See `IMPLEMENTATION_DECISION_POLICY.md` for the full distinction and required pre-second-attempt checkpoint.

## Testing efficiency

Default to targeted, minimum-sufficient validation. Do not perform exhaustive, redundant, speculative, or unchanged broad testing.

Expand testing only when a test fails, runtime evidence contradicts expectations, evidence suggests broader regression, or the user explicitly requests broader testing/audit. Reuse valid existing evidence. Batch manual/visual validation rather than repeatedly interrupting the user.

User testing time is expensive. Repeated user test -> failure -> patch cycles are evidence that the route itself may be wrong.

## Privacy / image-blind boundary

Real/sample experimental images and pixel-bearing derivatives must remain outside the repository and must never be committed, pushed, attached to issues/PRs, copied into fixtures, or supplied to Codex/Gemini/other model context.

Agents must not open, render, preview, screenshot, OCR, thumbnail, or otherwise inspect real/sample image pixels. Local Fiji/ImageJ/Python/AHK tools may process external image paths, but agents may consume only non-image outputs such as exit codes, filenames, structured metadata, ROI/grid coordinates, dimensions, numeric measurements, textual logs, generated macro text, and window/process state.

If visual interpretation is required, record/batch the exact manual validation for the user. Follow `docs/development/IMAGE_BLIND_TESTING.md` where present.

Synthetic/public test images may be used only when clearly non-confidential.

## Current environment / compatibility

Unless the user explicitly changes the target:

- production/testing priority is **Windows + Miniforge `workflow-c` + Python 3.11**;
- do not spend CI/testing time on Linux or older Python versions merely for general compatibility;
- AutoHotkey is **v2 only**; do not write v1/v2 hybrid syntax;
- preserve source images and avoid destructive in-place processing by default.

## Workflow-specific authority

Do **not** embed old implementation choices in this file as permanent invariants. Current alignment method, launcher route, V10 semantics, GUI state, crop/export behavior, and active blockers belong in current-state/roadmap/contract documents.

For normal Codex work, `docs/development/CURRENT_STATE.md` is the active implementation source of truth. For future architecture/state reuse, read the relevant workflow/project-asset contracts rather than reviving retired routes from old documentation.

A previously working component should be preserved unless the current task or evidence justifies changing it, but no historical approach receives permanent protection merely because it once existed.

## Multi-agent / branch coordination

When multiple agents or prototype branches are involved, read `docs/development/MULTI_AGENT_CONTRACT.md` where present.

- `workflow-C` is the normal integration/product branch and should have one active writer/integrator at a time.
- `geminimain` is the shared Gemini specification baseline; independent Gemini implementation streams belong on dedicated child branches.
- Do not have two agents actively modify the same branch/implementation surface.
- Cross-agent components should meet through explicit shared contracts under `contracts/` and shared project-state contracts rather than copying controller internals or guessing semantics.
- Prototype completion does not automatically authorize integration; the integration owner reviews the exact branch/commit and may cherry-pick, adapt, defer, reject, or reimplement around the proven contract.
- Do not create extra branches for routine tiny fixes; branch when genuine parallel isolation/review value exists.

## Architecture posture

Prefer modular, independently callable components and focused mini-apps where that lowers conflicts and user burden. The eventual main controller should primarily orchestrate project selection/state/status and launch the same underlying applet/core APIs that can run independently.

Shared project state and durable geometry—especially accepted grid coordinates—should be reused rather than forcing repeated clicks or recalculation. A later action should check only its true prerequisites, not require replaying an entire workflow.

Keep Fiji/ImageJ functionality in mature Fiji/ImageJ facilities when that is the best route, but do not prohibit Python-hosted or other officially supported integration modes merely because older architecture placed Fiji in a separate process. Architecture is subordinate to the endpoint.

## Model-cost discipline

Use the least expensive capable model. **Reasoning budget should scale with architectural uncertainty, not code length or file count.** Follow `docs/development/AGENT_MODEL_ROUTING.md` where present.

A failed implementation does not itself authorize a premium model. Prefer bounded research, decomposition, a changed architecture, or a discriminating micro-proof first. Any model/effort tier marked as requiring user approval in the routing document must never be invoked automatically.

## Development behavior

- inspect the actual active implementation before changing behavior;
- preserve working outputs unless change is intentional;
- validate inputs and fail/skip clearly rather than corrupting a batch;
- keep geometry/math explicit and auditable;
- prefer small compatible changes and mature integrations over rewrites;
- do not confuse more code with more progress;
- record durable research/failure lessons only when they prevent rediscovery; do not create chronological debugging diaries;
- use `docs/research/INDEX.md` before researching or substantially changing an endpoint with prior history;
- keep documentation concise by putting detailed policy/specification in the authoritative linked document instead of duplicating it here.
