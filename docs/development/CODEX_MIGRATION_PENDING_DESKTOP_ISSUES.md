# Codex migration — pending desktop issues

Documentation-only checkpoint. **Do not treat this file as authorization to implement fixes yet.** The user is still collecting issues before migrating the active work to Codex.

## Desktop test state — 2026-08-22

The current one-plate four-point proof reaches the real Fiji interaction and the four ROI 1-click placements, but the desktop route is not yet working end-to-end.

### 1. Fiji main GUI/window sizing and placement is still unstable

Observed after the recent program-side visibility rescue:

- Fiji/ImageJ can initially appear as an **extremely small/minimal window**, effectively just a tiny title bar/window chrome rather than the usable normal toolbar GUI.
- After cancelling out of alignment, the main `(Fiji Is Just) ImageJ` toolbar can appear in the corner at a more normal size, but its placement is inconsistent.
- Sometimes the Fiji toolbar is partly or wholly off-screen by default; sometimes it is not.
- Therefore the latest Python-side Win32 visibility/position rescue has **not** solved the real desktop behavior reliably.
- Do not assume that merely finding/restoring/moving the top-level Fiji frame guarantees that Java/AWT has finished sizing/layout of the main toolbar.
- AHK v2 remains a convenience layer and must not become the sole mechanism by which Fiji exists/appears, but current program-side positioning is still not reliable enough.

### 2. Placement/confirmation dialogs are no longer being moved upper-left reliably

The four placement dialogs (`1 / 4 — R1C1`, etc.) are appearing large/centrally positioned rather than being moved to the intended upper-left location.

This is a regression relative to the desired AHK v2 behavior. Current AHK design is shell-hook based with one ~120 ms catch-up pass and no permanent polling. Before changing it, inspect whether:

- the Java dialog title is assigned later than the one delayed pass;
- title matching is affected by the rendered title/encoding (desktop showed text similar to `1 / 4 â R1C1` rather than a clean en-dash title);
- the window is created/reparented/resized again after the shell event;
- or the helper is not running/receiving the expected shell event at that point.

Do not blindly return to continuous polling unless desktop evidence requires it.

### 3. Macro parse error after the fourth point blocks QC/export

After successfully placing all four authoritative points and confirming the fourth placement, Fiji reports:

`Error: ';' expected in line 388`

at generated macro code equivalent to:

`halfW = QC_W / 2;`

The debug window shows `halfW` already present as `"108"`, and the parser highlights the division operator. This is a generated ImageJ-macro-language problem and must be diagnosed before QC can run.

Important values immediately before the failure:

- `viewW = 1750`
- `viewH = 1750`
- `roiBoxW = "108"`
- `roiBoxH = "108"`
- `roiBoxSize = 108`
- `QC_W = "108"`
- `QC_H = "108"`
- `gridCols = 12`
- `R1LX = 122`, `R1LY = 540`
- `R1RX = 1558`, `R1RY = 480`
- `R5LX = 142`, `R5LY = 1062`
- `R5RX = 1582`, `R5RY = 1002`
- `gridHX = 1438`, `gridHY = -60`
- `gridVX = 22`, `gridVY = 522`
- `hLen = 1439.2512`
- `vLen = 522.4634`
- `hux = 0.9991`, `huy = -0.0417`
- `vux = 0.0421`, `vuy = 0.9991`

The four-point geometry itself therefore appears to have been calculated sensibly before the parse failure.

Likely investigation area for Codex: `QC_W`/`QC_H` are coming from `call("ij.Prefs.get", ...)` and appear in the debug window as quoted string-like values (`"108"`), whereas `roiBoxSize` became numeric through `maxOf`. The generated ImageJ macro must use unambiguous numeric values before arithmetic. Do not implement this inference yet without inspecting the exact generated macro around line 388.

### 4. CLAHE settings now appear correctly encoded in the generated runtime state

The debug output from this failed run is useful positive evidence. It shows:

- `roiBoxW = "108"`
- `roiBoxH = "108"`
- `roiBoxSize = 108`
- `claheBlock = 356`
- `claheOptions = "blocksize=356 histogram=256 maximum=1000 mask=*None* fast_(less_accurate)"`

This matches the user's requested current settings closely:

- block size approximately 3.3× the one-click ROI dimension; 108 × 3.3 gives ~356 (user described ~355 and requires >3×);
- histogram bins 256;
- maximum slope 1000;
- mask None;
- Fast / less accurate enabled.

The previous issue where CLAHE looked unlike the intended settings should not be assumed to be an option-string mismatch based on this debug state. Whole-image application still matters; the current generated proof explicitly clears an ROI before the CLAHE calls.

### 5. ROI 1-click tool selection worked in this run

Positive evidence from the debug output:

- `roiToolsetPath` resolves to the installed `Roi 1-Click Tools.ijm`;
- `roiClickToolFound = 1`;
- `toolCandidate = 17`;
- all four clicked ROI bounds were 108 × 108.

So automatic discovery/selection of the custom ROI 1-click Rotated Rectangle Click Tool appears to have worked in this desktop run.

### 6. Four-point interaction itself reached all four placements

The user successfully placed:

- R1C1;
- R1C(last);
- R5C1;
- R5C(last).

The failure happened **after** the fourth placement when generated QC geometry code began. Do not regress or replace the authoritative four-point interaction while addressing the later failure.

## Codex token-usage / orchestration considerations

These are migration-design notes, not authorization to install or adopt anything yet.

### A. Avoid repeatedly loading large files/output into the primary Codex context

The user's prior Codex usage was token-heavy while repeatedly editing/reading a large monolithic `.py`. Working from GitHub is not intrinsically token-free: token cost depends on how much source/tool output Codex actually reads, not whether bytes came from a local file or GitHub. The useful optimization is **targeted retrieval**, not merely moving code to GitHub.

Codex should therefore:

- start from `AGENTS.md`, the current-state/handoff docs, and the small active file/test set;
- use symbol/search/diff/range-based reads rather than repeatedly reading whole large files;
- inspect only the relevant surrounding code before editing;
- prefer `git diff`, targeted test failures, bounded log tails, and focused command output;
- periodically compact accumulated findings into a short durable handoff and continue from that rather than carrying dead ends indefinitely.

This matches the existing repository policy that `CURRENT_STATE.md` should identify the small active file/test set.

### B. Subagents for genuinely large read/summarization tasks

Current Codex supports delegating narrower work to mini-model subagents when using a ChatGPT account; this does not inherently require the user's own API key. However, subagent work still consumes Codex/agentic usage and may be accounted separately from the visible primary thread.

Recommended policy: **do not spawn a subagent for every command result.** Delegate when the raw material is genuinely large or parallelizable, for example:

- >20–50k tokens of logs/output/docs;
- multiple sizeable files that primarily need summarization/search;
- broad repository reconnaissance where only a compact answer is needed by the primary agent;
- independent audits/tests that can run in parallel without duplicating active implementation context.

For ordinary small command outputs, direct reading is cheaper and simpler.

Do not hard-code `gpt-5.4-mini` as a permanent model requirement in project policy. Current OpenAI guidance says GPT-5.4/5.4-mini in Codex are being replaced by GPT-5.6 Terra/Luna for ChatGPT-account Codex use after 2026-08-31. Phrase policy functionally: use the **current lower-cost/mini Codex subagent model** for large summarization/reconnaissance tasks where appropriate.

### C. Multi-agent workflow

A modest multi-agent workflow is potentially useful, but do not create an orchestration system merely because it is possible. The primary Codex agent should remain the project manager and final integrator. Delegate **independent bounded subtasks**, such as:

- one agent inspects a generated Fiji macro around an error;
- one audits AHK v2 behavior;
- one runs/searches relevant tests;
- one summarizes a very large log or repository area.

The primary agent must validate and consolidate results before editing. Avoid having multiple agents concurrently edit overlapping files or all independently reread the whole repository; that can increase token use and merge/reasoning overhead rather than reduce it.

External-model orchestration (Gemini/Claude/etc.) is a separate toolchain requiring those services/credentials or a compatible local orchestration layer; ChatGPT Plus by itself does not provide arbitrary third-party model calls through Codex. Do not add that complexity unless measured benefit justifies it.

### D. Candidate context/token-reduction tools to evaluate

Do not install all of these at once. Benchmark one small representative task with and without the candidate and keep it only if it reduces total token/time cost without hurting correctness.

1. **`dreamlx/codeindex` — strongest low-complexity first candidate.**
   - deterministic/tree-sitter structural code navigation;
   - can generate compact `README_AI.md` navigation files without AI enrichment (`--no-ai`), so it can work locally without API usage;
   - project's published benchmark reports about 28% fewer tokens / 19% less wall time on navigation tasks, with no overall quality gain and some noted failure cases;
   - likely fits this repository's preference for simple mature tooling before heavier bespoke/context systems.

2. **`GlitterKill/sdl-mcp` — potentially powerful but heavier.**
   - local MCP server with symbol graph, task-scoped slices, bounded source windows, delta/blast-radius tooling;
   - explicitly targets context-budget reduction;
   - requires Node.js 24+ and MCP setup, so adoption cost is meaningfully higher than a static index;
   - consider only if targeted Git/search/codeindex navigation remains inadequate for the repository as it grows.

3. **`yibie/caveman-codex` — possible output-token reduction, lower priority.**
   - mainly compresses agent language/output style rather than improving code retrieval;
   - may reduce verbosity, but aggressive compression can make debugging/handoffs less legible;
   - do not allow terse-output rules to damage precise Fiji/AHK/debug reasoning. If tested, apply to routine chatter/summaries, not correctness-critical technical explanations.

4. **Command-output reduction (`rtk`-style ideas from the Reddit discussion).**
   - useful principle: prevent huge command output entering context in the first place via `rg`, `head/tail`, test selection, diff filters, and summary scripts;
   - third-party wrappers have mixed user-reported savings and can truncate something later needed, forcing duplicate commands;
   - prefer native bounded commands and targeted retrieval first, then benchmark a wrapper only if shell output remains a measured dominant cost.

### E. Practical default migration strategy

Before installing a complex token-saving stack, use this hierarchy:

1. concise durable `AGENTS.md` + task-specific/current-state docs;
2. small active file/test set in `CURRENT_STATE.md`;
3. targeted search/symbol/range/diff reads, never whole-repo reconstruction by default;
4. bounded shell/test output;
5. periodic compact handoff notes;
6. current mini/lower-cost Codex subagents only for large summarization/reconnaissance or independent bounded parallel tasks;
7. trial `codeindex` structural-only navigation if repository navigation is still a meaningful token cost;
8. only then trial heavier SDL-MCP or other orchestration.

Measure the effect on one or two real tasks before making any candidate mandatory.

## Current migration posture

- Do **not** fix the desktop issues yet; the user has more issues to report before migration.
- Do **not** install new Codex/context/orchestration tools yet; the user is deciding the migration setup.
- Preserve the current code and evidence until the user says to begin implementation/Codex migration.
- When migration begins, Codex should read `AGENTS.md`, `docs/development/IMPLEMENTATION_DECISION_POLICY.md`, `docs/development/CURRENT_STATE.md`, and this file first.
- Runtime target remains Windows + Python 3.14.
- AutoHotkey requirement remains **AHK v2 only**; no AHK v1 compatibility is needed.
- Continue to prefer the mature four-point Fiji + ROI 1-click route rather than returning to detector development.
- Fix desktop failures narrowly and verify the generated ImageJ macro itself before asking the user for another test.
