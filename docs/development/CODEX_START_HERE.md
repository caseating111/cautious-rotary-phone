# Codex start here

This is the concise bootstrap for normal local Codex work on `workflow-C`. Current repository state and the documents below outrank older migration-era instructions.

## First-read order

Before implementation, read only:

1. root `AGENTS.md`;
2. `docs/development/IMPLEMENTATION_DECISION_POLICY.md`;
3. `docs/development/AGENT_MODEL_ROUTING.md`;
4. `docs/development/AUTONOMY_SCOPE.md`;
5. `docs/development/IMAGE_BLIND_TESTING.md`;
6. `docs/development/CURRENT_STATE.md`;
7. `docs/development/MANUAL_VALIDATION_BACKLOG.md` when desktop/manual checks are relevant;
8. this file;
9. `docs/development/WORKFLOW_ROADMAP.md` when selecting/confirming a feature stage;
10. `docs/development/V10_WORKBOOK_CONTRACT.md` when working on V10 integration;
11. `docs/development/MULTI_AGENT_CONTRACT.md`, `docs/development/PROTOTYPE_HANDOFF_STANDARD.md`, and `contracts/README.md` when consuming, reviewing, or integrating work from another agent/prototype branch;
12. the matching `docs/research/INDEX.md` topic before researching or changing an endpoint with prior failure history.

Do not reconstruct project history or read the whole repository by default.

## Current durable environment

- Active integration branch: `workflow-C`.
- `workflow-dev` is a pre-Codex development line/snapshot; do not advance it in parallel with routine `workflow-C` work.
- Current runtime/CI target: **Windows + Python 3.14**.
- AutoHotkey contract: **AHK v2 only**.
- GitHub is the durable remote/source of truth; the local checkout is the normal Codex working copy.
- SDL-MCP shell/CLI retrieval can be used when helpful. Native Codex MCP database initialization has been unreliable; do not spend product-development time repairing it unless explicitly tasked.

## Task scope

Default behavior is **task-scoped autonomy**, not open-ended improvement. Complete the requested objective plus directly required regression fixes, targeted validation, cleanup, and concise state update, then stop.

Record worthwhile adjacent ideas instead of automatically implementing unrelated roadmap work.

## Anti-tunnel-vision / research trigger

`AGENTS.md` and `IMPLEMENTATION_DECISION_POLICY.md` are authoritative.

After the first meaningful endpoint failure, do not search only for ways to repair the failing technology. Restate the user-visible endpoint without implementation terminology, check prior endpoint memory, research current official/mature end-to-end solutions and architectural alternatives, then prove the smallest uncertain property before another production implementation attempt.

Different errors blocking the same user-visible outcome remain one continuing endpoint failure. Existing custom code is sunk cost and may be deleted/replaced when a mature route is better.

Two meaningful attempts relying on substantially the same architectural assumption trigger the stop-patching circuit breaker in `AGENT_MODEL_ROUTING.md`; another cosmetic variation is not justified without materially new evidence.

## Model-cost boundary

Use the least expensive capable model. Routine work should normally stay with Luna/Terra or comparable low-cost workhorse models; Sol Light is permitted when stronger reasoning is genuinely useful.

**Do not invoke Sol Medium or higher, Claude Sonnet 4.6, Gemini 3.1 Pro High, Claude Opus 4.6, or another comparably expensive tier without explicit user approval.** Reaching an architectural escalation point does not authorize premium-model use. Prepare a compact escalation packet and ask first; continue other non-blocked useful work with permitted models where possible.

## Image-blind privacy contract

`docs/development/IMAGE_BLIND_TESTING.md` is a hard local-testing rule.

Real/sample image pixels and pixel-bearing derivatives must never be opened, previewed, rendered, OCRed, screenshotted, encoded, or supplied to Codex/another model. Codex may pass external image paths to local Fiji/ImageJ and consume only text/structural/numeric telemetry.

Before every real-image/Fiji verification, use the actual active config and run the image-blind path check documented in `IMAGE_BLIND_TESTING.md`. Proceed only when it passes. If visual judgement is genuinely required, add one concise item to `MANUAL_VALIDATION_BACKLOG.md` for the user.

Real/source images, crops, matrices, and pixel-bearing temp data stay outside the repository.

## Multi-agent / prototype integration

Read `docs/development/MULTI_AGENT_CONTRACT.md` when another agent is involved.

Current model:

- Codex is the normal writer/integrator on `workflow-C`.
- `geminimain` is the shared Gemini specification baseline.
- Gemini may implement isolated components on dedicated branches such as `gemini-v10` or other feature-specific branches.
- Gemini is **not limited to read-only review**: bounded standalone prototypes are valid parallel work when they do not touch the active `workflow-C` implementation surface.
- Parallelize investigation and bounded independent artifacts; serialize mutation of the production integration surface.
- No two agents should actively write the same branch/implementation surface at once.
- Cross-agent components meet through explicit shared contracts under `contracts/` plus project-state contracts, not by copying controller internals.
- Prototype completion does not automatically merge into production. Codex reviews the exact branch/commit and may cherry-pick, adapt, defer, reject, or reimplement around the shared contract.

When evaluating a prototype, begin with its `HANDOFF.md` under `PROTOTYPE_HANDOFF_STANDARD.md`, then the referenced contracts, fixtures and targeted verification evidence. `PROOF PASSED` is not automatically `READY FOR INTEGRATION`.

For narrow review-only tasks, Gemini/other agents may still receive a compact diff/generated-artifact/error packet, but that is one use case rather than the entire multi-agent architecture.

## Shared contracts

`contracts/README.md` and its schemas are the versioned machine-facing handshake for isolated prototype components and eventual integration.

Do not silently change an existing contract field's meaning. If production needs a new shared field, identify the concrete use case and make the smallest compatible change where practical.

Reusable geometry/project state, especially accepted grid coordinates, is described in `PROJECT_ASSET_CONTRACT.md` where relevant. The accepted grid result is a durable project asset, not merely an immediate crop-export intermediate.

## Context/token efficiency

- Navigate/search/index before reading source.
- Prefer bounded symbol/file ranges, diffs, targeted logs, and exact generated artifacts over whole-file dumps.
- Reuse existing valid test/research evidence; do not rerun unchanged broad tests without a concrete reason.
- Delegate genuinely large repetitive reading/review to a cheaper available subagent when useful, but keep architecture decisions and final verification with the primary integrator.
- Keep handoffs and status updates concise; durable details belong in the relevant topic/handoff/contract document.

## Testing and user-validation gate

Use targeted, minimum-sufficient validation under `IMPLEMENTATION_DECISION_POLICY.md`. Expand testing only when failures or evidence of broader regression justify it, or when the user explicitly requests broader testing.

Do every feasible image-blind/local check before asking the user for manual validation. Batch related visual/manual checks rather than repeatedly interrupting the user.

A known Codex sandbox issue can prevent Python `tempfile` setup before test code runs. If the exact documented setup-time permission failure recurs, do not waste time trying many TEMP/TMP locations; use one narrow approved test command when necessary.

## Current work source of truth

`docs/development/CURRENT_STATE.md` contains the active implementation state, small working file/test set, pending manual validation, and exact next action.

Older migration documents may retain useful historical evidence, but they are **not** startup authority and should not override current state, endpoint research memory, or current contracts.
