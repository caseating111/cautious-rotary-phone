# Multi-agent coordination contract

This document defines how Codex/integration work and Gemini/other prototype work may proceed in parallel without overwriting one another or inventing incompatible interfaces.

## Roles

- `workflow-C` is the active integration/product branch. Codex is the normal writer/integrator there unless the user explicitly assigns another agent.
- `geminimain` is the shared Gemini specification/baseline branch.
- Independent Gemini feature work belongs on dedicated child branches such as `gemini-v10`, `gemini-annotation`, `gemini-preprocessing`, etc.
- Two agents should not actively write the same branch or the same implementation surface at the same time.

## Shared-contract boundary

Cross-agent work should meet at explicit contracts rather than by copying controller internals or guessing each other's state.

The machine-facing prototype handshake is under `contracts/`. Read `contracts/README.md` before implementing or integrating a component that consumes another agent's output.

Shared project/runtime state that must survive between standalone applets is described by `docs/development/PROJECT_ASSET_CONTRACT.md` where present.

A prototype may propose the smallest necessary contract extension, but must not silently redefine existing fields or production semantics.

## Prototype ownership and handoff

A prototype branch should:

1. implement one bounded component;
2. avoid modifying active `workflow-C` runtime files;
3. expose a narrow callable/standalone interface where practical;
4. use synthetic/public fixtures only under the repository privacy rules;
5. run targeted tests for its own component;
6. update its handoff/index with exact branch/commit, interface, prerequisites, tests, limitations, and any proposed contract change;
7. stop at a coherent proof rather than merging itself into `workflow-C`.

`docs/development/PROTOTYPE_HANDOFF_STANDARD.md` defines the integration-facing status vocabulary and minimum handoff evidence. `HANDOFF.md` is the mandatory entry point for evaluating a prototype; referenced contracts, fixtures, tests, and executable behavior remain authoritative evidence.

Codex/integration work should then review the exact branch/commit and choose whether to cherry-pick, adapt, reimplement around the shared contract, defer, or reject it. Prototype completion does not automatically authorize production integration.

## Parallelize investigation; serialize production mutation

Parallel work is encouraged for **investigation and bounded independent artifacts** when ownership does not overlap. Good parallel work includes:

- official/current documentation research;
- independent architecture comparisons;
- micro-prototypes with explicit contracts;
- synthetic fixture/test generation;
- review of a compact architecture/evidence packet;
- separate feature branches whose implementation surfaces do not overlap.

Production/integration mutation is serialized. Only **one active writer** should modify a given production integration surface at a time, especially `workflow-C` controller/runtime files.

Parallel reasoning is not permission for parallel mutation. Multiple agents may investigate alternatives simultaneously, but their evidence should converge into one chosen route before one writer changes the integrated implementation.

Avoid patterns where several agents/subagents independently rewrite the same controller, launcher, macro, or shared contract. That multiplies merge conflict and architectural drift rather than useful parallelism.

## Parallel-work examples

Parallel work is useful when components have narrow, non-overlapping ownership. Examples:

- Codex stabilizes the current Fiji/grid runtime while Gemini explores the V10 adapter;
- one prototype branch proves plate preprocessing while another proves annotation from synthetic contracts;
- several permitted subagents independently inspect PyImageJ/Jaunch/Appose evidence while the parent/integrator makes one architecture decision;
- the integration branch consumes a completed prototype only after the active runtime checkpoint is coherent.

Do not create parallel branches for routine tiny fixes. Use them when independent agents can genuinely work without touching the same files/endpoint.

## Model-cost and escalation coordination

Model selection follows `docs/development/AGENT_MODEL_ROUTING.md` where present. Use the least expensive capable model; model cost should scale with architectural uncertainty, not file count or code length.

A stop-patching/endpoint circuit breaker does **not** authorize automatic premium-model escalation. If the routing policy requires user approval for a model/effort tier, request that approval before invoking it and continue other non-blocked useful work with permitted models when possible.

## Main-controller versus standalone applets

The eventual main controller is an orchestrator/convenience layer, not the only way components may run.

Focused applets should normally be independently runnable and should consume shared project state/contracts. The controller should call the same underlying core/API rather than maintain a second controller-only implementation.

Grid registration should eventually be separable as a producer of a durable `GridCoordinateAsset`; downstream annotation, visibility, crop export, and composition consume that asset rather than rerunning alignment.

## Conflict/merge discipline

- Before integrating a prototype, fetch current refs and compare the exact prototype commit against current `workflow-C`.
- Resolve conflicts by preserving current production behavior unless the prototype intentionally supersedes it and has evidence.
- Shared specification/contract files should be reconciled deliberately; do not choose `ours`/`theirs` blindly when both branches changed semantics.
- After integration, record the adopted prototype commit or adaptation in the relevant handoff/current-state documentation.

## Efficiency

Keep coordination artifacts concise. The index routes agents; handoffs contain component detail; contracts contain machine-facing semantics. Do not duplicate the full project history in every branch or prompt.
