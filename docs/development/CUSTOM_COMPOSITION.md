# Unified matrix and labelled-crop composition

The active composition endpoint is **Build matrices and labelled crops** in the controller. It launches `tools/custom_matrix_gui_recorded.py`; `tools/unified_matrix_export.py` is the recorded orchestration core. The old controller Pillow dropdown, separate preferred-WT applet, direct `custom_matrix_selection.py` CLI, and unrecorded GUI entrypoint are retired user routes. Their mature renderer/helper internals remain available to the unified orchestrator.

One run can build any checked combination of:

- per-experiment matrices;
- all selected strains across experiments;
- all selected strains with duplicate WT X/WT Y controls removed;
- individually labelled crops.

Experiment/Set strain columns, conditions, and Top/Low are independent selectors. Top and Low checked together create separate state outputs in the same numbered run; either can be selected alone. Only metadata and exact current crops in the chosen subset/state are staged and required. The applet retains All, None, Only this set, availability checking, optional per-experiment preview, legacy-recipe import, and last-selection restore.

Preferred WT source and case-insensitive WT matching live in this applet. **Normalize WT separators** additionally treats spaces, hyphens, and underscores as equivalent; it defaults on to preserve established hyphen behavior. Presets store the complete request beside dataset metadata at `Metadata/_workflow/matrix-presets`.

Published files never use timestamp subfolders and never overwrite earlier runs:

```text
Matrices/
  !All Matrix Exports/
  1. All Strain Matrices/
  2. All Strain Matrices -- No WT Dupe/
  3. Per Experiment Matrices/
  4. Individual Labelled Crops/<Experiment>/<Strain>/
```

Every matrix is copied to its category and `!All Matrix Exports`; labelled crops are excluded from the aggregate. One global `RunNNN` identifies every file from the action. All-strain names include export date and matrix type. Deduplicated names list retained WT Experiment/Set/name provenance in experiment order, with numeric Sets before lettered Sets. Processing details append to `Processing Logs/Unified Matrix Exports.log`, with a machine recipe in `_workflow/output-recipes`.

Every run filters authoritative CSVs into a temporary workspace, selects exact current crop filenames, checks source freshness, normalizes only disposable staged copies, runs the established Pillow renderers, verifies results, and transactionally publishes only after all checked renderers succeed. Source images, crops, and CSVs are not changed.
