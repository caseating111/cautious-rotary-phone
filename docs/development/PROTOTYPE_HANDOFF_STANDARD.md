# Prototype handoff standard

This document defines the minimum integration-facing record for isolated prototype branches. It exists so the integration owner can evaluate useful work without reconstructing the prototype's development history.

## Status vocabulary

Use these statuses deliberately:

- `EXPLORATORY` — architecture/interface still being investigated; no integration claim.
- `PROOF PASSED` — the explicitly documented narrow proof succeeded against the stated fixture/conditions. This does **not** imply current full requirements are satisfied.
- `READY FOR INTEGRATION` — the prototype has been re-audited against the **current** shared contracts and current component requirements, its stated limitations are acceptable/known, and the integration owner has enough evidence to evaluate adoption.
- `INTEGRATED` — an integration owner has adopted/adapted the prototype into the integration/product branch and recorded the source branch/commit or equivalent lineage.
- `ROUTE FAILED` — the attempted route did not satisfy the endpoint. Preserve only the evidence needed to avoid repeating the same assumption; durable endpoint failures belong in `docs/research/<endpoint>.md`.

Do not use `Proven` as an unqualified synonym for production readiness. A proof can remain valid while later-expanded requirements make the prototype not yet `READY FOR INTEGRATION`.

## HANDOFF.md is the integration entry point

Each prototype branch should maintain one concise component `HANDOFF.md`. The handoff is the mandatory human/agent-facing entry point, but it is not the sole authority: referenced schemas/contracts, fixtures, tests, and executable behavior remain authoritative machine evidence.

A useful handoff should contain:

```text
Status:
Endpoint:
Branch:
Commit:

What was proven:
What was NOT proven:

Public interface:
Input contract:
Output contract:
Shared schemas used:

Fixture(s):
Verification command(s):
Verification result:

Dependencies:
External software/plugins required:

Known limitations:
Failed/abandoned routes relevant to integration:
Human/manual validation still required:

Files the integrator should inspect:
Files the integrator normally should NOT need to inspect:

Recommended integration/adaptation:
Contract changes proposed:
```

Omit empty boilerplate where it adds no value, but do not hide material limitations or unproven assumptions.

## Integration evidence rule

The integrator should normally begin with:
1. the component `HANDOFF.md`;
2. referenced shared schemas/contracts;
3. the exact minimal fixture(s);
4. the exact targeted verification command/result;
5. only then the implementation files/diff needed to decide integration.

Do not require the integrator to read chronological scratchpads, full branch history, or every source file merely to understand what a prototype does.

## Updating older prototypes

When requirements or shared contracts expand after a prototype's original proof:
- preserve the old proof claim accurately;
- downgrade/relabel status from an overbroad `Proven` claim if necessary;
- re-audit only the newly relevant requirements;
- add targeted tests for materially new semantics;
- mark `READY FOR INTEGRATION` only after the current contract is satisfied or limitations are explicitly accepted.

This is especially important for long-lived prototype branches developed from earlier, shorter specifications.
