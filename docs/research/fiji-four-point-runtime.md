# Fiji four-point runtime / launch lifecycle

## Goal / endpoint
Reach a repeatable CSV-driven one-plate four-point Fiji run that launches/reuses Fiji correctly, applies the intended preview processing, accepts four authoritative 108x108 ROI 1-click placements, and reaches grid/QC without deterministic launcher or IJM failures.

## Current state
The four click placements themselves have worked, but the practical endpoint has failed through multiple materially different integration routes. The current implementation must not repeat prior adapter, generator-only validation, or launch/reuse assumptions without new evidence.

## Research history

### Searches tried
Prior exact online search strings were not durably recorded. Do **not** invent them retroactively. Future searches for this topic should be appended here only when they materially affect the next implementation route.

### Useful findings
- Production macro generation is the intended single source of truth for ROI 1-click adaptation.
- Exact generated artifacts matter more than generator-only checks: manual Fiji execution exposed deterministic IJM failures after synthetic/generator checks passed.
- AutoHotkey contract is v2 only.
- Intended preview CLAHE behavior is two applications using block size approximately 3.3x ROI dimension, histogram 256, maximum slope 1000, mask None, fast/less-accurate.

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

**What this established:**
Validating only the Python generator or synthetic proof is insufficient evidence that the exact emitted ImageJ macro is accepted by the real Fiji runtime. The failure occurred after apparently successful upstream validation.

**Reusable lesson:**
For this endpoint, test the exact generated runtime IJM through Fiji's actual parser/runtime whenever feasible and image-blind; do not report the endpoint deterministic path clean based only on generator-level checks.

**Disposition:** generator-only validation is ruled out as endpoint proof.

### Route 3 — Existing Fiji launch/reuse lifecycle
**What was tried:**
The proof/controller attempted to run again while Fiji was already open, using the current launch/reuse and macro invocation path.

**Observed endpoint result:**
The controller attempted another Fiji launch instead of reliably reusing the existing instance, left the `Launching Fiji...` overlay visible, and produced `File not found: Macro_Runner` behavior.

**What this established:**
Launch-state cleanup, existing-instance detection/reuse, and macro invocation were not reliably coordinated. Earlier indirect window-geometry/desktop assumptions also proved too fragile to use as the authority for Fiji main-window state.

**Reusable lesson:**
Do not return to indirect geometry-based Fiji main-window inference or the same relaunch/Macro_Runner lifecycle under a cosmetic rewrite. Prefer documented/established Fiji/ImageJ invocation behavior and ensure success/failure paths always clear launch UI state.

**Disposition:** current route unreliable; requires a materially better-supported implementation.

## Additional durable debugging evidence
- Four 108x108 ROI 1-click placements themselves have worked as the authoritative manual references; do not redesign them merely because downstream runtime stages failed.
- A direct-script import-context failure (`ModuleNotFoundError: No module named 'tools'`) was fixed separately. It was a concrete launcher execution-context bug, not evidence that the four-point geometry approach was wrong.
- Different downstream errors blocking the same grid/QC endpoint should be treated as one continuing endpoint problem for research/reassessment purposes, not as a reset to unrestricted patching.

## Current preferred route / current unknown
Perform bounded research before another speculative implementation attempt. Prioritize established Fiji/ImageJ launch/reuse/macro-runner behavior and exact IJM syntax/runtime evidence, then verify only the affected end-to-end path. Preserve the current four-click interaction and required double-CLAHE behavior unless evidence specifically implicates them.

## Re-search / retry triggers
Search or retry when a materially different Fiji/runtime failure changes the question, a distinct launch mechanism is being considered, Fiji/ImageJ version behavior changes, a source documents a concrete fix, or the user explicitly requests broader/fresh research. Do not repeat substantially equivalent searches or implementation routes merely because the error wording changes while the same endpoint remains blocked.

## Sources / durable references
Add authoritative Fiji/ImageJ documentation, established project references, GitHub issues, Image.sc discussions, or other decisive sources prospectively as they materially influence the implementation route. Prior search URLs were not durably recorded.
