# Current state

## Product and runtime

workflow-integrated is the active integration product branch, anchored to the workflow-C production baseline at d600ed4. The supported environment is Windows, Miniforge environment workflow-c, Python 3.11, Pillow, Tkinter, Fiji/ImageJ, ROI 1-click Tools, and AutoHotkey v2.

Start with start_controller.cmd. It validates exact Python 3.11 plus Pillow and Tkinter for every candidate and never tries another interpreter after the controller has run. start_custom_matrix.cmd uses the same contract.

## Portable pre-release

`tools/build_portable_release.py` creates `dist/workflow-integrated-prerelease.zip` from an explicit tracked runtime allowlist. The archive includes Windows launch/setup files, required Python/AHK/Fiji/legacy renderer assets, JSON contracts, and anonymous sample CSVs. It excludes Git metadata, repository docs/tests/fixtures/V10 data, caches, images, personal paths, AI/development material, and user state. The current artifact passes deterministic archive checks, anonymity/content scanning, extracted Python compilation, and packaged sample-CSV validation.

## Active endpoints

The controller provides project setup and CSV discovery; metadata reconciliation/preflight; all-folder, subfolder, single, and rerun four-point processing; and one unified **Build matrices and labelled crops** applet. Four-point processing defaults to crop export and also offers an explicit, non-persisted **Register grid only (no crops)** option. Register-only uses the same proven placement/QC/handoff path, writes the durable grid asset, and skips crop bounds/archive/write/state operations. It cannot be combined with rerun or replacement.

**Open V10 project applets** launches the stateful rich-metadata workflow. It can create/open project state, preview/apply UID-safe Working copies, orient and whole-plate crop derivatives, attach an accepted grid, adjust visibility or flag manual review, annotate from V10 layout plus measured spots, export Top/Low cultures later from either unprocessed or accepted processed whole plates, and build a matrix whose selected cells may independently use Top or Low. Preview and acceptance are separated for operations that write derivatives.

The basic CSV matrix endpoint remains available. One numbered applet run can publish any combination of per-experiment, selected all-strain, duplicate-WT-removed all-strain, and individually labelled outputs, with dataset presets, preferred-WT selection, optional separator normalization, recipes, and consolidated processing logs.

Retired user routes are the controller Pillow dropdown, separate preferred-WT applet, full-column detector, global-visibility launcher, presentation-normalized output, generic dedup CLI, partial-output flag, and direct unrecorded custom entrypoints. Their proven Pillow helpers remain internal to the unified endpoint.

## Alignment and export

The active route uses R1C1, R1C-last, R5C1, and R5C-last to interpolate the 8 by N grid mathematically. The installed ROI 1-click Rotated Rectangle Click Tool supplies placement. A disposable whole-image duplicate receives two CLAHE passes; source pixels remain unchanged.

QC is optional. Accept exports and Retry repeats placement. Without QC, export follows four clicks. Both paths bounds-check every Top and Low rectangle before replacement archiving and before the first crop write. Crop dimensions default to 130 by 546 and remain configurable.

Rerun reads authoritative images.csv and always forces a replacement manifest. Ordinary single remains pending-only. Selected files must be inside image_root. After accepted crop export—or after accepted register-only QC—batch and single routes persist a versioned GridCoordinateAsset beside project metadata. It records the explicit source-image pixel coordinate system, four measured references, row/column geometry, and named spots such as r1c1. Default export ordering remains bounds-check all crops, archive replacements, write crops, record crop completion, then publish the grid handoff.

## Lifecycle and AHK

Batch handoff is TSV keyed by folder plus filename. The controller checks ROI readiness, tracks only owned processes, and does not call wrapper exit a crop success. Success requires the Fiji macro completion sentinel. Cancel exits cleanly; restart writes a resume marker and relaunches; early or nonzero exit fails closed.

Generated Fiji macros do not use ImageJ `print`, so runs do not create a separate Log window. Completed Batch All, Batch Folder, Single, and Single Rerun sessions append to the dataset-level `matrix_output/Processing Logs/Four-Point Alignment Runs.txt` under sequential `Run NNN` dividers; interrupted sessions are not recorded as completed.

Windows PID liveness uses OpenProcess and WaitForSingleObject. Never use os.kill(pid, 0) on Windows because it terminates for non-console signals.

The AHK v2 helper restricts Java-frame and shell-hook handling to fiji-windows-x64.exe. Preserve launcher AlwaysOnTop removal plus MoveBottom, native toolbar placement, source hiding, owned-window cancel cleanup, 1.8-second duplicate prompt containment, and AHK restart signaling. RMI, socket, and direct ij.ImageJ attachment failures remain documented in docs/research/fiji-four-point-runtime.md.

## Data and outputs

CSV validation rejects unheaded extra fields, Windows case-only identities, unsafe output components, and Strain values that sanitize to the same folder. Reconciliation, finalization, freshness, and inventory use case-insensitive Windows identity while retaining physical spelling.

The read-only V10 adapter preserves the workbook and canonical terminology, and validates required schema, field types/mappings, duplicate identities, missing values, starred machine columns, `sessionUID`/`Image UID`, profile `Pos`, and strain-profile `Order`. It embeds explicit `PlateLayout` row-band provenance while leaving the intentionally simpler CSV contract unchanged. Stateful project records live under `State/workflow_project.json` and reject stale/mismatched grid-dependent work.

Saved-grid culture export validates every requested Top/Low rectangle before writing, publishes immutable numbered runs under distinct `Crops/Unprocessed` and `Crops/Processed` parents, and records source/grid/layout provenance. Mixed-tier composition accepts only current recorded crops, permits Top and Low choices in one matrix, previews without writes, validates a complete requested layout, and publishes immutable numbered runs under `Matrices/Mixed Tier`.

The unified Pillow endpoint filters to selected groups/strains, conditions, and Top/Low states, then requires exact current crops only for that selected metadata contract. It stages disposable copies, normalizes only staging, runs all checked mature renderers before publishing, and never overwrites past numbered runs. Matrix outputs are categorized and copied to `!All Matrix Exports`; labelled crops are grouped by Experiment/Strain and excluded from the aggregate.

Custom composition is Raw only. Presentation recipes and direct presentation shims fail explicitly. Deduplicated all-strains output requires a selected WT Experiment/Set; names record actual retained WT provenance in experiment order, with numeric Sets before lettered Sets.

## Validation and remaining boundary

Automated coverage includes compileall, Ruff checks, the current suite, synthetic prepare-only batch, single/rerun/register-only routing, durable grid handoff/finalization and consumer reuse, V10 parsing/layout, stateful project applets, later culture export, mixed-tier composition, bounds/archive ordering, every unified Pillow output family across experiments and states, run preservation/categorization, presets and WT naming, CSV/reconciliation safety, launchers, nondestructive Windows PID probing, AHK hotfix contracts, and failure-closed Fiji wrapper behavior.

Manual-only boundaries are real visual click/QC and derivative presentation quality, plus an installed Fiji/Jaunch desktop session confirming default export and register-only behavior in the real window stack. Real image pixels remain image-blind to agents; the exact batched checks are in `MANUAL_VALIDATION_BACKLOG.md`.
