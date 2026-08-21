# Implementation decision policy

This repository is operated under a practical time constraint. Optimize for the user's total time-to-reliable-result, not for maximal automation, architectural elegance, novelty, or completeness of custom code.

This policy is mandatory for all substantial implementation decisions.

## Primary objective

Reduce a multi-hour manual workflow to a much shorter, predictable, low-friction workflow. A partially manual route that cuts hours down to minutes is a success. Do not spend disproportionate engineering effort removing the final small amount of manual work unless the benefit is clear and the route is low risk.

Total cost includes:
- setup and installation;
- user operating time;
- user testing time;
- debugging and retesting;
- regression risk;
- maintenance burden;
- validation/audit time;
- fragility across machines or future versions.

A route that looks elegant in code but creates repeated test/debug cycles for the user is a bad route.

## Evidence ranking

When choosing an implementation, give strong preference to solutions with real-world evidence and maturity:

1. built-in Fiji/ImageJ functionality already known to work;
2. maintained, established Fiji/ImageJ plugins or scientifically used/published tools;
3. mature, widely used Python packages such as Pillow or established scientific libraries;
4. existing scripts/utilities that already perform the needed task reliably;
5. combinations of the above plus thin glue/manual steps;
6. narrowly scoped custom code for a genuine uncovered gap;
7. large bespoke implementations only with compelling evidence that the earlier options cannot produce a practical result.

Do not assume code written during one development session is superior to software that has been used, tested, maintained, or published over months or years.

## No exact-match requirement

An existing tool does not need to solve the request exactly.

Preferred solutions may be composed, patched, awkward, manual in places, or spread across multiple programs. Examples that are explicitly acceptable:

- plugin A does most of detection, plugin B does geometry, a macro connects them;
- Fiji handles ROI interaction, AHK reduces clicking, Pillow handles outputs;
- the user manually selects two or four reliable reference points and existing geometry tools calculate the rest;
- a plugin is close but requires a wrapper, coordinate translation, saved ROI, intermediate file, or small patch;
- CSVs are translated by a GUI/helper before being passed to existing scripts;
- a manual QC/accept step remains because it is faster and safer than building a complex automatic validator.

A cobbled-together workflow that reliably works is preferable to a theoretically unified bespoke application that is fragile.

## Mandatory reuse search

Before substantial custom implementation:

1. define the end function in plain language;
2. decompose it into smaller functions;
3. check Fiji/ImageJ built-ins;
4. check established plugins/update sites and scientific tools;
5. check mature Python packages/utilities;
6. check whether multiple tools can be composed;
7. check whether manual input or QC can cheaply close the remaining gap;
8. check wrappers, macros, patching, preprocessing/postprocessing, file exchange, coordinate conversion and CSV translation;
9. repeat the search using alternate terminology before concluding that the route is unavailable.

"No single tool does exactly this" is not sufficient justification for bespoke implementation.

## Immediate practicality test

Prefer routes that can be demonstrated quickly as a small end-to-end working slice using representative synthetic/test data.

Before expanding a new architecture, first prove the smallest useful route from input to output. Do not build hundreds or thousands of lines around a speculative component before confirming that the key external tool/plugin/package actually works with this workflow.

A solution that requires substantial compatibility surgery, legacy dependency resurrection, extensive environment pinning, or repeated patching before it can perform the basic task is a long-shot route. Reconsider it before investing further.

## Stop-loss rule

Repeated failure is evidence about the approach, not merely an invitation to add another patch.

Stop and reassess the route when any of the following occur:
- repeated user test -> failure -> patch -> retest cycles;
- new patches break previously working functions;
- custom code grows mainly to work around earlier custom code;
- a legacy dependency requires increasingly invasive compatibility fixes;
- the user must spend more time testing the automation than the manual workflow would cost;
- the design is becoming difficult to validate end-to-end;
- a simpler mature-tool composition would provide most of the time saving.

When a stop-loss condition appears, return to ecosystem search and composition. Do not continue escalating custom complexity by default.

## Manual oversight is allowed and often valuable

Manual interaction is not a failure state.

Keep manual steps when they:
- provide useful scientific/visual validation;
- are fast and predictable;
- replace brittle automated inference;
- would need to be checked manually later anyway;
- materially reduce implementation/testing risk.

Do not automate away human validation merely to increase an automation percentage.

## GUI principle

The GUI is primarily a simplification and orchestration layer.

It should make a multi-tool workflow feel simple by controlling:
- paths;
- config/presets;
- macro/plugin toggles;
- Fiji launch/control;
- AHK helpers;
- Pillow/script settings;
- CSV creation/translation/validation;
- processing stages;
- status/errors and handoffs.

The GUI does not need to contain the processing itself. Native functionality should stay in mature tools when practical.

## Default decision rule

When comparing two workable routes, prefer the one with lower total user burden and higher demonstrated reliability, even if it is less elegant, less automated, or more manually supervised.

The project is successful when the workflow becomes substantially faster, less taxing, easier to validate and less fragile—not when it contains the most original code.