# Fiji four-point runtime / launch lifecycle

## Goal
Reach a repeatable CSV-driven one-plate four-point Fiji run that reuses/launches Fiji correctly, applies the intended preview processing, accepts four authoritative ROI 1-click placements, and reaches grid/QC without deterministic launcher or IJM failures.

## Searches tried
Prior exact online search strings were not durably recorded. Do **not** invent them retroactively. Future searches for this topic should be appended here only when they materially affect the next implementation route.

## Useful findings
- Production macro generation is the intended single source of truth for ROI 1-click adaptation; a prior proof layer applying the adapter again caused a double-application contract failure.
- Exact generated artifacts matter more than generator-only checks: manual Fiji execution has exposed deterministic IJM failures that synthetic generator checks did not catch.
- AutoHotkey contract is v2 only.

## Ruled-out / failed local routes
- Double-applying the ROI 1-click adapter in production + proof preparation: failed contract validation; removed in commit `21a04b0`.
- Treating generator/static checks alone as sufficient proof of Fiji runtime validity: manual execution subsequently exposed an IJM parser failure.
- Current relaunch behavior that starts another Fiji instance while one is already usable: produced a persistent `Launching Fiji...` overlay and `File not found: Macro_Runner` behavior.

## Local attempts / current evidence
- Four 108x108 ROI 1-click placements have worked as the authoritative manual references.
- Intended preview CLAHE behavior is two applications using block size approximately 3.3x ROI dimension, histogram 256, maximum slope 1000, mask None, fast/less-accurate.
- Manual run after `21a04b0` still failed after the fourth click with an ImageJ macro parser error around `halfW = QC_W / 2;`; grid/QC did not appear.
- Re-running the proof with Fiji already open attempted an unnecessary new launch, left the launching overlay visible, and raised a `Macro_Runner` file-not-found error.

## Current preferred route / current unknown
Perform bounded research before another speculative patch. Prioritize established Fiji/ImageJ launch/macro-runner behavior and exact IJM syntax/runtime evidence, then verify only the affected real execution path. Do not broaden into unrelated workflow redesign.

## Re-search triggers
Search again when a materially different Fiji/runtime failure appears, a distinct launch mechanism is being considered, Fiji/ImageJ version behavior changes, or the user explicitly asks for broader/fresh research. Do not repeat substantially equivalent searches merely because the error wording changes while the same end-to-end goal remains blocked.
