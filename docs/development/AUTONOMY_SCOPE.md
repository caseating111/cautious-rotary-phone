# Autonomy scope

This file narrows older broad "continue autonomously" guidance for quota-limited/local agent work. For Codex sessions, this policy is authoritative when older wording could be read as permission for open-ended continuous development.

## Default mode: task-scoped autonomy

The agent should act autonomously **inside the user's current requested objective**, but should not continue indefinitely into unrelated improvements merely because useful work remains possible.

Within the active objective, the agent may without routine approval:

- inspect the minimum relevant repository state, symbols, files, diffs, tests, logs, generated artifacts and local tooling;
- choose implementation details, dependencies, mature tools/plugins/packages, small refactors, UI/default details and normal Git actions;
- fix directly discovered bugs/regressions that block or materially compromise the requested objective;
- add or update targeted tests, validation, fixtures and concise documentation needed to make the requested change reliable;
- perform necessary cleanup caused by the requested change;
- use mature external tools, thin glue, macros, AHK v2, Fiji/ImageJ facilities, Pillow and local automation when they reduce user burden;
- delegate genuinely large reading/reconnaissance work to the current lower-cost/mini subagent when this saves primary-agent context;
- record non-blocking uncertainties or future ideas without stopping the current task.

## Normal stopping condition

A session/task should stop when the requested objective is implemented and the feasible validation for that objective has completed, or when further progress genuinely requires user-only information/desktop judgement/authorization.

A completed task, test pass, commit, milestone or manual-validation gate is **not automatically a reason to continue into new work**.

After completing the requested objective, the agent may perform only directly related verification, regression checks, necessary cleanup and concise handoff/state updates. It should then stop and report.

## Do not continue automatically into

Unless the user explicitly asks for broader exploration or continued improvement, do not spend quota/time on:

- speculative new features;
- unrelated optimizations or refactors;
- broad whole-repository audits not required by the task;
- opportunistic architecture work;
- implementing every useful idea discovered during the task;
- repeatedly polishing already-working code for elegance;
- starting the next roadmap item merely because the current one finished;
- open-ended "persistent improvement" loops.

Useful adjacent ideas should normally be recorded as deferred candidates rather than implemented immediately.

## Adjacent fixes

A directly adjacent issue may be fixed autonomously when all of the following are true:

1. it was discovered while executing or validating the current objective;
2. it is clearly real rather than speculative;
3. leaving it unfixed would break, invalidate or materially undermine the requested result;
4. the fix is narrow and low-risk;
5. it does not expand the task into a new subsystem or substantial feature.

Otherwise record it and leave it for a later task.

## User-testing budget

Do not hand the user successive speculative builds. Before requesting manual testing, exhaust feasible automated/static/generated-artifact/local checks for the current objective. If repeated patch -> user test -> failure cycles appear, reassess the route instead of continuing indefinitely.

## Token/context budget

Autonomy does not imply unlimited context consumption. Prefer SDL/symbol/search/diff/bounded reads and targeted tests. Use the current cheaper/mini subagent for genuinely large logs, outputs or repetitive multi-file reading when that preserves the primary agent's allowance. Do not spawn subagents for small tasks where delegation overhead is larger than the saving.

## Explicit broader modes

The user may explicitly request a broader mode such as an audit, roadmap exploration, continuous session, or autonomous improvement pass. When they do, obey the stated scope/time/budget. Even in those modes, the implementation decision policy and stop-loss/user-testing rules still apply.

Absent such an explicit instruction, **task-scoped autonomy is the default**.