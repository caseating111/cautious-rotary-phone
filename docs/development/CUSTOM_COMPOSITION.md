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
Custom matrix selection supports:
- one or more Experiment/Set groups;
- independent strain/column selection within each selected Experiment/Set;
- a condition/type subset;
- Top, Low or both.

The GUI shows strain names to the user but stores grid column numbers internally because column identity is the stable crop contract.

### Selection inheritance
The last **successful** custom selection is automatically reusable as the starting point for the next focused comparison. Failed/partial builds do not replace that convenience state. This is not a new metadata source.

### Existing crops first
Focused composition uses existing current crops only. It never silently launches Fiji or recrops because a requested cell is missing.

**Check selected crop availability** reports exact selected current/missing/stale/incompatible/duplicate crops. In presentation mode the same dialog also reports whether every selected source plate has a usable archived Fiji display range.

A later explicit "missing only" processing handoff may be useful, but composition and processing remain distinct actions.

### Preview-first multi-output default
When one request would generate multiple images, default to previewing only the first representative output before rendering the rest.

Preview validates/stages only that representative selection, including source freshness, then the accepted full build validates the complete requested selection. This avoids a redundant recursive scan of the complete crop tree before preview while retaining the actual full-build safety boundary.

Single-image output does not need a mandatory duplicate preview. Keep an override to generate all without preview for trusted settings.

Preview is for checking selection/layout/labels/display appearance, not for building a freeform image editor.

### Raw versus presentation-normalized
Raw crops and existing raw matrix output remain untouched.

Presentation-normalized mode reuses source-specific Fiji display ranges and applies them only to disposable staged crop copies. `fiji/apply_global_visibility_and_archive.ijm` runs the existing visibility calculation unchanged and archives the resulting range with source identity.

When `image_root` is configured, an archived range older than the current source image is rejected. The user must run **Global visibility** once on that current plate or choose Raw mode. Crop-only standalone composition keeps filename-identity validation without inventing a source root.

### Output postcondition
The established `make_matrices.py` generator remains unchanged, but focused wrappers no longer treat a merely non-empty output folder as sufficient success. Every selected Experiment/Set × requested Top/Low state must produce its expected `{Experiment}_{Set}_{State}_MATRIX.png` before the output is remembered/opened/recorded. A non-empty partial folder is left for inspection but is reported as failure.

### Control / WT source
The inherited no-extra-WT script executable behavior prefers E2/A despite an old contradictory E2/B comment. That ambiguity is not treated as biological authority.

`tools/run_dedup_with_control.py` patches only the generated copy's existing preference condition. The user chooses the Experiment/Set containing recognised WT X/Y controls. The GUI restores only the last **successful** user-selected control source when it is still present; otherwise it starts from the available list without a hard-coded E2/A default.

### Human processing logs + machine recipes
Focused outputs keep two representations:
- clear human-readable TXT processing logs under `Processing Logs`;
- machine-readable JSON output recipes under `_workflow/output-recipes` for reopen/rebuild.

The two records share the unique output-folder identifier and capture selection, display mode and crop counts. Do not build a database for this.

### Labels/layout
Overall plate annotation positions/spacing are plate-specific. Presets may cover stable style settings such as font, size, colour and orientation, but do not force fixed plate-specific positions.

Pillow matrices are regular enough for reusable label/font/margin/gap templates, and their label spacing should continue to follow the crop/matrix geometry.

### V10.2 workbook
V10.2 integration is deliberately deferred until further workflow discussion. It already lists the full strain universe and is likely to become the human-maintained master source later.

Expected eventual pattern:
`V10.2 complete master data -> initial processing selection -> crop inventory -> GUI composition selection -> Pillow outputs`.

Do not create a parallel long-term workbook while this is deferred.

## Current implementation
`tools/custom_matrix_selection.py` adapts the established `make_matrices.py` route without changing the legacy matrix builder: temporary filtered CSVs, exact selected crop staging, staged orientation normalization, state-setting patch, mature Pillow generation and explicit expected-output verification.

`tools/custom_matrix_gui_recorded.py` is the current user-facing surface. It adds selection restoration, detailed availability, raw/presentation mode, representative preview, prior-recipe reopening and processing-log access while remaining a separate thin GUI launched by the extended controller.

`tools/workflow_controller_extended.py` subclasses the original controller and adds only **Custom matrices** and **Preferred WT source** entry points. `start_controller.cmd` launches this extension. `start_custom_matrix.cmd` remains a direct launcher.

## Reuse / external-tool notes
Do not build a freeform figure designer into the controller. Pillow remains the deterministic regular-layout tool. If later presentation work needs arbitrary figure rearrangement, investigate mature Fiji/ImageJ figure tooling such as QuickFigures as an optional handoff instead of reproducing its capabilities.

For plate alignment/peak detection, existing BAR/ImageJ fallbacks remain governed by the current alignment docs; custom composition does not change that decision.