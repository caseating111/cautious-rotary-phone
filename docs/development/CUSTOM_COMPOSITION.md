# Custom composition

Current focused composition recomposes existing validated crops without rerunning Fiji or changing authoritative CSVs. It supports Experiment/Set groups, columns/strains, conditions, Top/Low, last-successful selection, representative preview, processing logs, and recipes.

Only Raw display mode is current. Presentation-normalized mode depended on absent full-column display-range macros and is incompatible with current four-point state. It is removed from the GUI; old presentation recipes and runners fail explicitly and direct the user to Raw.

Use tools/custom_matrix_gui_recorded.py from the controller or start_custom_matrix.cmd. tools/run_custom_matrix_job.py is the current recorded core route. The old direct custom_matrix_selection.py CLI and unrecorded custom_matrix_gui.py entrypoint are retired, while their callable internals remain reused.

Every build uses filtered temporary CSVs, exact current crop staging, freshness validation, staged orientation normalization, the established Pillow renderer, and expected-output verification. Deduplicated all-strains requires explicit WT Experiment/Set selection through dedup_control_gui.py.
