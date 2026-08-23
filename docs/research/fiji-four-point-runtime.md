# Python-controlled interactive Fiji / four-point runtime

## Goal / endpoint
Provide **one reliable interactive Fiji session controlled/orchestrated from the Python workflow**, while preserving normal Fiji GUI interaction and the proven four-click grid workflow, without duplicate Fiji/ImageJ windows, delayed launchers, or fragile custom process attachment.

The four-click interaction itself is no longer the main uncertainty. The current endpoint problem is how the Python application should correctly own/start/control an interactive modern Fiji session.

## Current state
The four-click → grid → Accept → export path has worked manually. Existing-instance launch/control has nevertheless failed through multiple materially different routes. The latest fail-closed RMI route also failed immediately against the user's open Fiji instance, and a separate regular ImageJ window still appeared in the observed workflow.

**Architecture reset required before another launcher/IPC implementation attempt.** Do not repair RMI/socket/direct-`ij.ImageJ` again merely because those are the mechanisms already implemented. Follow `IMPLEMENTATION_DECISION_POLICY.md`: restate the endpoint without those technologies, research current official/mature end-to-end Fiji/Python integration architectures, and prove the smallest critical GUI-interaction property before modifying production launcher code.

## Mandatory pre-next-attempt checkpoint

**Endpoint:** A Python application controls one interactive Fiji session, can run the required Fiji/ImageJ/IJ1 operations and retain user GUI interaction, with one GUI/JVM and no duplicate application instance.

**Current approach:** custom existing-instance lifecycle built around Fiji/ImageJ legacy single-instance behavior, direct IJ1/socket experiments, and most recently an RMI bridge.

**Why it failed:** direct `ij.ImageJ` created a separate regular ImageJ GUI; the latest RMI route reported that the existing-instance RMI endpoint was not found, and the user still observed an extra regular ImageJ instance.

**Official/mature alternatives requiring bounded proof:** modern Fiji/Jaunch invocation; PyImageJ with Python as host in interactive GUI mode; Fiji/Jaunch Python mode; direct modern Fiji script/command invocation; Appose where separate Python workers are actually advantageous. These are candidates, not assumptions.

**Smallest next proof:** without changing production runtime, prove whether the user's installed Fiji can be started/owned from Python via a current supported route, show a real Fiji GUI, retain IJ1 legacy/plugin access, and support a synthetic/manual GUI interaction or harmless macro marker without starting a second GUI/JVM.

## Research history

### Searches tried
Prior exact online search strings were not durably recorded. Do **not** invent them retroactively.

Searches run on 2026-08-22 after the earlier manual failures:
- `ImageJ macro string arithmetic ')' expected parseFloat call ij.Prefs.get`
- `Fiji Windows existing instance macro command line RMI IJ.getInstance null`
- `site:forum.image.sc Fiji existing instance run macro Windows`
- `site:stackoverflow.com ImageJ run macro existing instance`
- GitHub issue searches: `repo:imagej/imagej-legacy SingleInstance`, `repo:imagej/imagej-legacy RMI stub`, and `repo:imagej/imagej-legacy macro existing instance`

These searches were too implementation-centered to satisfy the strengthened endpoint-first policy for the next architectural attempt. Before another launcher/control implementation, perform at least one technology-independent query such as `current supported way for Python application to control interactive Fiji GUI` and explicitly check current official Fiji/ImageJ Python/launcher integration documentation.

Do not repeat the older equivalent RMI/socket/legacy-launcher searches unless new evidence specifically makes one relevant.

### Useful findings already established
- Production macro generation is the intended single source of truth for ROI 1-click adaptation.
- Exact generated artifacts matter more than generator-only checks: manual Fiji execution exposed deterministic IJM failures after synthetic/generator checks passed.
- AutoHotkey contract is v2 only.
- Intended preview CLAHE behavior is two applications using block size approximately 3.3x ROI dimension, histogram 256, maximum slope 1000, mask None, fast/less-accurate.
- ImageJ's official macro reference states that `call()` returns a string and `parseFloat(string)` converts it to a numeric value. Saved ROI dimensions must therefore be converted where read, before CLAHE or QC arithmetic.
- ImageJ legacy's `SingleInstance` source forwards `-macro <path>` to a running legacy instance, but that does **not** prove it is the right modern architecture for this application's current Fiji installation.
- `WindowOrganizer.showAll()` unconditionally calls `IJ.getInstance().toFront()`. It is incompatible with the observed forwarded-macro state where `IJ.getInstance()` is null; main-frame placement should remain outside that macro command.
- The direct-IJ1 and RMI work established useful failure boundaries, but neither is now the presumptive architecture.

### Modern architecture candidates to research/prove before another repair

Do not select one merely because it sounds promising; inspect the current installed versions and official docs, then prove the key property cheaply.

1. **Jaunch / current Fiji launcher**
   - Fiji's modern launcher path should be treated separately from the legacy ImageJ launcher/runtime assumptions.
   - Inspect the installed Jaunch/Fiji configuration and current `--help`/`--dry-run`/script-command behavior.
   - Determine whether Jaunch is only the correct startup layer or whether its current Fiji configuration can also satisfy command delivery/reuse needs.

2. **PyImageJ with Python as host, interactive GUI mode**
   - Strong architectural fit because the product is already Python-based and requires visual Fiji interaction.
   - Prove local-Fiji initialization, GUI display, IJ1 legacy compatibility, access to the existing custom toolset/plugins, and a minimal manual/synthetic four-click-style interaction.
   - If successful, evaluate how much custom launcher/RMI/socket/window glue can be removed rather than preserved.

3. **Fiji Python mode (`--python`)**
   - Investigate current Windows support using the actually installed Jaunch/Fiji version.
   - Historical Windows issues must not be assumed current; inspect the current status/fix and test the installed version rather than pinning conclusions to a 2025 report.

4. **Direct modern Fiji script/command invocation**
   - Test current supported Fiji/Jaunch script or command entry points and whether they reuse/own the intended GUI in this installation.
   - Do not substitute a plain `ij.ImageJ` JVM launch for this test.

5. **Appose**
   - Evaluate as a separate-process bridge when isolated Python worker environments or heavy Python processing are advantageous.
   - Do not adopt it merely to solve GUI ownership if PyImageJ/modern Fiji Python integration is simpler.

### Fresh endpoint-first check — 2026-08-23

Current official PyImageJ guidance documents Python-hosted interactive initialization (`imagej.init(..., mode="interactive")`), explicit UI display (`ij.ui().showUI()`), and repeated macro/script execution through the same gateway. This is a materially different ownership model from repeatedly launching Fiji with `-macro` and is now the preferred next micro-proof.

Jaunch/Fiji documents `--no-splash`, but no supported option was found for suppressing the separate observed `Launching Fiji...` status window. The bounded AHK hide/lower rule is therefore only a UI workaround. It must not be treated as evidence that launcher reuse or macro delivery is reliable.

### Bounded PyImageJ ownership proof — 2026-08-23

The configured Miniforge Python 3.11 environment already contained PyImageJ. An image-blind proof started the configured Fiji directory in interactive mode, showed its UI, and ran two harmless macro markers in the same gateway. However, PyImageJ used Java 11 while installed Fiji extensions include Java-21 class files, causing plugin-discovery/class-version failures. Do not replace the production launcher with PyImageJ unless its JVM compatibility with the installed Fiji distribution is resolved first.

## Endpoint debugging / failure history

### Route 1 — ROI 1-click adapter applied in both production and proof preparation
**What was tried:**
The ROI 1-click adapter was applied during production macro generation and then applied again by the proof-preparation layer.

**Observed endpoint result:**
The proof failed contract validation before a usable four-point run could proceed.

**What this established:**
The proof layer was duplicating a transformation that already belonged to production macro generation. Production generation must be the single source of truth; the proof layer should only narrow metadata.

**Reusable lesson:**
Do not reintroduce a second ROI-adapter application under a different proof/helper name unless new evidence shows the production contract has changed.

**Disposition:** ruled out; removed in commit `21a04b0`.

### Route 2 — Generator/proof checks treated as sufficient IJM endpoint validation
**What was tried:**
Synthetic and generated-artifact checks were used to validate the macro path before asking for manual Fiji verification.

**Observed endpoint result:**
Those checks passed, but actual Fiji later rejected the generated IJM after the fourth click with parser/arithmetic failures. Runtime telemetry established that saved ROI dimensions had entered arithmetic as strings.

**What this established:**
Generator/static validation alone is not sufficient evidence that the exact emitted ImageJ macro is accepted by the real Fiji runtime.

The source-of-truth fix converts `call("ij.Prefs.get", ...)` with `parseFloat()` at ingestion. A hidden image-blind run through installed Fiji later executed the exact preference conversion, geometry, QC overlay construction and both CLAHE calls on synthetic data successfully.

**Reusable lesson:**
Test the exact generated runtime IJM through Fiji's actual parser/runtime whenever feasible and image-blind; do not report the deterministic Fiji path clean based only on generator-level checks.

**Disposition:** generator-only validation is ruled out as endpoint proof.

### Route 3 — Existing Fiji launch/reuse lifecycle via launcher/single-instance assumptions
**What was tried:**
The proof/controller attempted to run while Fiji was already open using launcher/single-instance and macro invocation behavior.

**Observed endpoint result:**
The controller attempted another Fiji launch, left `Launching Fiji...` visible, and produced `Macro_Runner`/`IJ.getInstance()` lifecycle problems. Indirect window-geometry inference also proved fragile.

Local inspection established that the installed Fiji launch stack exposed both Jaunch-era options and legacy single-instance internals, but those facts did not prove a reliable end-to-end ownership/control architecture.

**Reusable lesson:**
Do not return to indirect geometry-based Fiji main-window inference or the same relaunch/Macro_Runner lifecycle under cosmetic rewrites.

**Disposition:** unreliable.

### Route 4 — Direct IJ1 socket/`ij.ImageJ` handoff
**What was tried:**
A direct `ij.ImageJ -macro`/legacy listener route was tested to bypass delayed Fiji launcher behavior.

**Observed endpoint result:**
A synthetic blank IJ1 proof could forward a marker with one JVM, but manual validation against the user's actual open Fiji showed that direct `ij.ImageJ` did **not** attach to the intended Fiji instance; it created a separate regular ImageJ GUI.

**Reusable lesson:**
A legacy IJ1 proof against a controlled blank IJ1 process does not establish compatibility with the user's modern Fiji GUI/session. Do not return to plain `ij.ImageJ` as the production GUI-control route.

**Disposition:** ruled out for this installation/workflow.

### Route 5 — Source-launched RMI bridge to Fiji legacy single-instance stub
**What was tried:**
A bespoke helper `FijiExistingInstanceHandoff.java` was invoked via `java.exe` looking up dynamic `.stub` files in `%TEMP%` to send RMI arguments to Fiji, while AHK clamped toolbar dimensions to 640x180.

**Observed endpoint result:**
1. `java.exe -cp ... FijiExistingInstanceHandoff.java` failed with `ClassNotFoundException` because Java 11+ source execution is disabled when `-cp` is specified.
2. File paths with `!` characters caused argument-handling errors in JDK tooling.
3. Stub discovery by mtime picked stale/dead stub files from prior crashed runs.
4. Bytecode inspection of `ij.OtherInstance` and `net.imagej.legacy.SingleInstance` proved that RMI single-instance listening is disabled by default unless bit `4194304` is enabled in `prefs.options` in `IJ_Prefs.txt`.
5. AHK forced `WinMove` with fixed 640x180 shrank the native Fiji toolbar, clipping buttons.

**What this established:**
- Direct custom RMI stub invocation was a brittle workaround for disabled preferences and is unnecessary.
- When `prefs.options` has single-instance enabled, or when invoked directly with `--no-splash -macro <path>`, Fiji executes the macro cleanly.
- Fiji toolbar positioning should only position `(x, y)` in the upper right (`WinMove(x, top + 10, , , hwnd)`) and must NOT impose a fixed width or height, allowing native toolbar dimensions to be preserved.

**Disposition:** Custom RMI handoff removed; toolbar resize constraint removed.

## Additional durable debugging evidence
- Four 108x108 ROI 1-click placements have worked as the authoritative manual references; do not redesign them merely because launch/control stages failed.
- The four-click → grid → Accept → export path has worked on multiple images/experiment folders; preserve that behavior while changing orchestration around it.
- A direct-script import-context failure (`ModuleNotFoundError: No module named 'tools'`) was a concrete launcher execution-context bug, not evidence that four-point geometry was wrong.
- Different downstream errors blocking the same single-interactive-Fiji endpoint are one continuing endpoint problem, not a reset to unrestricted patching.
- Case-insensitive matching and explicit DONE/reset behavior are separate proven workflow concerns and should not be entangled with the Fiji ownership architecture.
- GUI/tool-window positioning is convenience behavior. Do not let window-placement code become the authority for whether the correct Fiji process/session exists.

## Current preferred route / current unknown
The current `workflow-C` implementation:
1. Converts saved ROI dimensions to numbers at source.
2. Uses `--no-splash -macro <path>` with the configured Fiji launcher without `Show All`.
3. Positions the native Fiji toolbar in the upper-right without resizing its native width/height.
4. Removes superseded buttons (old full-column detector, synthetic plates, manual hotkeys) from active controller UI.
5. Uses case-insensitive filename comparison for pending plates and dispositions.
6. The affected QC/CLAHE path passes real Fiji on synthetic data; manual validation remains the standard desktop verification gate.

### Late duplicate prompt containment

Generated one-plate macros contain one calibration block and four click dialogs; static inspection does not support generator duplication.  A retained Fiji session can nevertheless receive a late duplicate macro delivery from the launcher/single-instance lifecycle.  The AutoHotkey helper therefore has a deliberately narrow containment rule: after `ALL DONE`, or an explicit user cancellation, it dismisses only a newly appearing four-click dialog whose title matches the just-finished source for 1.8 seconds.  Retries do not arm it.  This is not evidence that session ownership is solved; revisit the runtime architecture rather than broadening this window hook if the containment proves unreliable.

## Re-search / retry triggers
Search or retry when a materially different Fiji/runtime failure changes the endpoint question, a genuinely distinct architecture is being considered, Fiji/ImageJ/Jaunch/PyImageJ version behavior changes, an upstream source documents a concrete relevant fix, or the user explicitly requests broader/fresh research.

Do not repeat substantially equivalent RMI/socket/direct-IJ1 searches or implementations merely because the error wording changes while the same endpoint remains blocked.

## Sources / durable references
- ImageJ built-in macro functions (`call`, `parseFloat`): https://imagej.net/ij/developer/macro/functions2.html
- ImageJ legacy `SingleInstance` source: https://github.com/imagej/imagej-legacy/blob/master/src/main/java/net/imagej/legacy/SingleInstance.java
- ImageJ `WindowOrganizer` source: https://github.com/imagej/ImageJ/blob/master/ij/plugin/WindowOrganizer.java
- ImageJ legacy single-instance issue 275: https://github.com/imagej/imagej-legacy/issues/275
- ImageJ legacy single-instance issue 238: https://github.com/imagej/imagej-legacy/issues/238
- Stack Overflow, “Controlling already existing instance of ImageJ”: https://stackoverflow.com/questions/33023534/controlling-already-existing-instance-of-imagej
- ImageJ command-line guide (`-port`, `-macro`): https://imagej.net/ij/docs/guide/146-18.html
- ImageJ `ImageJ.java` (`OtherInstance` argument forwarding): https://github.com/imagej/ImageJ/blob/master/ij/ImageJ.java
- Fiji modern launcher / Jaunch: https://imagej.net/learn/launcher
- PyImageJ scripting: https://imagej.net/scripting/pyimagej
- ImageJ/Fiji Python scripting modes: https://imagej.net/scripting/python
- Appose: https://apposed.org/
- Jaunch Windows Python-mode issue history: https://github.com/apposed/jaunch/issues/87
