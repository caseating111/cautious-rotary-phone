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
- Profile averaging now uses a mature native ImageJ path: the tall rectangle is temporarily converted to a vertical straight-line ROI with the same width, then `getProfile()` delegates to ImageJ's wide-line/`Straightener` machinery. The rectangle is immediately restored. The previous explicit `getValue()` pixel loop remains only as a fallback if the native profile is unexpectedly unavailable/short.
- `ahk/full_column_alignment_hotkeys.ah2` remains small global-hotkey convenience only.
- Source identity/dimensions are persisted with accepted alignment geometry to prevent stale reuse.

### Visibility / crop handoff
- `fiji/apply_global_visibility.ijm`: robust outside-grid background + inside-grid high percentile -> one whole-image display range while preserving quantitative source pixels.
- It can consume saved visibility settings through ImageJ macro arguments; direct no-argument launch retains the original dialog.
- Official ImageJ documentation confirms the launcher form `-macro path [arg]`, so the config-driven visibility argument itself no longer needs manual compatibility testing.
- `fiji/export_crops_from_alignment.ijm`: accepted alignment -> established Top/Low crop naming and geometry.
- Crop export validates every intended Top/Low rectangle against source-image bounds before writing the first PNG. Non-positive crop dimensions and zero matching grid rows are rejected as well.

### Existing production batch composition
- `tools/run_full_column_batch_from_config.py` reuses the existing production Fiji batch macro's folder/CSV/image loop.
- Only the old four-point calibration/export section is replaced in a temporary configured copy by calls to `full_column_alignment.ijm` and `export_crops_from_alignment.ijm`.
- The original four-point macro remains untouched as fallback.
- CSV semantic validation runs before Fiji starts.
- Saved crop width/height and alignment tolerance are consumed only where metadata already supplies the grid column count.
- `--prepare-only` performs CSV validation, preflight, pending-image generation, exact source-marker checks and configured macro construction without launching Fiji.

### Batch preflight / resume
- `tools/preflight_batch.py` mirrors production immediate-subfolder, basename metadata and exact output-name semantics.
- It reports discovered/mapped/unmapped images, duplicate source basenames, stale metadata rows, missing grid definitions and expected/existing/missing crop counts.
- It blocks exact same-path output collisions before Fiji can overwrite a plate.
- It also blocks duplicate logical crop names across different output folders. This is required because the reused Pillow matrix scripts recursively search by filename prefix and otherwise warn then choose the first match, so cross-folder duplicates are downstream-ambiguous even though Fiji itself writes them to separate folders.
- It writes `~/.cautious-rotary-phone/last_preflight.txt` and pending-only `pending_images.csv`.
- The composed batch uses pending-only metadata, so completed plates are naturally skipped on rerun. Partially complete plates remain pending as a whole plate; no fragile per-crop resume path is introduced.
- `tests/test_preflight_batch.py` covers missing, complete, duplicate-basename, same-folder collision, cross-folder downstream ambiguity and distinct-condition non-ambiguity cases.

### Metadata reconciliation
- `tools/reconcile_images_csv.py` scans production source folders, preserves existing authoritative metadata, leaves new metadata blank rather than guessed, and preserves manual draft metadata across rescans.
- Duplicate source basenames, duplicate metadata rows and stale metadata rows are explicitly flagged.
- `tools/finalize_images_reconciliation.py` creates a separate `images_candidate.csv` only when current source rows are complete, basenames are unique and the project validator accepts the candidate.
- Authoritative `images.csv` is never overwritten automatically.
- `tools/metadata_review_gui.py` keeps reconcile/edit/finalize/open actions outside the main processing GUI; the controller has one launcher button.

### Existing Pillow output reuse
- `tools/run_existing_pillow_from_config.py` exposes the four existing matrix/all-strain/individual-label scripts through saved controller paths without rewriting their composition logic.
- All four aliases are regression-checked for the shared path-block adapter.
- Before output generation, the wrapper derives the same logical crop prefixes used by the existing scripts from `grid.csv` + `images.csv` and blocks any prefix with multiple real file matches. This catches stale/legacy duplicates before the old scripts can silently choose the first match.
- Only current logical crop matches are passed to orientation normalization. Unrelated images under `crop_output` are ignored.
- Current crop inputs matching the configured unrotated dimensions are rotated once with Pillow; already-rotated crops are skipped. Current logical crops with incompatible dimensions fail before matrix generation.
- Temporary configured copies force `ROTATE_IMAGES_90_CCW = False`, removing dependence on the legacy one-shot `.rotated_90ccw.done` behavior.

### CSV validation
- `tools/validate_project_csvs.py` checks required headers, grid completeness/duplicates, consistent GridCols, unique source filenames, image->grid references and condition-order coverage.
- It rejects comma-bearing Experiment/Set/Type/Strain metadata and embedded line breaks that the reused ImageJ line parser would misread.
- It rejects semicolons in Experiment/Set/Type because the composed Fiji helpers use semicolon-delimited `runMacro` arguments.
- Comma-containing filenames remain allowed because the production macro explicitly handles quoted filenames containing commas.
- `tests/test_csv_validation.py` covers comma, semicolon, embedded-line-break and supported comma-in-filename cases.

### Lightweight controller / conda
- `tools/workflow_controller.py` persists paths/settings, validates CSVs, launches Fiji/AHK/Pillow helpers and ROI presets.
- Processing settings cover alignment tolerance, crop size and global visibility values without moving processing into the GUI.
- Quick buttons open configured source-image, crop-output and matrix-output folders directly using the OS shell.
- Controller window is titled `Image workflow controller`.
- `tools/run_fiji_macro_from_config.py` is a thin visibility launcher using ImageJ's macro argument mechanism and supports dry-run command inspection.
- `environment.yml` remains minimal (`python`, `pillow`).

### Automated regression checks
- `.github/workflows/python-glue-tests.yml` runs the Python unittest suite on pushes to `workflow-dev` and pull requests.
- The workflow now installs Pillow explicitly before running tests, so clean GitHub runners can execute the current adapter/orientation tests instead of depending on an incidental preinstalled package.

## Branch cleanup status
Historical milestone branches are not needed for routine continuation. Do not create more routine branches; development remains on `workflow-dev`.

## Legacy audit result
- `existing scripts clean/pythonfileaudit.py` is an E2/B-specific diagnostic and is superseded by generic preflight/reconciliation tooling; do not expose or expand it without a concrete missing use case.

## Pending manual validation (not a stop condition)
- Desktop Fiji interaction for ROI preset patch and whole-column placement/QC.
- Visual confirmation of native wide-line profile peak selection on representative real plates.
- End-to-end composed batch on representative images, including pre-export bounds checks.

## Research notes / stop-loss
- ImageJ documentation/source confirms wide straight-line profiles perform pixel averaging natively and `Array.findMaxima(array, tolerance)` returns peak positions ordered by descending strength. The current route therefore composes mature ImageJ profile + peak functionality rather than bespoke colony detection.
- BAR's established `Find Peaks` command remains the first fallback if native maxima selection proves weak on representative plates. It is macro-callable and supports minimum peak amplitude/distance and flat-topped peaks.
- Intensity Profile Tools remains a lower-priority interactive profile alternative.
- Do not build a custom colony detector or spacing optimizer before representative real-plate QC demonstrates a concrete need.
- ImageJ supports installed macro keyboard shortcuts, but AHK remains preferable for the current modal-dialog flow because the image window is not always focused. Do not move workflow logic into AHK.

## Highest-value next routes
1. Use `--prepare-only` with the user's real configured metadata before asking for interactive Fiji validation.
2. Validate the smallest real desktop first/last-column route; preserve the old four-point fallback.
3. If native peak selection is weak, test BAR Find Peaks before any custom detection work.
4. Add only cheap guards or orchestration improvements that prevent wrong outputs or remove repeated navigation; avoid architecture expansion.
5. Keep metadata inference conservative unless real data demonstrates a stable, verifiable pattern.
