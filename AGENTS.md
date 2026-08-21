# Agent control

This repository develops a practical Fiji + Python/Pillow workflow for experiment-aware plate-image alignment, cropping, display/QC, annotation, matrices and later quantitative scoring.

Repository state, executable checks, actual script behaviour and accepted data contracts outrank chat-history reconstructions.

## Mandatory implementation decision policy

Before any substantial implementation decision, read and follow `docs/development/IMPLEMENTATION_DECISION_POLICY.md`.

That policy is binding. In particular:
- assume the user is operating under a practical time constraint unless explicitly told otherwise;
- optimize total user time-to-reliable-result, including setup, testing, debugging, regression risk and validation, not just coding time;
- prefer mature/tested/published tools and composed workflows over fresh bespoke code;
- an approximate or partially manual route is acceptable if it removes most of the burden;
- prove a small end-to-end route before expanding a speculative architecture;
- repeated patch/test failures trigger reassessment of the approach rather than automatic escalation;
- substantial bespoke code requires clear evidence that mature-tool composition, patching, wrappers, manual steps and thin glue cannot provide a practical result.

Do not assume code written in one session is likely to outperform or be more reliable than established software that has been tested, maintained, used scientifically, or published over months or years.

## Core product posture

Preserve the useful existing workflow and improve it incrementally. Reliability, source-image safety, transparent geometry and low-friction human QC matter more than architectural novelty.

The optimization target is **major reduction in user time and cognitive load**, not theoretical perfection, maximal automation, or a single elegant architecture. A workflow that reduces a multi-hour manual process to roughly ten minutes of guided/manual work can be an excellent outcome even if it still contains deliberate human steps.

Manual oversight is not automatically technical debt. In this project it can be a valuable validation layer, especially when the user would otherwise need to review outputs later anyway. Do not remove reliable human checkpoints merely to claim higher automation.

Fiji is the interactive scientific-image environment. Python/Pillow handles repeatable file/data/image composition work where appropriate. AutoHotkey is a thin global-hotkey/UI convenience layer only. A later Python controller may coordinate these pieces, but it must not absorb mature functionality merely to centralise it.

For every substantial capability, use this decision order:

`END FUNCTION -> EXISTING FIJI/IMAGEJ FEATURE OR TRUSTED PLUGIN -> MATURE DOMAIN TOOL/PACKAGE -> COMPOSE MULTIPLE EXISTING TOOLS -> PATCH/CONFIGURE/WRAP EXISTING TOOL -> THIN ADAPTER/BRIDGE -> SMALL CUSTOM IMPLEMENTATION FOR THE TRUE GAP -> BESPOKE REPLACEMENT ONLY AS LAST RESORT`

## Mandatory composition-first rule

This is a hard project rule, not a preference.

A workable existing route does **not** need to be elegant, direct, fully automatic, or provided by one tool. It does not need to satisfy 100% of the desired workflow by itself.

Prefer combinations of mature tools even when the route is somewhat cobbled together. For example:

`Tool/plugin A solves ~60% + Tool/plugin B solves ~30% + manual step/glue/adapter solves ~10% = preferred route`

Likewise, if an established plugin approximately performs the required function but needs manual point clicks, ROI repositioning, intermediate files, coordinate translation, CSV conversion, AHK assistance, Pillow post-processing, a macro wrapper, a patch, or another apparently hacky bridge, that is **not** a reason to reject it.

Do not interpret multiple programs, intermediate files, manual references, wrappers, macros, patched plugins, or thin glue as architectural failure. "Messy internally but simple for the user" is acceptable when it is reliable and maintainable enough.

A mature tool that solves 60-90% of the problem has a strong presumption in its favour. The missing portion should first be addressed by configuration, composition, patching, scripting, glue, manual interaction, preprocessing/postprocessing, or another mature tool.

Do **not** respond to "this exact feature is not implemented in this exact way" by escalating directly into a large original implementation.

Before writing substantial bespoke functionality, the agent must perform a second-pass reuse check using alternate terminology and decomposed subproblems. Specifically ask:

1. Can an existing Fiji/ImageJ feature or plugin do any substantial portion?
2. Can two or more existing tools together cover most of it?
3. Can an approximate plugin be configured, patched, wrapped or complemented rather than replaced?
4. Can a small manual step preserve validation while removing most of the time cost?
5. Can a thin adapter, macro, file exchange, coordinate translation, CSV translation or GUI wrapper close the remaining gap?
6. Can the GUI hide the multi-tool complexity so the user still has one simple control surface?
7. If the answer still appears to be no, search/check once more before authorizing substantial custom code.

Only after those checks may bespoke implementation be considered, and then it must be limited to the smallest genuinely uncovered gap.

The burden of proof is on bespoke implementation, not on reuse.

## Anti-perfection / anti-escalation rule

Do not optimize for "100% automated" when that increases development risk, testing burden, or user time.

Do not create a chain of increasingly complex original scripts merely because earlier custom attempts failed to achieve an idealized solution. Repeated custom-code patching that creates more manual testing, regressions, or unreliable behaviour is specifically contrary to this repository's goals.

When a custom route becomes fragile or keeps requiring new patches, stop escalating it. Reassess existing plugins/packages/tools and prefer a simpler composed route even if it leaves some manual interaction.

Prefer a reliable 80-95% reduction in effort over a brittle attempt at 100% automation.

Success should be measured by outcomes such as:
- hours of repetitive alignment/adjustment reduced to minutes;
- fewer precision clicks;
- fewer repeated settings changes;
- fewer manual file/CSV translations;
- clearer QC and easier retry;
- preserved source data and validation;
- fewer fragile scripts the user must repeatedly test.

The "best" technical solution is not necessarily the most elegant or most automated one. A good-enough, robust, partially manual composition is often the intended solution.

## GUI role

The GUI should simplify controls and hide orchestration complexity, not replace mature processing tools.

Prefer the GUI to provide a coherent control surface for:
- file and folder locations;
- persistent config;
- macro/plugin toggles;
- Fiji launch/control;
- AHK launch/stop;
- Pillow script settings;
- CSV validation and translation;
- presets;
- processing-stage enable/disable choices;
- status/errors;
- lightweight handoff between existing tools.

It is acceptable for the GUI to launch or coordinate several programs/scripts behind one button or workflow step.

Do not move Fiji-native interactive work into Python merely to make the application appear self-contained.

## Workflow invariants

### Manual alignment remains authoritative

Do **not** remove the manual first/last-column alignment step unless the user explicitly changes this requirement.

The intended direction is to make those manual references more informative and less tedious: use whole-column references where practical, calculate the regular grid from them, tolerate weak/missing/smeared colonies, and show a full-grid QC overlay before accepting geometry.

Automatic/refined detection may assist the selected columns, but the user's first/last-column placement is authoritative. Provide retry/re-align rather than silently overriding it.

Manual reference clicks are acceptable if they substantially reduce total time while preserving useful oversight.

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
- If a composed route needs a few manual steps but achieves a major time-cost reduction, implement it rather than continuing to chase total automation.
- If a mature plugin/package is close but not exact, prefer adapting or patching it over replacing it unless there is concrete evidence that adaptation is less reliable or more costly.
- Do not expand a speculative architecture until a small representative end-to-end route has actually worked.
- Treat repeated fragile patches or repeated user retesting as evidence that the implementation route may be wrong.

## Research/reuse requirement

When considering a new capability, explicitly search the mature ecosystem before implementing it from first principles. Examples include Fiji/ImageJ update sites/plugins, Bio-Formats/ImageJ facilities, ROI Manager tooling, registration/grid/segmentation plugins, established Python imaging/scientific libraries and Pillow facilities.

Research should be driven by the desired function and decomposed subfunctions, not by exact wording. For example, if a requested "one-click ROI" tool nearly fits the need, investigate wrappers, ROI resizing, saved selections, macros, plugin patching, companion tools or follow-on transformations before deciding that a custom replacement is preferable.

If the first search suggests no exact match, run a second search with alternative terminology and component tasks before concluding that custom code is needed.

## Repository hygiene

- Never commit real experimental/private data, credentials, personal information or machine-specific secrets.
- Synthetic CSV fixtures/examples should be obviously fictional.
- Do not change repository visibility as part of ordinary development.
- Keep public-facing documentation focused on this repository's actual purpose; do not import unrelated predecessor-project history or rules.
- Prefer a feature branch for changes and a reviewable pull request rather than casual direct edits to the default branch.
