# Agent model routing

This document is advisory routing for the models currently available to the user. It may be updated as model availability, quotas, pricing, or capability changes. Durable engineering principles live in `AGENTS.md`, `IMPLEMENTATION_DECISION_POLICY.md`, and `MULTI_AGENT_CONTRACT.md`.

## Governing principle

**Reasoning budget scales with architectural uncertainty, not code length, file count, or apparent task difficulty.** Use the least expensive capable model. Prefer reducing the problem, researching the current official solution, changing architecture, or running a discriminating micro-proof before increasing model cost.

A failed implementation does not itself authorize a more expensive model.

## Current routing ladder

### Tier 0 — cheap mechanical work; autonomous

Prefer:
- Gemini 3.7 Flash Low (or comparable Flash Low);
- Codex Luna.

Use for repository navigation, file reading, concise documentation maintenance, test execution, fixture generation, mechanical edits, formatting, obvious localized fixes, and other low-uncertainty work.

### Tier 1 — normal workhorse engineering; autonomous

Prefer:
- Gemini 3.7 Flash Medium;
- Codex Terra Light or Medium.

Use for most bounded glue implementation, adapters, standalone prototypes, normal debugging on a proven architecture, package integration with a clear contract, targeted tests, and routine refactoring needed by the task.

This tier should handle most repository work.

### Tier 2A — stronger reasoning still permitted autonomously

Permitted:
- GPT-5.6 Sol Light.

Use only when the task genuinely benefits from stronger cross-system reasoning, architecture comparison, integration review, or ambiguity resolution that Tier 1 has not resolved efficiently. Do not select Sol Light merely because a task is large.

### Tier 2B — premium escalation; explicit user approval required

Do **not** invoke without explicit user approval:
- GPT-5.6 Sol Medium or higher;
- Claude Sonnet 4.6;
- another comparably expensive model not already covered above.

When this tier appears useful, first prepare a compact escalation packet containing the endpoint, evidence, routes already tried, current official/mature alternatives, and the smallest unresolved decision. Ask the user before invoking the premium model.

Reaching an endpoint circuit breaker does not itself authorize this tier. Continue other independent useful work with permitted models where possible.

### Tier 3 — emergency premium; explicit user approval required and exceptional

Avoid unless a high-value problem remains unresolved after cheaper research, decomposition, and Tier 2A reasoning:
- GPT-5.6 Sol High or above;
- Gemini 3.1 Pro High;
- Claude Opus 4.6;
- equivalent highest-cost reasoning modes.

These are emergency resources, not routine stages. Ask the user first and explain why cheaper routes are insufficient.

## Endpoint circuit breaker

Ordinary defects such as typos, syntax errors, malformed fixtures, narrow regressions, and obvious argument mistakes do not count toward this circuit breaker.

After the first **meaningful endpoint/integration failure**, follow the endpoint-first research rule in `IMPLEMENTATION_DECISION_POLICY.md` before another speculative implementation attempt.

If **two meaningful implementation attempts relying on substantially the same architectural assumption** fail to achieve the endpoint, stop patching that route. Do not attempt a third workaround, fallback, compatibility layer, or cosmetic variation unless new evidence materially changes the underlying assumption.

At that point:
1. update the existing `docs/research/<endpoint>.md` record rather than creating a debugging diary;
2. reopen the solution space at the endpoint/architecture level;
3. use cheap/current official research first;
4. identify the smallest discriminating proof for the best alternative;
5. use Tier 0/1/2A models for that proof when sufficient;
6. request user approval only if Tier 2B/3 reasoning still appears worthwhile.

The circuit breaker is about **stopping implementation-token waste**, not automatically escalating model cost.

## Horizontal escalation before vertical escalation

Prefer independent perspective or a changed task framing before a more expensive reasoning level. Examples:
- Terra implementation fails -> Flash researches current official alternatives -> Terra runs the new micro-proof;
- Gemini prototype fails -> Sol Light reviews the endpoint/assumptions rather than rewriting the whole prototype;
- Codex implementation is uncertain -> another permitted model reviews only the architecture evidence/contract rather than duplicating the implementation.

Do not send the same large codebase to several premium models for routine duplicate review.

## Cross-model review

Use independent review selectively when disagreement or architectural assumptions matter. A reviewer should normally receive a compact packet: endpoint, contract, relevant diff/interface, targeted evidence, and unresolved question.

Premium reviewers should challenge assumptions or choose among architectures; cheaper workhorse models should normally perform the resulting implementation/proof.

## Quota posture

Target the overwhelming majority of work at Tier 0–1. Tier 2A should be occasional. Tier 2B and Tier 3 should be rare and are never automatic.

If the project completes without using Tier 3, that is preferable.
