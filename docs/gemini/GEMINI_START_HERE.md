# Gemini start here

This branch exists to let Gemini make useful parallel progress without interfering with the active `workflow-C` writer.

## Read first

Read only:

1. root `AGENTS.md`
2. `docs/development/IMPLEMENTATION_DECISION_POLICY.md`
3. `docs/development/MULTI_AGENT_CONTRACT.md`
4. `docs/gemini/PROTOTYPE_RULES.md`
5. `contracts/README.md`
6. `docs/gemini/GEMINI_INDEX.md`
7. `docs/gemini/FUTURE_WORKFLOW.md` when the assigned prototype depends on or feeds another workflow stage
8. `docs/development/PROJECT_ASSET_CONTRACT.md` when the prototype creates/consumes/transforms reusable project state or geometry
9. the HANDOFF for the prototype you are assigned
10. only the narrow existing project docs/files actually needed for that prototype

Do not reconstruct the full repository history or ingest the current runtime broadly.

Before online research, check `docs/research/INDEX.md`; if a matching endpoint/topic exists, read only that topic file first. **Avoid tunnel vision:** after a meaningful endpoint failure, reopen the solution space and research current official/mature end-to-end and architectural alternatives before repairing the failed mechanism.

## Ownership

- `workflow-C` is the integration/product branch and is normally owned by Codex/current integrator.
- Do not write to or merge into `workflow-C` from a Gemini prototype task.
- `geminimain` is the shared Gemini specification/baseline branch.
- Use a dedicated child branch for each active implementation stream, for example `gemini-v10`, `gemini-annotation`, or `gemini-preprocessing`.
- Do not have multiple agents actively edit the same branch/implementation surface.

## Prototype order

Preferred dependency order is described in `FUTURE_WORKFLOW.md`. Independent prototypes may run in parallel when they do not edit the same files or require an unproven upstream contract.

Start with the smallest useful proof for the assigned component rather than attempting the entire future workflow at once.

## Standalone applet rule

Future mini-apps should be independently runnable without the main controller. The main controller is an orchestrator/convenience layer. Applets should consume shared project state, check only their true prerequisites, and use the same core implementation whether launched standalone or from the controller.

## Efficiency

- Optimize for a useful isolated proof, not production completeness.
- Prefer mature packages/software and thin glue.
- Use targeted tests; do not broadly regression-test the active application.
- Do not repeatedly read large existing files when a narrow contract or bounded excerpt is enough.
- Reuse already-proven project state rather than making another component rediscover it.
- Keep checkpoint handoffs short so the eventual integrator can evaluate the prototype without consuming large context.

## Successful checkpoint

When a prototype reaches a coherent proven state:

1. run its targeted synthetic tests;
2. update its HANDOFF;
3. update the one-line entry in `GEMINI_INDEX.md`;
4. commit/push that prototype branch;
5. stop rather than automatically integrating it into `workflow-C`.

The active `workflow-C` integrator later decides whether to cherry-pick, adapt, reimplement around the contract, defer, or reject it.