# Manual validation backlog

This file is the durable queue for checks that genuinely require user visual/desktop judgement. Codex should accumulate such items here instead of repeatedly interrupting implementation for one-off manual tests.

## Rules

- Before any real-image/Fiji verification, run the image-blind privacy gate first and report its result.
- Real/sample images must remain image-blind to Codex/other models; see `IMAGE_BLIND_TESTING.md`.
- If a check can be completed from logs, geometry, dimensions, return codes, generated artifacts or other non-pixel telemetry, complete it autonomously instead of adding it here.
- If a check genuinely requires seeing image pixels or manual point placement, add one concise backlog item with exact steps and expected observable result.
- Continue other safe, task-relevant implementation/testing while backlog items are pending whenever they are not blocking the current objective.
- Batch related manual checks together where practical so the user can perform one desktop session instead of repeated interruptions.
- Remove or mark an item complete only after the user reports the result.

## Pending

- One installed-Fiji session covering both four-point modes after passing the image-blind privacy gate. On one pending plate, run default export: confirm the toolbar/dialog placement and Z advance, acceptable disposable CLAHE/QC overlay, Accept/Retry, unchanged source, expected Top/Low crops, grid asset, and completed-run log. On a different pending plate, enable **Register grid only (no crops)**: confirm the same placement/QC, registration-specific wording, a finalized grid asset, no crop files/archive/crop-completion state, and a completed log that does not claim crop export. Do not send screenshots or pixels to an agent.

- One V10-apps visual/QC session using local real images only after the privacy gate: create/open project state; preview/apply optional Working copies; confirm orientation and plate-crop previews before acceptance; attach the saved grid; inspect visibility and annotation previews; export later Unprocessed and Processed Top/Low cultures; then compose one matrix mixing at least one Top and one Low crop. Confirm raw sources remain unchanged, rejected previews write nothing, accepted outputs use numbered/provenance-recorded locations, and label/crop/matrix presentation is usable. Report observations textually only.

- In the same private desktop session, exercise Quick Figures with a non-V10 PCR/other-figure image and the packaged `samples/quick_figure.csv`: test both embedded and detached forms, dragged-edge alignment, whole crop, two-endpoint 1×N registration, optional QC, quick description/date, one rich header/in-image preset (including an exact strain colour), and long rectangular per-well export. Then select at least two project images in Batch and confirm manual queue advance plus one automatic dry-run/accept stage. Confirm hotkeys act only in the intended applet/tab and report observations textually without sending pixels.

## Completed

None recorded yet.
