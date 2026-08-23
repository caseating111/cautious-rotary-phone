# CSV semantic validation

tools/validate_project_csvs.py validates grid.csv, images.csv, and condition_order.csv before Fiji or Pillow runs.

It checks exact unique headers, rejects unheaded extra fields, validates GridCols/Column completeness, Experiment/Set and condition identities, flattened crop-prefix ambiguity, ImageJ delimiter hazards, macro semicolons, filename-unsafe Experiment/Set/Type, and Filename whitespace.

Windows identities are case-insensitive. Source filenames differing only by case are duplicates. Strain values pass through the exporter sanitizer and are rejected when the result is empty, dot/dot-dot, trailing-dot/space, a reserved DOS device name, or collides with another sanitized Strain folder.

Comma-containing source filenames remain supported because current Fiji handoff is tab-separated folder plus filename. Metadata fields consumed by the retained comma parser may not contain commas or line breaks.

Reconciliation/finalization use the same Windows identity while preserving disk spelling. Adoption remains explicit and validated.
