# Gemini prototype integration status

The reviewed prototype cores are integrated on `workflow-integrated` under `tools/applets/`. The original prototype branches remain provenance; runtime code no longer imports from documentation directories.

Integrated cores:

- V10 workbook adapter
- project setup and non-destructive working-copy rename
- plate layout derivation
- whole-plate orientation
- plate crop preprocessing
- visibility adjustment and review queue
- annotation and matrix composition

`tools/applets/registry.py` is the controller-facing catalog. Applets remain independently callable and communicate through the schemas under `contracts/`. This checkpoint does not claim that every applet has an interactive GUI button yet.

The production anchor remains the four-point Fiji route. Its accepted grid coordinates are the prerequisite asset for visibility and annotation. Persisting that grid as a durable project asset is the next integration boundary; applets must not recalculate or force the user to click it again.

Runtime baseline: Windows, Miniforge/Conda environment `workflow-c`, Python 3.11. Pillow, NumPy, pandas and openpyxl are declared in `environment.yml`.
