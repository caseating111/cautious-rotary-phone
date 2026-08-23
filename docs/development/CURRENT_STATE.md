# Current state

## Product and runtime

workflow-C is the active product branch. The supported environment is Windows, Miniforge environment workflow-c, Python 3.11, Pillow, Tkinter, Fiji/ImageJ, ROI 1-click Tools, and AutoHotkey v2.

Start with start_controller.cmd. It validates exact Python 3.11 plus Pillow and Tkinter for every candidate and never tries another interpreter after the controller has run. start_custom_matrix.cmd uses the same contract.

## Active endpoints

The controller provides project setup and CSV discovery; metadata reconciliation/preflight; all-folder, subfolder, single, and rerun four-point crop export; raw matrices, all-strains and labelled-individual outputs; explicit preferred-WT deduplication; and raw custom matrices with preview, recipes, and processing logs.

Retired user routes are the full-column detector, global-visibility launcher, presentation-normalized output, generic dedup CLI, partial-output flag, and direct unrecorded custom entrypoints.

## Alignment and export

The active route uses R1C1, R1C-last, R5C1, and R5C-last to interpolate the 8 by N grid mathematically. The installed ROI 1-click Rotated Rectangle Click Tool supplies placement. A disposable whole-image duplicate receives two CLAHE passes; source pixels remain unchanged.

QC is optional. Accept exports and Retry repeats placement. Without QC, export follows four clicks. Both paths bounds-check every Top and Low rectangle before replacement archiving and before the first crop write. Crop dimensions default to 130 by 546 and remain configurable.

Rerun reads authoritative images.csv and always forces a replacement manifest. Ordinary single remains pending-only. Selected files must be inside image_root. Accepted grid coordinates are not yet persisted; current docs must not claim they are.

## Lifecycle and AHK

Batch handoff is TSV keyed by folder plus filename. The controller checks ROI readiness, tracks only owned processes, and does not call wrapper exit a crop success. Success requires the Fiji macro completion sentinel. Cancel exits cleanly; restart writes a resume marker and relaunches; early or nonzero exit fails closed.

Windows PID liveness uses OpenProcess and WaitForSingleObject. Never use os.kill(pid, 0) on Windows because it terminates for non-console signals.

The AHK v2 helper restricts Java-frame and shell-hook handling to fiji-windows-x64.exe. Preserve launcher AlwaysOnTop removal plus MoveBottom, native toolbar placement, source hiding, owned-window cancel cleanup, 1.8-second duplicate prompt containment, and AHK restart signaling. RMI, socket, and direct ij.ImageJ attachment failures remain documented in docs/research/fiji-four-point-runtime.md.

## Data and outputs

CSV validation rejects unheaded extra fields, Windows case-only identities, unsafe output components, and Strain values that sanitize to the same folder. Reconciliation, finalization, freshness, and inventory use case-insensitive Windows identity while retaining physical spelling.

Pillow endpoints validate complete current exact crops, stage disposable copies, normalize only staging, and require a new non-empty output. Partial output is retired. Labelled Strain folders are Windows-validated and containment-checked below matrix_output.

Custom composition is Raw only. Presentation recipes and direct presentation shims fail explicitly. Deduplicated all-strains output requires a user-selected WT Experiment/Set.

## Validation and remaining boundary

Automated coverage includes compileall, Ruff F checks, the current pytest suite, synthetic prepare-only batch, single/rerun routing, bounds/archive ordering, raw Pillow outputs, CSV/reconciliation safety, launchers, nondestructive Windows PID probing, AHK hotfix contracts, and failure-closed Fiji wrapper behavior.

Manual-only boundaries are real visual click/QC quality and one installed Fiji/Jaunch desktop session confirming one usable GUI plus the redundant-launcher/window-stack workaround. Real image pixels remain image-blind to agents.
