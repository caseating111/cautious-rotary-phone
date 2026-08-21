# Agent control

This repository develops a practical Fiji + Python/Pillow workflow for experiment-aware plate-image alignment, cropping, display/QC, annotation, matrices and later quantitative scoring.

Repository state, executable checks, actual script behaviour and accepted data contracts outrank chat-history reconstructions.

## Core product posture

Preserve the useful existing workflow and improve it incrementally. Reliability, source-image safety, transparent geometry and low-friction human QC matter more than architectural novelty.

Fiji is the interactive scientific-image environment. Python/Pillow handles repeatable file/data/image composition work where appropriate. AutoHotkey is a thin global-hotkey/UI convenience layer only. A later Python controller may coordinate these pieces, but it must not absorb mature functionality merely to centralise it.

For every substantial capability, use this decision order:

`END FUNCTION -> EXISTING FIJI/IMAGEJ FEATURE OR TRUSTED PLUGIN -> MATURE DOMAIN TOOL/PACKAGE -> COMPOSE MULTIPLE EXISTING TOOLS -> THIN ADAPTER/BRIDGE -> SMALL CUSTOM IMPLEMENTATION FOR THE TRUE GAP -> BESPOKE REPLACEMENT ONLY AS LAST RESORT`

A candidate tool does **not** need to satisfy 100% of the desired workflow by itself. If it solves a major part reliably, first investigate whether its limitation can be covered by a small adapter, preprocessing/postprocessing step, companion plugin/package, saved ROI/state, scripting wrapper or manual QC step.

Do not reject a mature solution merely because one desired behaviour is missing. Do not use the missing 10-20% as justification to reimplement the other 80-90% from scratch.

Before writing non-trivial original image-processing, segmentation, registration, ROI-management, interpolation, statistics, annotation, file-format or GUI machinery:

1. Identify the exact end function and constraints.
2. Check Fiji/ImageJ built-ins and established Fiji/ImageJ plugins or update sites.
3. Check mature Python packages where Python is the appropriate layer.
4. Check whether a reliable composition of existing tools solves the end-to-end task.
5. Document why the remaining gap genuinely requires custom code.
6. Keep that custom code as narrow and replaceable as practical.

Prefer boring, maintained, testable dependencies over clever custom algorithms. Existing custom code has no sunk-cost privilege, but working behaviour should not be discarded without a concrete improvement and compatibility plan.

## Workflow invariants

### Manual alignment remains authoritative

Do **not** remove the manual first/last-column alignment step unless the user explicitly changes this requirement.

The intended direction is to make those manual references more informative and less tedious: use whole-column references where practical, calculate the regular grid from them, tolerate weak/missing/smeared colonies, and show a full-grid QC overlay before accepting geometry.

Automatic/refined detection may assist the selected columns, but the user's first/last-column placement is authoritative. Provide retry/re-align rather than silently overriding it.

### Source and quantitative data safety

- Original image pixels are source data and should remain unchanged unless an explicitly separate derived output is being produced.
- Routine visibility normalisation should preferably change Fiji display range only.
- Quantitative stress/scoring measurements must use unmodified pixel data, not display-enhanced or annotation-rendered images.
- Derived crops, matrices, annotated images and reports belong in explicit output locations.

### Global visibility normalisation

Preferred normal approach once total-grid geometry exists:

1. estimate background from a band immediately outside the total-grid ROI, preferably considering top/bottom/left/right strips independently;
2. use robust statistics rather than raw minimum/simple mean and reject obviously contaminated side samples where justified;
3. estimate the high display point from pixels inside the total-grid ROI using a robust high percentile;
4. apply one resulting black/white display range uniformly to the whole image;
5. keep CLAHE/local enhancement optional rather than the default because local contrast changes can undermine visual consistency.

### Separation of responsibilities

- **Fiji/ImageJ:** interactive alignment/calibration, ROI/grid preview, image display/QC and scientific-image operations where Fiji already provides the strongest solution.
- **AutoHotkey v2:** tablet/global hotkeys and small window-placement conveniences. No experiment/workflow logic.
- **Python/Pillow:** deterministic rotation/export, matrix generation, annotation/composition and metadata-driven derived outputs where Pillow is sufficient.
- **Python controller (later):** paths/configuration, validation and orchestration. Keep processing modular and callable outside the GUI.

Do not build a monolithic application when a small coordinator around stable tools is sufficient.

## Data contracts

Real experimental CSV contents must not be committed merely to make development convenient. Use synthetic/generic fixtures and examples.

Current important conceptual contracts are:

- `grid.csv`: experiment + set + grid column -> strain, including `GridCols`.
- `images.csv`: original source filename -> experiment/set/condition metadata. Original filenames are authoritative inputs; generated crop filenames are outputs, not a replacement metadata database.
- `condition_order.csv`: explicit desired condition/matrix order.
- `calibration.csv`: likely future persisted accepted alignment/grid geometry; do not freeze its schema until the improved full-column geometry is implemented and the actual required state is known.
- `config.json`: preferred future location for application paths/settings rather than proliferating hard-coded paths across scripts.
- `annotations.csv`: optional only. Prefer deriving annotations from existing metadata when possible.

Generated crop names may encode useful metadata for human readability, but scripts should not depend on reparsing filenames when authoritative structured metadata is already available.

## Development behaviour

- Inspect the actual active scripts before changing behaviour.
- Preserve currently working outputs unless a change is intentional and documented.
- Prefer small compatible steps over large rewrites.
- Keep geometry/math explicit and auditable rather than hidden behind unexplained constants.
- Validate CSV/config inputs and fail/skip clearly rather than corrupting a batch.
- Avoid destructive in-place processing by default.
- Make routine implementation/refactor/dependency choices autonomously when evidence is clear.
- A completed subtask is a transition point, not a reason to redesign unrelated parts.

## Research/reuse requirement

When considering a new capability, explicitly search the mature ecosystem before implementing it from first principles. Examples include Fiji/ImageJ update sites/plugins, Bio-Formats/ImageJ facilities, ROI Manager tooling, registration/grid/segmentation plugins, established Python imaging/scientific libraries and Pillow facilities.

Research should be driven by the desired function, not by exact wording. For example, if a requested "one-click ROI" tool nearly fits the need, investigate wrappers, ROI resizing, saved selections, macros or companion tools before deciding that a custom replacement is preferable.

The burden of proof is on bespoke implementation, not on reuse.

## Repository hygiene

- Never commit real experimental/private data, credentials, personal information or machine-specific secrets.
- Synthetic CSV fixtures/examples should be obviously fictional.
- Do not change repository visibility as part of ordinary development.
- Keep public-facing documentation focused on this repository's actual purpose; do not import unrelated predecessor-project history or rules.
- Prefer a feature branch for changes and a reviewable pull request rather than casual direct edits to the default branch.
