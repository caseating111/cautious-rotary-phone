# CSV semantic validation

`tools/validate_project_csvs.py` checks the three existing CSV contracts before processing rather than introducing a new data format.

Checks include:
- required headers;
- consistent `GridCols` within each Experiment/Set;
- exactly columns `1..GridCols` with no duplicates;
- non-empty strain names;
- unique condition order/type entries;
- unique source filenames;
- every `images.csv` Experiment/Set exists in `grid.csv`;
- every image `Type` exists in `condition_order.csv`.

The controller **Validate CSVs** button uses this validator, and the full-column batch launcher runs it automatically before Fiji starts. The synthetic fixtures are kept semantically valid so they can serve as a known-good example.