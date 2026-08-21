# Custom composition / focused matrix workflow

## Goal
Make it cheap to re-compose already-generated crops into focused comparisons without rerunning Fiji or maintaining alternate source CSVs.

The expensive/manual **processing scope** and cheap **composition scope** are separate:
- processing scope decides which plates/strains need Fiji alignment/crop generation;
- composition scope chooses any available subset of current crops for Pillow outputs.

Authoritative project CSVs remain complete and unchanged. Custom composition uses temporary filtered copies only.

## Agreed behavior

### Default remains existing full output
The established Pillow jobs keep their current default behavior: all applicable experiment/set/strain/condition rows from the authoritative CSVs.

Custom composition is opt-in.

### GUI selection
Custom matrix selection should allow:
- one or more Experiment/Set groups;
- independent strain/column selection within each selected Experiment/Set;
- a condition/type subset;
- Top, Low or both;
- later, existing output variants such as all/no-extra-WT where applicable.

The GUI shows strain names to the user but stores grid column numbers internally because column identity is the stable crop contract.

Examples:
- E1/S0 columns 1+3 plus E2/A columns 2+4;
- E2/A only, columns 1+3+4;
- E2/A only, selected conditions 2+4;
- Top only, Low only or both.

### Selection inheritance
The last custom selection is automatically reusable as the starting point for the next focused comparison. This is convenience only, not a new metadata source.

### Existing crops first
Focused composition should normally use existing current crops only. It must not silently launch Fiji or recrop because a requested cell is missing.

The UI should report crop availability and identify missing selections. A later explicit "missing only" processing handoff may be useful, but composition and processing remain distinct actions.

### Preview-first multi-output default
When one request would generate multiple images, default to previewing only the first representative output before rendering the rest. Acceptance should freeze one recipe/settings set for the remaining batch.

Single-image output does not need a mandatory duplicate preview. Keep an override to generate all without preview for trusted settings.

Preview is for checking selection/layout/labels/display appearance, not for building a freeform image editor.

### Raw versus presentation-normalized
Preserve raw crops and existing raw matrix output.

Add an optional presentation-normalized output mode later. Normalization must operate only on disposable staging/derived copies, never on source pixels or stored quantitative crops. Prefer reusing accepted plate-level Fiji display-range values where available rather than independently beautifying each crop.

### Control / WT source
The inherited current no-extra-WT case uses E2/A, but control source must become GUI-selectable because the biologically preferred control depends on the experiment.

Do not hard-code biological choice deeper into Pillow scripts.

### Human processing logs + machine recipes
For generated focused outputs, keep two representations:
- clear human-readable TXT processing logs;
- machine-readable JSON output recipes for exact reconstruction/reopen.

Human-intended naming should be descriptive, not opaque. Preferred output-side folder is `Processing Logs`.

Machine files may be more technical and should be separated, e.g. `_workflow/output-recipes` or equivalent inside the experiment/output area.

TXT and JSON records should share an output/recipe identifier and include at least:
- created time;
- output path/type;
- Experiment/Set selections;
- selected strain columns/names;
- conditions;
- Top/Low state;
- raw/presentation mode;
- control source when relevant;
- required/available/used crop counts;
- missing/skipped warnings;
- settings needed to reproduce the output.

Do not build a database for this.

### Labels/layout
Overall plate annotation positions/spacing are plate-specific. Presets may cover stable style settings such as font, size, colour and orientation, but do not force fixed plate-specific positions.

Pillow matrices are regular enough for reusable label/font/margin/gap templates, and their label spacing should continue to follow the crop/matrix geometry.

### V10.2 workbook
V10.2 integration is deliberately deferred until further workflow discussion. It already lists the full strain universe and is likely to become the human-maintained master source later.

Expected eventual pattern:
`V10.2 complete master data -> initial processing selection -> crop inventory -> GUI composition selection -> Pillow outputs`.

Do not create a parallel long-term workbook while this is deferred.

## Current implementation slice
`tools/custom_matrix_selection.py` adapts the established `make_matrices.py` route without changing the legacy matrix builder:
- filters temporary grid/images/condition CSVs;
- stages only exact selected current crop filenames;
- normalizes orientation only on staged copies;
- patches only the generated configured script's `STATES_TO_BUILD` setting;
- runs the established Pillow matrix generator.

`tools/custom_matrix_gui.py` provides the first lightweight GUI selection surface, with all values selected initially or restoration of the previous selection.

`start_custom_matrix.cmd` is a direct Windows launcher while controller integration remains a later small orchestration change.

## Reuse / external-tool notes
Do not build a freeform figure designer into the controller. Pillow remains the deterministic regular-layout tool. If later presentation work needs arbitrary figure rearrangement, investigate mature Fiji/ImageJ figure tooling such as QuickFigures as an optional handoff instead of reproducing its capabilities.

For plate alignment/peak detection, existing BAR/ImageJ fallbacks remain governed by the current alignment docs; custom composition does not change that decision.
