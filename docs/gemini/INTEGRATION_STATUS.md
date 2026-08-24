# Gemini prototype integration status

The reviewed prototype cores are integrated on `workflow-integrated` under `tools/applets/`. The original prototype branches remain provenance; runtime code no longer imports from documentation directories.

Integrated product components:

- V10 workbook adapter and PlateLayout derivation (integrated and validated at `246efcb`)
- project setup and non-destructive working-copy rename
- plate layout derivation
- whole-plate orientation
- plate crop preprocessing
- visibility adjustment and review queue
- annotation and matrix composition
- durable `GridCoordinateAsset` row/column/`rNcM` spot geometry
- later unprocessed/processed culture export from saved grids
- mixed Top/Low matrix composition
- optional four-point register-only mode

`tools/applets/registry.py` is the controller-facing catalog. The applet cores remain independently callable, communicate through schemas under `contracts/`, and are exposed through **Open V10 project applets**. `WorkflowProjectState` persists accepted results, derivative provenance, crop exports, matrix exports, and staleness-relevant grid identities.

The production anchor remains the four-point Fiji route. Batch, single, and rerun persist `GridCoordinateAsset` v1 after successful crop export. The additive register-only option uses the same accepted placement/QC route and persists the grid without creating or changing crop output. Later visibility, annotation, culture export, and mixed-tier matrix actions reuse recorded assets rather than forcing alignment again.

Integration checkpoints: V10/layout `246efcb`; durable grid `8fabf35`; stateful project applets `c31d4f1`; later culture export `9d3205d`; mixed-tier matrix `fdac0df`; register-only `cfdd806`.

Runtime baseline: Windows, Miniforge/Conda environment `workflow-c`, Python 3.11. Pillow, NumPy, pandas and openpyxl are declared in `environment.yml`.
