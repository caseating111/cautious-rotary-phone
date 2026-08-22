# Research memory index

Read this index before starting online research or substantially changing an endpoint. Open only the matching topic file unless broader research is genuinely required. Keep this file as routing memory only; detailed research and endpoint debugging evidence belong in the topic file.

**Index by user-visible endpoint or durable functional problem, not by whichever technology currently fails.** A topic should remain stable when the implementation changes from one library/protocol/tool to another. Technologies and error-specific attempts belong underneath the endpoint in the detail file.

| Topic / endpoint | Status | Endpoint history | Last checked | Current conclusion | Detail |
| --- | --- | --- | --- | --- | --- |
| Python-controlled interactive Fiji / four-point runtime | active / repeated-failure | 3 materially distinct routes | 2026-08-22 | Exact Fiji runtime still fails before reliable grid/QC; consult prior adapter, validation, and launch/reuse failures before changing this endpoint. | [fiji-four-point-runtime.md](fiji-four-point-runtime.md) |
| SDL-MCP usable from Codex | deferred / repeated-failure / shell usable | 3+ setup/integration routes | 2026-08-22 | Shell retrieval works; native MCP remains unreliable and is outside current product work unless explicitly revisited. | [sdl-codex.md](sdl-codex.md) |

Index discipline:
- one row per stable user-visible endpoint/durable functional problem;
- do not create a new topic merely because a new library, protocol, launcher, wrapper or error is being tried for the same endpoint;
- status should stay short (for example `active`, `resolved`, `deferred`, `repeated-failure`);
- endpoint history counts materially different endpoint-level routes, not individual errors/tests; use `—` when no durable failure history is warranted;
- `Current conclusion` should normally stay at or below 30 words;
- `Detail` is a link only;
- do not put search queries, individual errors, test chronology, source lists, or detailed failure explanations here;
- after a meaningful endpoint failure, the detail file should record at least one technology-independent endpoint search and the current official/recommended route where available before another architectural attempt.

Add a new topic only when research or repeated endpoint-level implementation attempts produce evidence worth preserving. Do not turn this index into a development diary.