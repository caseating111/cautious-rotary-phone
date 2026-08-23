# Gemini start here

This branch exists to let Gemini make useful parallel progress without interfering with the active `workflow-C` writer.

## Read first

Read only:

1. root `AGENTS.md`
2. `docs/development/IMPLEMENTATION_DECISION_POLICY.md`
3. `docs/development/AGENT_MODEL_ROUTING.md`
4. `docs/development/MULTI_AGENT_CONTRACT.md`
5. `docs/development/PROTOTYPE_HANDOFF_STANDARD.md`
6. `docs/gemini/PROTOTYPE_RULES.md`
7. `contracts/README.md`
8. `docs/gemini/GEMINI_INDEX.md`
9. `docs/gemini/FUTURE_WORKFLOW.md` when the assigned prototype depends on or feeds another workflow stage
10. `docs/development/PROJECT_ASSET_CONTRACT.md` when the prototype creates/consumes/transforms reusable project state or geometry
11. the HANDOFF for the prototype you are assigned
12. only the narrow existing project docs/files actually needed for that prototype

Do not reconstruct the full repository history or ingest the current runtime broadly.

Before online research, check `docs/research/INDEX.md`; if a matching endpoint/topic exists, read only that topic file first. **Avoid tunnel vision:** after a meaningful endpoint failure, reopen the solution space and research current official/mature end-to-end and architectural alternatives before repairing the failed mechanism.

Two meaningful attempts that rely on substantially the same architectural assumption trigger the stop-patching circuit breaker. Another cosmetic workaround is not justified without materially new evidence.

## Model-cost boundary

Use the least expensive capable model. Prefer Flash Low for reading/mechanical work and Flash Medium for normal bounded prototype implementation. Sol Light is permitted when a stronger independent reasoning pass is genuinely useful.

**Do not invoke Sol Medium or higher, Claude Sonnet 4.6, Gemini 3.1 Pro High, Claude Opus 4.6, or another comparably expensive tier without explicit user approval.** An endpoint failure does not itself authorize premium escalation. First use bounded official research, decomposition, architectural alternatives, and discriminating micro-proofs with permitted models.

## Ownership

- `workflow-C` is the integration/product branch and is normally owned by Codex/current integrator.
- Do not write to or merge into `workflow-C` from a Gemini prototype task.
- `geminimain` is the shared Gemini specification/baseline branch.
- Use a dedicated child branch for each active implementation stream, for example `gemini-v10`, `prototype/annotation`, or `prototype/preprocessing`. Existing branch names are grandfathered; new branches should be named for the component/domain rather than the model when practical.
- Do not have multiple agents actively edit the same branch/implementation surface.
- Parallelize investigation and bounded independent artifacts; serialize mutation of the production integration surface.

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
- Do not duplicate premium-model review across several model families when one compact independent challenge is sufficient.

## Successful checkpoint

When a prototype reaches a coherent state:

1. run its targeted synthetic tests;
2. update its HANDOFF under `PROTOTYPE_HANDOFF_STANDARD.md`;
3. use the explicit status vocabulary (`EXPLORATORY`, `PROOF PASSED`, `READY FOR INTEGRATION`, `INTEGRATED`, or `ROUTE FAILED`) rather than an unqualified `Proven` claim;
4. update the one-line entry in `GEMINI_INDEX.md`;
5. commit/push that prototype branch;
6. stop rather than automatically integrating it into `workflow-C`.

`PROOF PASSED` means the documented narrow proof succeeded. `READY FOR INTEGRATION` requires an explicit audit against the current shared contracts and current component requirements.

The active `workflow-C` integrator later decides whether to cherry-pick, adapt, reimplement around the contract, defer, or reject it.
