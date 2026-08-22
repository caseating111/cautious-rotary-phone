# SDL-MCP with Codex

## Goal
Reduce primary-agent context use with bounded repository retrieval without allowing infrastructure troubleshooting to displace product work.

## Searches tried
Prior exact search strings were not durably recorded. Do not reconstruct them retroactively.

## Useful findings
- SDL-MCP 0.13.3 installed successfully with native addon support.
- A validated LadybugDB graph for repo id `workflow-c` was created and shell/CLI retrieval succeeded, including bounded symbol and context retrieval.
- Explicit SDL config path and repo id are important; folder name/absolute path are not interchangeable with SDL's configured repo id.

## Ruled-out / failed local routes
- Repeated attempts to make native Codex MCP retrieval reliable consumed disproportionate setup time.
- Fresh native MCP sessions reached SDL but still failed LadybugDB initialization despite a valid graph/config; this was treated as a stop-loss point rather than continuing infrastructure work.

## Current preferred route / current unknown
Use bounded SDL CLI/shell retrieval when it clearly saves context. Native Codex MCP repair is deferred and must not block current product work unless the user explicitly makes it a task.

## Re-search triggers
Revisit only if SDL/Codex integration materially changes, a newer SDL version documents a direct fix, shell retrieval stops working, or the user explicitly asks to repair native MCP integration.
