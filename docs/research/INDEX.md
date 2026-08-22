# Research memory index

Read this index before starting online research or substantially changing an endpoint. Open only the matching topic file unless broader research is genuinely required. Keep this file as routing memory only; detailed research and endpoint debugging evidence belong in the topic file.

| Topic | Status | Endpoint history | Last checked | Current conclusion | Detail |
| --- | --- | --- | --- | --- | --- |
| Fiji four-point runtime / launch lifecycle | active / manual-validation | 5 materially distinct routes | 2026-08-22 | Core export works; fail-closed Fiji RMI reuse and native-size upper-right placement await one manual check. | [fiji-four-point-runtime.md](fiji-four-point-runtime.md) |
| SDL-MCP with Codex | deferred / repeated-failure / shell usable | 3+ setup/integration routes | 2026-08-22 | Shell retrieval works; native MCP remains unreliable and is outside current product work unless explicitly revisited. | [sdl-codex.md](sdl-codex.md) |

Index discipline:
- one row per topic;
- status should stay short (for example `active`, `resolved`, `deferred`, `repeated-failure`);
- endpoint history counts materially different endpoint-level routes, not individual errors/tests; use `—` when no durable failure history is warranted;
- `Current conclusion` should normally stay at or below 30 words;
- `Detail` is a link only;
- do not put search queries, individual errors, test chronology, source lists, or detailed failure explanations here.

Add a new topic only when research or repeated endpoint-level implementation attempts produce evidence worth preserving. Do not turn this index into a development diary.
