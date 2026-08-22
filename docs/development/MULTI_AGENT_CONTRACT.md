# Multi-agent coordination contract

This document defines how Codex/integration work and Gemini/other prototype work may proceed in parallel without overwriting one another or inventing incompatible interfaces.

## Roles

- `workflow-C` is the active integration/product branch. Codex is the normal writer/integrator there unless the user explicitly assigns another agent.
- `geminimain` is the shared Gemini specification/baseline branch.
- Independent Gemini feature work belongs on dedicated child branches such as `gemini-v10`, `gemini-annotation`, `gemini-preprocessing`, etc.
- Two agents should not actively write the same branch or the same implementation surface at the same time.

## Shared-contract boundary

Cross-agent work should meet at explicit contracts rather than by copying controller internals or guessing each other's state.

The machine-facing prototype handshake is under `contracts/` where present. Read `contracts/README.md` before implementing or integrating a component that consumes another agent's output.

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

Codex/integration work should then review the proven branch/commit and choose whether to cherry-pick, adapt, reimplement around the shared contract, defer, or reject it. Prototype completion does not automatically authorize production integration.

## Parallel-work rule

Parallel work is useful when components have narrow, non-overlapping ownership. Do not create parallel branches for routine tiny fixes. Use them when independent agents can genuinely work without touching the same files/endpoint.

## Main-controller versus standalone applets

The eventual main controller is an orchestrator/convenience layer, not the only way components may run. Focused applets should normally be independently runnable and should consume shared project state/contracts. The controller should call the same underlying core/API rather than maintain a second controller-only implementation.

## Conflict/merge discipline

- Before integrating a prototype, fetch current refs and compare the exact prototype commit against current `workflow-C`.
- Resolve conflicts by preserving current production behavior unless the prototype intentionally supersedes it and has evidence.
- Shared specification/contract files should be reconciled deliberately; do not choose `ours`/`theirs` blindly when both branches changed semantics.
- After integration, record the adopted prototype commit or adaptation in the relevant handoff/current-state documentation.

## Efficiency

Keep coordination artifacts concise. The index routes agents; handoffs contain component detail; contracts contain machine-facing semantics. Do not duplicate the full project history in every branch or prompt.