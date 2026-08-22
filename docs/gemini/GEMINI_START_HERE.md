# Gemini start here

This branch exists to let Gemini make useful parallel progress without interfering with the active `workflow-C` writer.

## Read first

Read only:

1. root `AGENTS.md`
2. `docs/development/IMPLEMENTATION_DECISION_POLICY.md`
3. `docs/gemini/PROTOTYPE_RULES.md`
4. `contracts/README.md`
5. `docs/gemini/GEMINI_INDEX.md`
6. `docs/gemini/FUTURE_WORKFLOW.md` when the assigned prototype depends on or feeds another workflow stage
7. `docs/development/PROJECT_ASSET_CONTRACT.md` when the assigned prototype creates/consumes reusable project state
8. the HANDOFF for the prototype you are assigned
9. only the narrow existing project docs/files actually needed for that prototype

Do not reconstruct the full repository history or ingest the current runtime broadly.

Before online research, check `docs/research/INDEX.md`; if a matching endpoint/topic exists, read only that topic file first and follow the implementation policy's duplicate-search/logging rules.

**Avoid tunnel vision after a failed endpoint.** Do not frame follow-up research only around repairing the library/protocol/architecture that just failed. Restate the user-visible endpoint without that implementation terminology, search current official/mature end-to-end solutions and architectural alternatives first, then prove the smallest uncertain property before integration. Different technical errors blocking the same outcome remain one endpoint failure.

## Ownership

- `workflow-C` is the integration branch and is currently owned by another active writer.
- Do not write to or merge into `workflow-C`.
- Prototype work should stay isolated and mostly add new files.
- `geminimain` is the shared Gemini specification/baseline branch. Dedicated implementation branches such as `gemini-v10` should preserve their proven work while periodically syncing relevant shared documentation/contracts.

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
- Keep checkpoint handoffs short so the eventual integrator can evaluate the prototype without consuming large context.

## Successful checkpoint

When a prototype reaches a coherent proven state:

1. run its targeted synthetic tests;
2. update its HANDOFF;
3. update the one-line entry in `GEMINI_INDEX.md`;
4. commit/push that prototype branch;
5. stop rather than automatically integrating it into `workflow-C`.

The active `workflow-C` owner later decides whether to cherry-pick, adapt or reject it.