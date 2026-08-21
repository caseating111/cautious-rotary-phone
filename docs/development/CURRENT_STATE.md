# Current state

## Durable line
`workflow-dev`

## Branching rule
Routine implementation goes directly onto `workflow-dev`. Do **not** create a new branch for ordinary fixes, small features, docs, tests, adapters, UI/default changes, refactors, or routine experiments. Create a separate branch only when work is genuinely risky, destructive, highly speculative, likely to conflict with concurrent work, or may be discarded wholesale.

## Working baseline
- Original four-point Fiji crop macro and original AHK helper remain unchanged as fallback.
- Original Pillow matrix/label scripts remain under `existing scripts clean/` and are reused through thin config adapters.
- Synthetic `grid.csv`, `images.csv` and `condition_order.csv` examples remain the development fixtures; no real experimental CSV data is committed.
- Implementation is governed by `AGENTS.md` and `IMPLEMENTATION_DECISION_POLICY.md`.

## Implemented on workflow-dev

### ROI presets / manual alignment assistance
- Named ROI-size presets around the published ROI 1-Click Tools plugin.
- `fiji/full_column_alignment.ijm`: manually authoritative first/last whole-column ROIs -> vertical average profile -> native ImageJ `Array.findMaxima()` -> regular grid -> full-grid QC -> accept/retry.
- User interaction remains one tall rectangle on the first column and the same rectangle moved to the last column. Manual placement remains authoritative.
- Profile averaging uses mature native ImageJ wide-line profile machinery via `getProfile()` / `Straightener`; the explicit `getValue()` pixel loop remains fallback only.
- Batch Experiment/Set/Type context is passed into the already-required first-column `waitForUser` dialog. The separate per-plate `Next plate` acknowledgement was removed, saving one click/keypress per image without removing alignment oversight.
- After an accepted alignment, the first-column whole-column reference rectangle is persisted. On a later image with matching dimensions it can be pre-positioned as a **starting suggestion only**. The user must still move/resize it, position the last column, and accept full-grid QC; previous geometry is never automatically accepted.
- ROI preset reads fall back safely when the saved preset value is missing, NaN or non-positive.
- The ROI preset GUI uses the configured Fiji executable to find `Roi 1-Click Tools.ijm`, preferring the normal `macros/toolsets/` location and recursively searching only as fallback. A unique discovered toolset is patched directly; missing/ambiguous installs retain the file picker.
- The ROI 1-Click Tools patch action is idempotent. Re-running it on an already preset-aware toolset reports **Already patched** and makes no changes instead of presenting a false failure.
- Accepted alignment persists ImageJ `image.directory` and `image.filename` when available, plus title/dimensions. Crop export and visibility reject stale geometry from another same-named/same-sized real file; older/synthetic alignment files retain title+dimension fallback.
- `ahk/full_column_alignment_hotkeys.ah2` remains small global-hotkey convenience only. It watches only the remaining dialogs (`1 / 2`, `2 / 2`, `Alignment QC`, `ALL DONE`); obsolete `Next plate` handling was removed.
- `tests/test_alignment_macro_contract.py` protects the manual-authority/seed/native-profile contract without speculative headless Fiji CI. `tests/test_roi_preset_discovery.py` covers configured-Fiji discovery and idempotent patching without Fiji itself.

### Visibility / crop handoff
- `fiji/apply_global_visibility.ijm`: robust outside-grid background + inside-grid high percentile -> one whole-image display range while preserving quantitative source pixels.
- Visibility percentile/background work already uses ImageJ native histogram machinery; do not replace it with bespoke pixel loops.
- It can consume saved visibility settings through ImageJ macro arguments; direct no-argument launch retains the original dialog.
- Official ImageJ documentation confirms launcher form `-macro path [arg]`, so config-driven visibility argument passing itself no longer needs manual compatibility testing.
- Visibility uses the same source-path-aware accepted-alignment identity check as crop export, with backward-compatible title+dimension fallback.
- `fiji/export_crops_from_alignment.ijm`: accepted alignment -> established Top/Low crop naming and geometry.
- Crop export validates every intended Top/Low rectangle against source-image bounds before writing the first PNG.
- Direct/helper export also requires exactly `gridCols` matching grid rows, rejects duplicate grid columns before writing, and verifies final export count equals `gridCols * 2`.

### Existing production batch composition
- `tools/run_full_column_batch_from_config.py` reuses the existing production Fiji batch macro's folder/CSV/image loop.
- Only the old four-point calibration/export section is replaced by calls to `full_column_alignment.ijm` and `export_crops_from_alignment.ijm`; the original four-point macro remains untouched as fallback.
- `--prepare-only` performs CSV validation, preflight, pending-image generation, exact source-marker checks and configured macro construction without launching Fiji **and without requiring a configured Fiji path**.
- Batch preparation verifies the production macro, alignment macro, crop helper, validator and preflight helper exist. Actual standalone launch verifies Fiji only when launch is requested.
- Configured `grid_csv` and `crop_output` paths containing semicolons are rejected because the crop-helper handoff uses semicolon-delimited macro arguments.
- The composed route no longer opens a modal `Next plate` message. Plate identity is shown in Fiji status and in the already-required first-column prompt.
- `tests/test_batch_interaction.py` protects the reduced-click interaction/context handoff; `tests/test_source_adapters.py` covers Fiji-free preparation versus actual launch requirements. `tests/test_batch_prepare_end_to_end.py` proves the real noninteractive validator -> preflight -> production-macro patching route on synthetic data without Fiji.

### Batch preflight / resume
- `tools/preflight_batch.py` mirrors production immediate-subfolder, basename metadata and exact output-name semantics.
- Standalone preflight runs the authoritative project CSV validator first.
- `crop_output` must be outside `image_root`; derived crops are not allowed inside the production source-image tree.
- `build_report(config, require_full_column_geometry=True)` keeps the Fiji-specific `GridCols >= 2` rule by default. Shared consumers such as Pillow can call it with `False` to reuse source/crop freshness and mapping checks without inheriting a full-column-only geometry restriction. This preserves valid one-column non-Fiji/Pillow workflows.
- It reports discovered/mapped/unmapped images, duplicate source basenames, stale metadata rows, missing grid definitions and expected/current/pending crop counts.
- It blocks same-path output collisions and duplicate logical crop names across different output folders, preventing downstream Pillow first-match ambiguity.
- Semicolon-bearing `grid_csv`/`crop_output` paths and immediate source-folder names are rejected before Fiji handoff.
- An expected crop counts as current only when it exists, is not older than its source image, is readable by Pillow, and its dimensions match configured crop width/height in either orientation.
- Existing derived crops older than the source are listed under **STALE EXPECTED CROPS — WILL REBUILD**. Unreadable/corrupt or wrong-size expected PNGs are listed under **INCOMPATIBLE EXPECTED CROPS — WILL REBUILD**. In both cases the plate returns to pending instead of being silently skipped.
- Existing PNGs under `crop_output` outside the current expected set are listed as **UNEXPECTED CROP PNGS — NON-BLOCKING**.
- Partially complete plates are listed as **PARTIALLY COMPLETE PLATES — NON-BLOCKING**. Resume intentionally remains plate-level; rerunning may replace existing expected crops instead of introducing fragile per-crop resume logic.
- It writes `~/.cautious-rotary-phone/last_preflight.txt` and pending-only `pending_images.csv`; complete/current plates are skipped naturally.
- `tests/test_preflight_full_column_constraints.py` now proves both modes: a one-column project is blocked for full-column Fiji and accepted by shared non-Fiji preflight when its crops are current.

### Metadata reconciliation
- `tools/reconcile_images_csv.py` scans production source folders, preserves existing authoritative metadata, leaves new metadata blank rather than guessed, and preserves manual draft metadata across rescans.
- Duplicate source basenames, duplicate metadata rows and stale metadata rows are explicitly flagged.
- `tools/finalize_images_reconciliation.py` creates a separate `images_candidate.csv` only when current source rows are complete, basenames are unique and the project validator accepts the candidate.
- Authoritative `images.csv` is never overwritten automatically.
- `tools/metadata_review_gui.py` keeps reconcile/edit/finalize/open actions outside the main processing GUI; the controller has one launcher button.

### Existing Pillow output reuse
- `tools/run_existing_pillow_from_config.py` exposes the four existing matrix/all-strain/individual-label scripts through saved controller paths without rewriting their composition logic.
- All four aliases are regression-checked for the shared path-block adapter; all four create one unique top-level output folder under `matrix_output`, matching wrapper navigation/cleanup assumptions.
- Pillow output jobs run the same authoritative project CSV validator used by Fiji before adapter generation or crop mutation.
- `matrix_output` must be outside `crop_output`, preventing recursive legacy scans from ingesting their own generated matrices.
- The wrapper builds/validates its configured legacy script before any crop-orientation mutation.
- It derives the legacy logical prefixes **and exact current exporter filenames**. More than one prefix match is blocking. A lone prefix-compatible crop with an old/wrong strain suffix is also blocking instead of being silently accepted by the legacy `startswith()` lookup.
- Missing expected logical crop cells are blocking by default. Intentional partial output requires explicit CLI `--allow-missing`; that opt-in may omit cells but still cannot substitute stale prefix-compatible files.
- In normal controller use, where `image_root` is configured, the Pillow wrapper reuses established source/crop preflight with `require_full_column_geometry=False`. It therefore blocks changed/newer source images, corrupt/wrong-size crops, unfinished plates and mapping problems while preserving one-column Pillow use.
- Only current exact logical crop matches are passed to orientation normalization. Unrelated images are ignored; incompatible current crop dimensions fail before matrix generation.
- Temporary configured copies force `ROTATE_IMAGES_90_CCW = False`, removing dependence on legacy one-shot rotation markers.
- Failed legacy jobs remove only newly created empty output folders and retain non-empty partial output for inspection.
- `tests/test_pillow_source_readiness.py` covers preflight reuse, and `tests/test_pillow_wrapper_end_to_end.py` proves a complete synthetic source -> current crops -> shared preflight -> wrapper -> actual legacy matrix route.

### CSV validation
- `tools/validate_project_csvs.py` checks required headers, grid completeness/duplicates, consistent GridCols, unique source filenames, image->grid references and condition-order coverage.
- It rejects comma-bearing Experiment/Set/Type/Strain metadata and embedded line breaks that the reused ImageJ line parser would misread.
- It rejects semicolons in Experiment/Set/Type because composed Fiji helpers use semicolon-delimited `runMacro` arguments.
- It rejects Windows filename-unsafe characters (`/ \\ : * ? " < > |`) in Experiment/Set/Type because those values enter crop filenames directly. Strain remains safe because the established exporter applies `safeName()`.
- Comma-containing filenames remain allowed because the production macro explicitly handles quoted filenames containing commas.

### Lightweight controller / Windows launcher / conda
- `tools/workflow_controller.py` persists paths/settings and orchestrates CSV validation, metadata review, Fiji/AHK/Pillow helpers, ROI presets and folder navigation.
- Processing settings cover alignment tolerance, crop size and global visibility values without moving processing into the GUI.
- **Run full-column batch** runs `--prepare-only` synchronously first. Only after validation/preflight/build succeeds does it verify Fiji, optionally start AHK, and launch the already-prepared macro directly. If this launch started AHK and Fiji then fails to spawn, that AHK process is stopped again.
- Configured visibility launch is checked synchronously through its thin helper so configuration/path errors surface in the GUI.
- Pillow jobs are run synchronously through the existing adapter so strict input/validation failures are shown directly in the controller instead of disappearing into a child console.
- Root `start_controller.cmd` stays intentionally thin: active named conda -> `conda run` -> Windows `py` -> PATH Python. Environment auto-creation was deliberately not added because it would increase surprise/setup risk.
- `environment.yml` remains minimal (`python>=3.11`, `pillow`).

### Automated regression checks
- `.github/workflows/python-glue-tests.yml` runs compileall plus the Python unittest suite on pushes to `workflow-dev` and pull requests, installing Pillow explicitly.
- Stock ImageJ `-batch` and Maven ImageJ were investigated for IJM CI; no headless macro CI was added because the interactive helpers could not be proven cleanly without another unvalidated runtime path.
- Current regression coverage includes preflight/resume/freshness/dimensions, shared/full-column constraint modes, CSV validation, source adapters, Fiji launcher construction, ROI discovery/idempotent patching, output navigation, controller handoffs, batch interaction, alignment macro contract, Pillow source readiness and real synthetic end-to-end matrix generation.
- The GitHub connector's combined-status endpoint has returned no status contexts for direct branch commits; do not infer a passing/failing Actions result from that absence.

## Branch cleanup status
- Development remains on `workflow-dev`; no routine branch was created.
- `workflow-policy-stoploss`, `workflow-policy-stoploss-v2` and `workflow-policy-stoploss-final` were compared against `workflow-dev`: each has zero unique commits and is 205–207 commits behind, so they are fully obsolete. The available connector does not expose branch deletion, so they remain present but must not be resumed.
- `workflow-foundation` is 209 commits behind and Git reports four old divergent commits affecting `AGENTS.md` and example CSVs. Their content is superseded by evolved files on `workflow-dev`, but because the commits are not literally contained it was left untouched. Do not develop on it.

## Legacy audit result
- `existing scripts clean/pythonfileaudit.py` is an E2/B-specific diagnostic and is superseded by generic preflight/reconciliation tooling; do not expose or expand it without a concrete missing use case.

## Pending manual validation (not a stop condition)
- `docs/development/MINIMAL_DESKTOP_VALIDATION.md` caps the interactive validation burden: one ordinary representative plate first; a second same-sized plate only if the first succeeds to verify previous-reference ROI seeding.
- The representative plate validates Fiji `waitForUser`, native wide-line profile behavior, `Array.findMaxima()` row selection, first/last interpolation, full-grid QC, crop handoff and optional AHK convenience together.
- Do not manually re-test noninteractive validation/Pillow paths exhaustively; they already have synthetic regression coverage.

## Research notes / stop-loss
- ImageJ documentation/source confirms wide straight-line profiles average pixels natively and `Array.findMaxima(array, tolerance)` returns peak positions ordered by strength. The current route composes mature ImageJ functionality rather than bespoke colony detection.
- ImageJ `waitForUser` is the intended non-modal ROI-adjustment interaction; plate metadata was folded into that existing dialog rather than kept as a separate confirmation.
- The published ROI 1-Click Tools route uses `ImageJ/macros/toolsets` and provides modifiable macro source, supporting the current thin patch/discovery approach.
- `docs/development/BAR_FIND_PEAKS_FALLBACK.md` records the mature BAR **Find Peaks** fallback, including Fiji update-site installation and macro-call shape. It is deliberately not integrated pre-emptively.
- If native peak selection fails on a representative plate after one sensible reposition/retry, stop tuning custom/native heuristics and test BAR Find Peaks before any bespoke detector work.
- Previous-reference ROI seeding remains a starting rectangle only. Do not expand into automatic accepted alignment before representative desktop validation.

## Highest-value next routes
1. Use `--prepare-only` with real configured metadata before requesting interactive Fiji validation.
2. Perform the minimal representative desktop route in `MINIMAL_DESKTOP_VALIDATION.md`; preserve the four-point fallback.
3. If native peak selection is weak, test BAR Find Peaks before any custom detector.
4. Continue only deterministic, user-time-reducing setup/output handoff improvements that can be proven without repeated manual testing; avoid architecture growth.
5. Keep metadata inference conservative unless real data demonstrates a stable, verifiable pattern.
