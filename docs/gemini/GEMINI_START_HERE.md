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
7. `docs/development/PROJECT_ASSET_CONTRACT.md` when the prototype creates/consumes/transforms reusable project state or geometry
8. the HANDOFF for the prototype you are assigned
9. only the narrow existing project docs/files actually needed for that prototype

Do not reconstruct the full repository history or ingest the current runtime broadly.

Before online research, check `docs/research/INDEX.md`; if a matching topic exists, read only that topic file first and follow the implementation policy's duplicate-search/logging rules.

## Ownership

- `workflow-C` is the integration branch and is currently owned by another active writer.
- Do not write to or merge into `workflow-C`.
- Prototype work should stay isolated and mostly add new files.
- If multiple Gemini prototype streams run concurrently, create a dedicated branch from `geminimain` for each stream (for example `gemini-v10`, `gemini-annotation`, `gemini-plate-rotation`) rather than having multiple writers edit this branch simultaneously.

## Prototype order

Preferred dependency order is described in `FUTURE_WORKFLOW.md`. Independent prototypes may run in parallel when they do not edit the same files or require an unproven upstream contract.

Start with the smallest useful proof for the assigned component rather than attempting the entire future workflow at once.

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

The active `workflow-C` owner later decides whether to cherry-pick, adapt or reject it.
