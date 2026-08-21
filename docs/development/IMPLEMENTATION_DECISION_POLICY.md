# Implementation decision policy

This repository is operated under a practical time constraint. Optimize for the user's total time-to-reliable-result, not for maximal automation, architectural elegance, novelty, completeness of custom code, or software-development output for its own sake.

This policy is mandatory for all substantial implementation decisions.

## Primary objective: the end product, not the code

The user's goal is to obtain useful processed experimental/image outputs with substantially less effort. The code is only transport to that destination.

The primary deliverables are things such as:
- correctly aligned/cropped plate images;
- usable matrices/composites;
- annotations;
- visibility/QC improvements;
- validated metadata flow;
- reliable measurements/scoring;
- reduced repetitive manual work.

A GUI, macro, script, package integration, plugin patch or Python module is not successful merely because it is technically sophisticated. It is successful only if it helps produce the actual desired outputs more quickly, reliably and with less user burden.

Do not optimize for "building software". Optimize for **getting the user's real work done**.

## Time-cost objective

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

## Concision is part of practicality

Use the shortest reliable route in both implementation and communication.

Do not produce large amounts of code, architecture, documentation, explanation, scaffolding, abstraction or configuration when a smaller existing-tool composition will do the job. Do not confuse comprehensiveness with usefulness.

Default to concise status updates, concise instructions and small diffs. Put durable detail in repository documentation rather than repeatedly sending the user walls of text. Expand only when the complexity genuinely requires it or the user asks.

A solution that needs 20 lines of glue around mature tools is normally preferable to hundreds of lines of original machinery providing the same practical result.

## Evidence ranking

When choosing an implementation, give strong preference to solutions with real-world evidence and maturity:

1. built-in Fiji/ImageJ functionality already known to work;
2. maintained, established Fiji/ImageJ plugins or scientifically used/published tools;
3. other mature programs/utilities that already perform the required operation;
4. mature, widely used Python packages such as Pillow or established scientific libraries;
5. a tool's own macro/scripting/plugin/API facilities;
6. combinations of the above plus thin glue/manual steps;
7. narrowly scoped custom code for a genuine uncovered gap;
8. large bespoke implementations only with compelling evidence that the earlier options cannot produce a practical result.

Do not assume code written during one development session is superior to software that has been used, tested, maintained, scientifically validated, or published over months or years.

## Mandatory decision questions

Before writing new functionality, ask these questions in order:

1. **Can I find this online or in software already available?**
2. **If the existing solution is not exact, can I adapt it?**
3. **Does it have a macro system, scripting interface, plugin architecture, command interface, API, presets or configuration that can make it fit?**
4. **Can I patch the close-fit tool instead of replacing it?**
5. **Can part of the task happen in one mature tool and another part in a different mature tool?**
6. **Can a manual click/reference/QC step close the remaining gap cheaply and safely?**
7. **Can thin glue—AHK, a macro, Pillow, CSV translation, file exchange, coordinate conversion or a GUI wrapper—connect the pieces?**
8. **If not, have I repeated the search using alternative terminology and smaller decomposed subproblems?**
9. **Only then: what is the smallest piece of original code still genuinely necessary?**

"I can code this" is not justification for coding it.

"No single tool does exactly this" is not justification for coding the entire solution.

## No exact-match requirement

An existing tool does not need to solve the request exactly.

Preferred solutions may be composed, patched, awkward, manual in places, or spread across multiple programs. Examples that are explicitly acceptable:

- plugin A does most of detection, plugin B does geometry, a macro connects them;
- Fiji handles ROI interaction, AHK reduces clicking, Pillow handles outputs;
- the user manually selects two or four reliable reference points and existing geometry tools calculate the rest;
- a plugin is close but requires its own macro system, a wrapper, coordinate translation, saved ROI, intermediate file, or small patch;
- CSVs are translated by a GUI/helper before being passed to existing scripts;
- a manual QC/accept step remains because it is faster and safer than building a complex automatic validator;
- one program produces an intermediate representation that another mature program consumes.

A cobbled-together workflow that reliably works is preferable to a theoretically unified bespoke application that is fragile.

## Mandatory reuse search

Before substantial custom implementation:

1. define the end function in plain language;
2. decompose it into smaller functions;
3. check Fiji/ImageJ built-ins;
4. check established plugins/update sites and scientific tools;
5. check other mature desktop/CLI utilities;
6. check mature Python packages/utilities;
7. inspect the promising tools' built-in macro/scripting/API/configuration capabilities;
8. check whether multiple tools can be composed;
9. check whether manual input or QC can cheaply close the remaining gap;
10. check wrappers, macros, patching, preprocessing/postprocessing, file exchange, coordinate conversion and CSV translation;
11. repeat the search using alternate terminology before concluding that the route is unavailable.

## Immediate practicality test

Prefer routes that can be demonstrated quickly as a small end-to-end working slice using representative synthetic/test data.

Before expanding a new architecture, first prove the smallest useful route from input to output. Do not build hundreds or thousands of lines around a speculative component before confirming that the key external tool/plugin/package actually works with this workflow.

A solution that requires substantial compatibility surgery, legacy dependency resurrection, extensive environment pinning, or repeated patching before it can perform the basic task is a long-shot route. Reconsider it before investing further.

A less elegant route that works immediately or nearly immediately has a strong advantage over a theoretically superior route with uncertain integration and testing cost.

## Testing budget and stop-loss rule

The user's testing burden has previously exceeded the manual work the automation was supposed to replace. That is an explicit failure condition and must not be normalized.

User testing is expensive. The agent should perform every feasible non-user check before asking for manual validation.

Repeated failure is evidence about the approach, not merely an invitation to add another patch.

Stop and reassess the route when any of the following occur:
- repeated user test -> failure -> patch -> retest cycles;
- new patches break previously working functions;
- custom code grows mainly to work around earlier custom code;
- a legacy dependency requires increasingly invasive compatibility fixes;
- the user must spend more time testing the automation than the manual workflow would cost;
- the design is becoming difficult to validate end-to-end;
- a simpler mature-tool composition would provide most of the time saving;
- the route has become dependent on increasingly speculative assumptions;
- the agent is spending more effort perfecting internal software than improving the actual end-product workflow.

When a stop-loss condition appears, return to ecosystem search and composition. Do not continue escalating custom complexity by default.

Do not treat sunk effort as a reason to preserve a bad route.

## Manual oversight is allowed and often valuable

Manual interaction is not a failure state.

Keep manual steps when they:
- provide useful scientific/visual validation;
- are fast and predictable;
- replace brittle automated inference;
- would need to be checked manually later anyway;
- materially reduce implementation/testing risk;
- preserve user authority over ambiguous alignment/selection decisions.

Do not automate away human validation merely to increase an automation percentage.

Ten minutes of reliable guided manual work can be far better than hours of testing an ambitious automatic system.

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

A successful GUI may simply make a cobbled-together but reliable workflow feel coherent to the user.

## Autonomous improvement rule

The agent is encouraged to identify and propose useful new workflow improvements without waiting for the user to specify every feature.

However, autonomy applies to **finding better ways to achieve the user's end result**, not to inventing larger bespoke software systems.

For every self-proposed improvement:
- start from the real workflow pain/time cost;
- look for mature existing solutions first;
- prefer adapting/composing them;
- prove the smallest useful route;
- preserve manual oversight where valuable;
- reject the idea if its likely testing/debugging burden outweighs its practical benefit.

Novel ideas are welcome. Novel code is not inherently valuable.

## Default decision rule

When comparing two workable routes, prefer the one with lower total user burden and higher demonstrated reliability, even if it is less elegant, less automated, more manually supervised, or internally cobbled together.

The project is successful when the workflow becomes substantially faster, less taxing, easier to validate and less fragile—not when it contains the most original code or the most comprehensive program.