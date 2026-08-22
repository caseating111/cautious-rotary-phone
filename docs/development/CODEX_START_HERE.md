# Codex start here

This is the current bootstrap for migrating active development to local ChatGPT Codex. It supersedes only the older **Codex token/orchestration/tool-ranking advice** in `docs/development/CODEX_MIGRATION_PENDING_DESKTOP_ISSUES.md`. The desktop observations, debug values, unresolved Fiji/AHK/IJM failures, and positive evidence in that file remain authoritative and must not be discarded.

## First-read order

Before implementation, read only:

1. root `AGENTS.md`;
2. `docs/development/IMPLEMENTATION_DECISION_POLICY.md`;
3. `docs/development/CURRENT_STATE.md`;
4. this file;
5. `docs/development/CODEX_MIGRATION_PENDING_DESKTOP_ISSUES.md` for the concrete unresolved desktop evidence.

Do not reconstruct project history or read the whole repository by default.

## Current migration state

- Active durable branch: `workflow-dev`.
- Required current runtime/CI target: Windows + Python 3.14.
- AutoHotkey contract: **AHK v2 only**; AHK v1 compatibility is not required.
- SDL-MCP has been installed globally on the user's Windows machine, including its native addon. At the latest manual check there was no repository SDL config/index yet; repo-local SDL initialization is intentionally being handed to Codex.
- SDL setup used the **Code** embeddings option (Jina symbol embeddings, no file summaries).
- The local repository should become the normal Codex working copy; GitHub remains the durable remote/source of truth.
- Do not install `codeindex`, Caveman, or another orchestration stack during the initial SDL proof.
- Do not change Fiji/AHK/Python runtime behavior until the SDL/Codex setup is verified unless the user explicitly asks to proceed sooner.

## SDL-MCP first

Use SDL-MCP as the first context-reduction trial. Do not reinstall it unless it is genuinely unavailable.

First:

1. verify the local checkout/remote/branch and clean Git state;
2. verify `sdl-mcp` is callable from the Codex shell;
3. inspect current SDL help/docs locally rather than assuming old command syntax;
4. dry-run repo-local SDL initialization/config changes first where supported;
5. initialize/index this repository for Codex using the current supported SDL/Codex integration;
6. run SDL `info`/`doctor` checks;
7. verify Codex can actually call SDL and retrieve relevant symbols/cards/bounded context;
8. prove on representative project symbols that SDL can navigate without reading entire large source files.

Prefer SDL's smallest useful supported tool surface. Do not enable unnecessary services, paid APIs, extra embeddings, or unrelated features merely because they exist.

Generated caches/databases should not be committed unless SDL explicitly requires them as portable project state. Small reproducible repo config/instructions may be committed if useful. Inspect `.gitignore` and SDL's current generated paths before deciding.

## Primary-context/token policy

Primary Codex context is scarce. Optimize **per-model subscription allowance and user time**, not minimum aggregate AI tokens across all services.

- Navigate/search/index before reading source.
- Prefer SDL symbol/card/task context, `rg`, Git diff, exact symbols, and bounded line ranges over whole-file reads.
- Never read a large file in full merely because it is convenient when a bounded read can answer the question.
- Prefer targeted tests and bounded command output (`--tb=short`, selected tests, filtered logs) instead of dumping large output into context.
- For genuinely large reading/summarization work—roughly >20k tokens, multiple sizeable files, or output likely to consume a substantial fraction of the primary context—delegate to the current lower-cost/mini Codex subagent.
- The cheap/mini subagent should return a compact evidence-backed summary with exact file/symbol/error references. Do not use it for small outputs where delegation overhead is larger than the saving.
- Keep architecture/implementation decisions and final verification with the primary Codex agent.
- Do not hard-code a permanent model name for the mini role; use the current lower-cost Codex subagent model available through the user's ChatGPT Codex subscription.

## Planned Gemini / Antigravity role

The user also pays for Google Antigravity/Gemini and wants to use that separate allowance to improve reliability while reducing pressure on Codex quota.

Target architecture after SDL is proven:

`Codex primary writer -> automated narrow review gate -> Antigravity/Gemini read-only reviewer -> concise findings -> Codex verifies/fixes`

Do **not** make Codex and Gemini equal co-managers and do not have both independently ingest the entire repository. Codex remains the sole normal writer/integrator. Gemini should receive a narrow incremental review packet: relevant diff, exact generated runtime artifact, bounded error/test excerpt, and a precise review question.

Prefer a thin local wrapper/direct supported Antigravity invocation over a large bespoke orchestration system. Codex should inspect the installed Antigravity CLI/interface on the user's machine and prove a tiny non-interactive call before integrating it. Do not assume old Gemini CLI syntax is still valid.

Where Antigravity supports cheaper/Flash subagents, use them for large repetitive review input in the same thresholded way as Codex mini agents. Do not spawn subagents for every small task.

Do not initially add `hampsterx/codex-mcp-bridge`: its primary direction is exposing Codex to other MCP clients, while the intended first workflow is Codex calling a narrow Gemini review path. Reconsider only if it demonstrably removes maintenance/user work later.

## Pre-user-test reliability gate

A major objective of this migration is to stop using the user as a parser/debugger for defects that could have been caught locally.

Before requesting another manual desktop test, perform every feasible automated check, including:

- Python compile/static checks and the smallest relevant test set;
- generation of the **exact** runtime artifact that will be executed;
- syntax/parse/startup validation of generated or edited AHK v2 scripts using AHK v2 where feasible;
- inspection/validation of the exact generated ImageJ/Fiji macro, not only its Python generator/template;
- targeted Windows/path/launcher checks where locally possible;
- once the Antigravity review gate is proven, independent narrow Gemini review for risky desktop/generated-script/cross-language changes;
- Codex verification of every Gemini finding before changing code.

Only ask the user to test behavior that genuinely requires visual/desktop/hardware judgement after these gates pass.

## Current desktop blockers to resume after migration setup

Do not redesign the alignment route. The current four-point ROI 1-click workflow reached all four authoritative placements. Resume from the evidence in `CODEX_MIGRATION_PENDING_DESKTOP_ISSUES.md`.

Known blockers include:

- Fiji main GUI can appear extremely small and its final position/size is inconsistent; the latest Python-side visibility rescue is not reliable.
- AHK v2 placement/confirmation dialogs are no longer reliably moved upper-left.
- After the fourth point the generated IJM fails before QC/export with `';' expected` around `halfW = QC_W / 2;`; inspect the exact generated macro around that line before editing the generator.
- Positive evidence to preserve: ROI 1-click tool auto-selection worked; all four 108x108 placements worked; CLAHE runtime options showed block 356 / histogram 256 / maximum 1000 / mask None / fast less-accurate; four-point geometry values looked sensible before the parse failure.

Fix these narrowly after the migration tooling is proven. Do not return to detector development first.

## Initial Codex task boundary

The first Codex session should set up and prove local SDL-MCP integration only, plus minimal repository config/docs required for that integration. It should not fix the Fiji/AHK/IJM problems in the same setup step.

After SDL is proven, establish the thresholded mini-subagent policy. Then build/prove the thin Antigravity review gate. Only after those infrastructure steps are stable should normal runtime debugging resume.