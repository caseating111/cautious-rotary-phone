# Agent control

This repository exists to make a real image-processing/experimental workflow faster, easier, less tiring and easier to validate. **The software is not the product. The processed images, crops, matrices, annotations, measurements and reduced user workload are the product.** Scripts, macros, plugins, GUI controls and glue code are only means of getting there.

Repository state, executable checks, actual script behaviour and accepted data contracts outrank chat-history reconstructions.

## Mandatory implementation decision policy

Before any substantial implementation decision, read and follow `docs/development/IMPLEMENTATION_DECISION_POLICY.md`.

That policy is binding. In particular:
- assume the user is operating under a practical time constraint unless explicitly told otherwise;
- optimize total user time-to-reliable-result, including setup, testing, debugging, regression risk and validation, not just coding time;
- treat coding as an implementation tool, never as the deliverable or default objective;
- prefer mature/tested/published tools and composed workflows over fresh bespoke code;
- an approximate, patched, multi-tool or partially manual route is acceptable if it removes most of the burden;
- prove a small end-to-end route before expanding a speculative architecture;
- repeated patch/test failures trigger reassessment of the approach rather than automatic escalation;
- substantial bespoke code requires clear evidence that mature-tool composition, patching, wrappers, built-in macro/scripting systems, manual steps and thin glue cannot provide a practical result.

Do not assume code written in one session is likely to outperform or be more reliable than established software that has been tested, maintained, used scientifically, or published over months or years.

## Codex privacy boundary for real sample images

This is an inviolable project rule for local Codex work unless the user explicitly revokes it.

- Real/sample experimental images must remain outside the repository and must never be committed, pushed, attached to issues/PRs, copied into repository fixtures, or sent to external review services.
- Codex must not open, render, preview, screenshot, OCR, visually inspect, thumbnail, image-search, or otherwise ingest the pixel content of real/sample experimental images into model context.
- Codex may pass local image file paths to Fiji/ImageJ, Python, AHK, or other local tools for processing, but must consume only non-image outputs such as exit codes, structured numeric measurements, ROI coordinates, dimensions, filenames, logs, window geometry, generated macro text, test status, and other textual/structural diagnostics.
- Do not use Python/Pillow/OpenCV or any other library to load real/sample image pixels for Codex-side inspection. If a test would require visual interpretation of the image, record the exact manual validation required and ask the user to perform it.
- Screenshots containing sample-image pixels are also prohibited model input. Automated desktop tests should query window titles/positions/state and logs rather than capture the sample image canvas.
- Synthetic/public test images may be used only when clearly designated as such and when they contain no real experimental data.
- Real/sample CSV metadata may be read only when the user has intentionally anonymized it for this workflow. Do not infer or reconstruct sensitive biological meaning from genericized identifiers.
- Gemini/Antigravity or any other external reviewer must never receive real/sample images or image-derived screenshots. Review packets must contain code/diffs/generated scripts/sanitized logs/numeric diagnostics only.

If local permissions prevent access to an outside-repository image path, ask for the narrow filesystem permission/path access needed; do not solve this by copying the image into the repository.

## End-product-first rule

This is a hard rule.

Do not optimize for producing a sophisticated application, large codebase, elegant architecture, reusable framework or impressive automation. Optimize for helping the user get the actual experimental/image outputs they need with substantially less effort.

Before building anything, ask in this order:

1. **Can I find an existing tool/plugin/package/program that already does this or most of this?**
2. **If it is not an exact fit, can I make it fit using its own macro/plugin/scripting/configuration system?**
3. **Can I patch, wrap, configure or adapt it rather than replace it?**
4. **Can several existing tools divide the job between them?**
5. **Can a small manual step provide the missing judgement/validation cheaply?**
6. **Can a macro, AHK helper, Pillow step, CSV translator, file handoff, coordinate conversion or GUI wrapper bridge the remaining gap?**
7. **Only then: what is the smallest amount of original code genuinely required?**

The question is not primarily "can I code this?". The questions are "does this already exist?", "can an approximate existing solution be adapted?", and "can multiple mature components be made to work together?".

## Core product posture

Preserve the useful existing workflow and improve it incrementally. Reliability, source-image safety, transparent geometry and low-friction human QC matter more than architectural novelty.

The optimization target is **major reduction in user time and cognitive load**, not theoretical perfection, maximal automation, or a single elegant architecture. A workflow that reduces a multi-hour manual process to roughly ten minutes of guided/manual work can be an excellent outcome even if it still contains deliberate human steps.

Manual oversight is not automatically technical debt. In this project it can be a valuable validation layer, especially when the user would otherwise need to review outputs later anyway. Do not remove reliable human checkpoints merely to claim higher automation.

Fiji is the interactive scientific-image environment. Python/Pillow handles repeatable file/data/image composition work where appropriate. AutoHotkey is a thin global-hotkey/UI convenience layer only. A later Python controller may coordinate these pieces, but it must not absorb mature functionality merely to centralise it.

For every substantial capability, use this decision order:

`END FUNCTION -> EXISTING FIJI/IMAGEJ FEATURE OR TRUSTED PLUGIN -> OTHER MATURE PROGRAM/TOOL -> MATURE DOMAIN PACKAGE -> USE TOOL'S BUILT-IN MACRO/SCRIPTING/API -> COMPOSE MULTIPLE EXISTING TOOLS -> PATCH/CONFIGURE/WRAP EXISTING TOOL -> MANUAL VALIDATION/REFERENCE STEP -> THIN ADAPTER/BRIDGE -> SMALL CUSTOM IMPLEMENTATION FOR THE TRUE GAP -> BESPOKE REPLACEMENT ONLY AS LAST RESORT`

## Mandatory composition-first rule

This is a hard project rule, not a preference.

A workable existing route does **not** need to be elegant, direct, fully automatic, or provided by one tool. It does not need to satisfy 100% of the desired workflow by itself.

Prefer combinations of mature tools even when the route is somewhat cobbled together. For example:

`Tool/plugin A solves ~60% + Tool/plugin B solves ~30% + manual step/glue/adapter solves ~10% = preferred route`

Likewise, if an established plugin approximately performs the required function but needs manual point clicks, ROI repositioning, intermediate files, coordinate translation, CSV conversion, AHK assistance, Pillow post-processing, a macro wrapper, its own scripting system, a small patch, or another apparently hacky bridge, that is **not** a reason to reject it.

Do not interpret multiple programs, intermediate files, manual references, wrappers, macros, patched plugins, or thin glue as architectural failure. "Messy internally but simple for the user" is acceptable when it is reliable enough.

A mature tool that solves 60-90% of the problem has a strong presumption in its favour. The missing portion should first be addressed by configuration, composition, patching, scripting, glue, manual interaction, preprocessing/postprocessing, or another mature tool.

Do **not** respond to "this exact feature is not implemented in this exact way" by escalating directly into a large original implementation.

Before writing substantial bespoke functionality, the agent must perform a second-pass reuse check using alternate terminology and decomposed subproblems. Specifically ask:

1. Can an existing Fiji/ImageJ feature or plugin do any substantial portion?
2. Can another mature desktop/scientific/image tool do it?
3. Can two or more existing tools together cover most of it?
4. Does a close-fit tool expose macros, scripts, plugins, commands, APIs, presets or automation that can make it fit?
5. Can an approximate plugin be configured, patched, wrapped or complemented rather than replaced?
6. Can a small manual step preserve validation while removing most of the time cost?
7. Can a thin adapter, macro, file exchange, coordinate translation, CSV translation or GUI wrapper close the remaining gap?
8. Can the GUI hide the multi-tool complexity so the user still has one simple control surface?
9. If the answer still appears to be no, search/check once more before authorizing substantial custom code.

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
- fewer fragile scripts the user must repeatedly test;
- finished image outputs produced sooner and with less effort.

The "best" technical solution is not necessarily the most elegant or most automated one. A good-enough, robust, partially manual composition is often the intended solution.

## Testing-budget rule

**Testing efficiency:** Default to targeted, minimum-sufficient validation. Do not perform exhaustive, redundant, or speculative testing. Expand beyond affected paths only when a test fails, observed runtime behavior contradicts expectations, evidence indicates a broader regression, or the user explicitly requests broader audit/regression testing. Reuse valid existing test evidence and do not rerun unchanged tests without a concrete reason. Optimize for reaching a reliably user-testable product quickly.

The user has already experienced a testing/debugging burden that exceeded the original manual work. **Do not allow that pattern to repeat.**

User testing time is scarce and expensive. Do not casually hand the user successive speculative builds to debug for you.

Before requesting manual testing:
- perform all checks possible without the user;
- keep the tested change narrow;
- prefer testing a proven external tool or small integration slice over a large new architecture;
- state exactly what needs validation and why;
- avoid bundling unrelated experimental changes.

If repeated user testing is required, treat that as evidence that the route itself may be poor. Apply the stop-loss policy rather than automatically generating another patched version.

## Autonomous continuation and deferred questions

For Codex/local-agent work, `docs/development/AUTONOMY_SCOPE.md` narrows this older guidance and is authoritative where there is conflict. Default autonomy is task-scoped, not open-ended persistent improvement.

Within the active requested objective, make routine implementation, dependency, refactor, UI/default and Git decisions autonomously. Record non-blocking user/manual questions in the deferred/current-state docs and continue only as needed to complete and validate that objective.

Do not automatically start unrelated improvements or the next roadmap item after the requested objective and its necessary validation/cleanup are complete.

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

## Anaconda ecosystem preference

Anaconda/conda is a preferred environment and package ecosystem for Python/scientific tooling where it is useful. Reuse packages already available through Anaconda/conda before adding bespoke equivalents or unnecessary separate dependency stacks.

Do not force Anaconda into a path that does not benefit from it, and do not interrupt higher-value current work merely to migrate functioning components. Integrate it opportunistically for future scientific/image/data capabilities, environment reproducibility and dependency management when that reduces setup or maintenance burden.

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
- **AutoHotkey v2 only:** tablet/global hotkeys and small window-placement conveniences. All repository AHK scripts must use AutoHotkey v2 syntax and run under an AutoHotkey v2 executable. AutoHotkey v1 compatibility is not required and must not influence implementation; do not use v1 syntax or v1/v2 hybrid patterns.
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
- Propose useful adjacent workflow improvements when they plausibly reduce user effort or improve validation, but do not implement them automatically outside the active task scope; record them for later unless the user explicitly broadens scope.
- If a composed route needs a few manual steps but achieves a major time-cost reduction, implement it rather than continuing to chase total automation.
- If a mature plugin/package is close but not exact, prefer adapting or patching it over replacing it unless there is concrete evidence that adaptation is less reliable or more costly.
- Do not expand a speculative architecture until a small representative end-to-end route has actually worked.
- Treat repeated fragile patches or repeated user retesting as evidence that the implementation route may be wrong.
- Never mistake "more code completed" for "more progress". Progress means getting the user's real workflow closer to a reliable, low-effort result.
- Routine Codex development goes directly to `workflow-C`; do not create side branches for ordinary fixes, features, tests or documentation. Use another branch only when there is a concrete isolation/review need.

## Research/reuse requirement

When considering a new capability, explicitly search the mature ecosystem before implementing it from first principles. Examples include Fiji/ImageJ update sites/plugins, Bio-Formats/ImageJ facilities, ROI Manager tooling, registration/grid/segmentation plugins, established Python imaging/scientific libraries, Pillow facilities, command-line utilities and other established desktop tools.

Research should be driven by the desired function and decomposed subfunctions, not by exact wording. For example, if a requested "one-click ROI" tool nearly fits the need, investigate wrappers, ROI resizing, saved selections, macros, plugin patching, companion tools or follow-on transformations before deciding that a custom replacement is preferable.

If the first search suggests no exact match, run a second search with alternative terminology and component tasks before concluding that custom code is needed.

## Repository hygiene

- Never commit real experimental/private data, credentials, personal information or machine-specific secrets.
- Synthetic CSV fixtures/examples should be obviously fictional.
- Do not change repository visibility as part of ordinary development.
- Keep public-facing documentation focused on this repository's actual purpose; do not import unrelated predecessor-project history or rules.
- Do not treat pull requests or side branches as the default for routine work. Direct incremental commits to `workflow-C` are the normal Codex development path; reserve isolation branches for genuinely separate or risky work.
