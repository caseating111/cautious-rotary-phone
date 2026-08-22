# Fiji four-point runtime / launch lifecycle

## Goal / endpoint
Reach a repeatable CSV-driven one-plate four-point Fiji run that launches/reuses Fiji correctly, applies the intended preview processing, accepts four authoritative 108x108 ROI 1-click placements, and reaches grid/QC without deterministic launcher or IJM failures.

## Current state
The four click placements themselves have worked, but the practical endpoint has failed through multiple materially different integration routes. The current implementation must not repeat prior adapter, generator-only validation, or launch/reuse assumptions without new evidence.

## Research history

### Searches tried
Prior exact online search strings were not durably recorded. Do **not** invent them retroactively.

Searches run on 2026-08-22 after the next manual failure:
- `ImageJ macro string arithmetic ')' expected parseFloat call ij.Prefs.get`
- `Fiji Windows existing instance macro command line RMI IJ.getInstance null`
- `site:forum.image.sc Fiji existing instance run macro Windows`
- `site:stackoverflow.com ImageJ run macro existing instance`
- GitHub issue searches: `repo:imagej/imagej-legacy SingleInstance`, `repo:imagej/imagej-legacy RMI stub`, and `repo:imagej/imagej-legacy macro existing instance`

The general web and Image.sc search endpoints returned no usable results; the official ImageJ reference/source, GitHub issue API, and Stack Exchange API supplied the decisive evidence below. Do not repeat these equivalent searches unless the retry conditions apply.

### Useful findings
- Production macro generation is the intended single source of truth for ROI 1-click adaptation.
- Exact generated artifacts matter more than generator-only checks: manual Fiji execution exposed deterministic IJM failures after synthetic/generator checks passed.
- AutoHotkey contract is v2 only.
- Intended preview CLAHE behavior is two applications using block size approximately 3.3x ROI dimension, histogram 256, maximum slope 1000, mask None, fast/less-accurate.
- ImageJ's official macro reference states that `call()` returns a string and `parseFloat(string)` converts it to a numeric value. Saved ROI dimensions must therefore be converted where read, before CLAHE or QC arithmetic.
- ImageJ legacy's `SingleInstance` source explicitly forwards `-macro <path>` to the running instance. A Stack Overflow answer by an ImageJ maintainer likewise identifies the single-instance listener plus a second launcher's command-line arguments as the built-in IPC route.
- The same legacy route has open upstream lifecycle defects (imagej-legacy issues 275 and 238); do not assume that successful argument forwarding implies every IJ1 GUI singleton is initialized.
- `WindowOrganizer.showAll()` unconditionally calls `IJ.getInstance().toFront()`. It is incompatible with the observed forwarded-macro state where `IJ.getInstance()` is null; main-frame placement should remain outside that macro command.

### Research routes ruled out / weak
- Treating a superficially close custom patch as sufficient without checking established Fiji/ImageJ launch/macro behavior after the endpoint repeatedly failed.
- Treating generator/static checks alone as proof of Fiji runtime validity.

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
Those checks passed, but actual Fiji later rejected the generated IJM after the fourth click with a parser error around `halfW = QC_W / 2;`; grid/QC never appeared.

After `halfW`/`halfH` were inlined, the next manual run failed at the same operation in `p1x = qcX - (QC_W / 2) * hux - (QC_H / 2) * vux;`. Runtime telemetry showed `QC_W="108"`, `QC_H="108"`, `roiBoxW="108"`, and `roiBoxH="108"`, proving the dimensions—not the arithmetic layout—were typed as strings.

**What this established:**
Validating only the Python generator or synthetic proof is insufficient evidence that the exact emitted ImageJ macro is accepted by the real Fiji runtime. The failure occurred after apparently successful upstream validation.

The active artifact that produced the reported failure was `%USERPROFILE%\.cautious-rotary-phone\one_plate_four_point_validation.configured.ijm`, so future diagnosis must inspect that configured file rather than infer its contents from the generator. ImageJ `ij-1.54p.jar`'s `ij.macro.Interpreter` accepted both an isolated copy of the geometry and the geometry placed in the extracted artifact's symbol/function context, including the `halfW`/`halfH` identifiers. That narrower interpreter check therefore did not reproduce the real interactive Fiji failure and is not an adequate substitute for the actual configured runtime path.

The source-of-truth fix converts `call("ij.Prefs.get", ...)` with `parseFloat()` at ingestion. A hidden `--allow-multiple --headless` run through the installed Fiji executable then executed the exact preference conversion, user-reported geometry, QC arithmetic/overlay construction, and both CLAHE calls on a synthetic blank image. It wrote `QC_RUNTIME_PASS`, `QC_W=108`, `QC_H=108`, `CLAHE_CALLS=2`, and `LINES=392` with exit code 0.

**Reusable lesson:**
For this endpoint, test the exact generated runtime IJM through Fiji's actual parser/runtime whenever feasible and image-blind; do not report the endpoint deterministic path clean based only on generator-level checks.

**Disposition:** generator-only validation is ruled out as endpoint proof.

### Route 3 — Existing Fiji launch/reuse lifecycle
**What was tried:**
The proof/controller attempted to run again while Fiji was already open, using the current launch/reuse and macro invocation path.

**Observed endpoint result:**
The controller attempted another Fiji launch instead of reliably reusing the existing instance, left the `Launching Fiji...` overlay visible, and produced `File not found: Macro_Runner` behavior.

The next manual run showed the standard single-instance handoff message and then `WindowOrganizer.showAll()` threw because `IJ.getInstance()` was null, although the forwarded macro continued far enough to collect all four clicks and sensible geometry.

**What this established:**
Launch-state cleanup, existing-instance detection/reuse, and macro invocation were not reliably coordinated. Earlier indirect window-geometry/desktop assumptions also proved too fragile to use as the authority for Fiji main-window state.

Local Fiji inspection established several reusable boundaries:
- the configured Windows Fiji launcher produced a stable main window only when started with the Fiji installation directory as its working directory;
- Fiji's installed Jaunch configuration documents `--run <plugin> [<arg>]`, `--allow-multiple`, and `--no-splash`;
- decompilation of installed `imagej-legacy-2.0.3.jar` showed its single-instance layer forwarding `-macro <path>` and `-run` requests through a serialized RMI stub;
- a stale `%LOCALAPPDATA%\Temp\ImageJ-<user>-7.stub` existed, but no causal link was proven, so deleting or managing that stub must not be adopted as a fix without new evidence.

Image-blind automation attempts using `-macro`, `--run "Macro Runner"`, and a temporary AHK File/Open handoff either exited or failed to reach observable alignment without a decisive textual error. The experimental AHK route was removed. These attempts did not prove the exact configured macro reached QC and must not be cited as successful real-Fiji validation.

**Reusable lesson:**
Do not return to indirect geometry-based Fiji main-window inference or the same relaunch/Macro_Runner lifecycle under a cosmetic rewrite. Prefer documented/established Fiji/ImageJ invocation behavior and ensure success/failure paths always clear launch UI state.

**Disposition:** current route unreliable; requires a materially better-supported implementation.

The current narrow disposition is to retain the documented `-macro` single-instance argument handoff and remove only the incompatible `run("Show All")` macro command. The existing bounded Win32/AHK frame placement remains responsible for visibility. Manual confirmation is still required; do not claim the lifecycle resolved from the synthetic probe.

## Additional durable debugging evidence
- Four 108x108 ROI 1-click placements themselves have worked as the authoritative manual references; do not redesign them merely because downstream runtime stages failed.
- A direct-script import-context failure (`ModuleNotFoundError: No module named 'tools'`) was fixed separately. It was a concrete launcher execution-context bug, not evidence that the four-point geometry approach was wrong.
- Different downstream errors blocking the same grid/QC endpoint should be treated as one continuing endpoint problem for research/reassessment purposes, not as a reset to unrestricted patching.
- The apparently silent fourth physical image was not lost by discovery or reconciliation. In actual filesystem order, two non-proof files preceded the selected proof image and the fourth followed it; the selected image's parser exception aborted the sequential IJM loop before the fourth could print a disposition. Case-insensitive comparison keys are still required at preflight and IJM filename lookup boundaries while preserving original display values.

## Current preferred route / current unknown
The current `workflow-C` implementation converts saved ROI dimensions to numbers at source, retains the established `-macro` single-instance handoff without `Show All`, uses case-insensitive filename keys, and gives the compact Fiji frame a 640x180 minimum. The affected QC/CLAHE path passes real Fiji on synthetic data; the exact interactive one-plate artifact still requires one batched manual validation. Preserve the current four-click interaction and required double-CLAHE behavior unless evidence specifically implicates them.

## Re-search / retry triggers
Search or retry when a materially different Fiji/runtime failure changes the question, a distinct launch mechanism is being considered, Fiji/ImageJ version behavior changes, a source documents a concrete fix, or the user explicitly requests broader/fresh research. Do not repeat substantially equivalent searches or implementation routes merely because the error wording changes while the same endpoint remains blocked.

## Sources / durable references
- ImageJ built-in macro functions (`call`, `parseFloat`): https://imagej.net/ij/developer/macro/functions2.html
- ImageJ legacy `SingleInstance` source: https://github.com/imagej/imagej-legacy/blob/master/src/main/java/net/imagej/legacy/SingleInstance.java
- ImageJ `WindowOrganizer` source: https://github.com/imagej/ImageJ/blob/master/ij/plugin/WindowOrganizer.java
- ImageJ legacy single-instance issue 275: https://github.com/imagej/imagej-legacy/issues/275
- ImageJ legacy single-instance issue 238: https://github.com/imagej/imagej-legacy/issues/238
- Stack Overflow, “Controlling already existing instance of ImageJ”: https://stackoverflow.com/questions/33023534/controlling-already-existing-instance-of-imagej
