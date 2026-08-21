# CSV semantic validation

`tools/validate_project_csvs.py` checks the three existing CSV contracts before processing rather than introducing a new data format.

Checks include:
- required headers;
- exact header names with no surrounding whitespace, matching the reused Pillow `csv.DictReader` scripts rather than silently normalizing a format those scripts would later reject;
- duplicate headers that collapse to the same name after trimming are rejected with a targeted error;
- consistent `GridCols` within each Experiment/Set;
- exactly columns `1..GridCols` with no duplicates;
- non-empty strain names;
- unique condition order/type entries;
- **case-insensitive uniqueness of Experiment/Set identities** and condition `Type` names, because the reused Pillow scripts lowercase crop prefixes before matching;
- uniqueness of every flattened legacy `Experiment_Set_Type` lookup prefix across the Cartesian grid-key × condition set. Underscores remain allowed in metadata; only combinations that become indistinguishable after underscore-delimited flattening are rejected;
- unique source filenames;
- source filenames with no surrounding whitespace, because the reused Fiji batch macro matches the raw CSV filename field before later trimming/metadata handling;
- every `images.csv` Experiment/Set exists in `grid.csv`;
- every image `Type` exists in `condition_order.csv`;
- comma-bearing `Experiment`, `Set`, `Type` and `Strain` values that the reused ImageJ macros cannot safely parse with simple comma splitting;
- embedded line breaks in those ImageJ line-parsed metadata fields;
- semicolons in `Experiment`, `Set` or `Type`, because the composed Fiji helpers use semicolon-delimited `runMacro` arguments;
- Windows filename-unsafe characters (`/ \\ : * ? " < > |`) in `Experiment`, `Set` or `Type`, because those values are inserted directly into crop filenames without sanitizing.

The case/flattening checks are intentionally targeted to the established scripts rather than imposing a generic naming convention. For example, `EXP_1 / SET_A / YPDA_CONTROL` remains valid when it is unambiguous. A combination such as `E1 / A_B / YPDA` alongside `E1_A / B / YPDA` is rejected because both legacy lookups flatten to the same lower-case prefix even though the structured metadata tuples are different.

`Strain` is different: the established Fiji crop exporter already sanitizes filename-unsafe strain characters through `safeName()`, so the validator does not unnecessarily prohibit them there.

Comma-containing source filenames remain supported. The existing production ImageJ macro already has explicit handling for quoted filenames containing commas, so the validator deliberately does not reject that case; only unsafe surrounding whitespace is blocked.

The controller **Validate CSVs** button uses this validator, and both batch routes run it automatically before Fiji starts. The synthetic fixtures are kept semantically valid so they can serve as a known-good example.
