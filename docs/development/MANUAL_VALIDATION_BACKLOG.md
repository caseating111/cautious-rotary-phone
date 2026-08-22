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

- Four-point Fiji proof: manually place R1C1, R1C(last), R5C1 and R5C(last) when the next validated build is ready; verify visual grid/QC alignment only after automated privacy/static/generated-artifact checks pass.
- CLAHE visual appearance: only if still needed after parameter/runtime telemetry is verified; confirm that whole-image CLAHE appearance is acceptable without sending screenshots to the model.

## Completed

None recorded yet.
