# V10 workbook contract for workflow-C

V10 is the preferred human-facing metadata source for full experiments. workflow-C should consume V10 metadata into one canonical internal project model and keep V10 terminology wherever practical.

This document describes the intended current contract. It is deliberately scoped to the features needed for the current workflow and the next annotation stages. Do not generalize beyond this contract unless a real use case requires it.

## Core principles

- Read the existing `.xlsm` directly and preserve VBA/formulas; do not convert it to `.xlsx` merely for machine convenience.
- Prefer resolved machine-readable workbook fields (`*`) where they exist. Sparse human-entry cells may intentionally rely on workbook fill-down/inheritance logic.
- `Image UID` is the canonical image identity.
- `sessionUID*` is the canonical acquisition/session identity.
- `Original` is the camera/source basename for that session (for example `image1.jpg`). It is a locator, not the canonical identity.
- `Working filename` is the workbook's intended readable filename. It is also a locator/reference, not the canonical identity.
- Actual observed files may be raw, working-named, or known derivatives with different prefixes/extensions. workflow-C should reconcile them to the V10 `Image UID` instead of deriving experiment identity from filenames.
- Full machine-specific source paths remain local workflow-C state rather than workbook metadata.
- The image-blind privacy contract applies to all workbook-driven filesystem reconciliation and testing.

## Canonical V10 terminology

Prefer these names in workflow-C UI/docs/adapters when the concept is the same:

- `Exp`
- `Date`
- `Time`
- `Name`
- `Arrangement`
- `annotationSet`
- `Replicate label`
- `Description text`
- `Image #`
- `Sample description`
- `Set`
- `Media`
- `Condition`
- `Rep #`
- `Original`
- `Image UID`
- `Working filename`
- `sessionUID`
- `Strain profile`
- `Vertical profile`
- `labels_strain`
- `labels_vertical`
- `Pos`
- `Order`

Python identifiers may use safe snake_case equivalents, but external terminology should remain consistent with V10 where practical.

## Session semantics

Each included Overview row represents one acquisition/session. `Image #` restarts at 1 for each session, matching acquisition software that restarts raw names such as `image1.jpg`, `image2.jpg`, etc.

`sessionUID*` disambiguates otherwise-repeated raw filenames across sessions. `Image UID` combines session identity with image number and should remain stable even if the physical filename later changes.

`Name` and `Time` are optional disambiguators. They should not be required when the resulting session identity/filenames are already unique.

## Media and Condition

`Media` and `Condition` are separate optional metadata components. Do not require both.

Supported examples include:

- Media only: `Media=YPDA`, blank Condition.
- Condition only: blank Media, `Condition=sugar`.
- Both: `Media=YPDA`, `Condition=salt`.

Do not make a flattened `Type` field canonical. If an existing processing handoff temporarily requires one field, generate a compatibility key from the separate V10 values.

## Expected images versus files currently present

The Master Registry describes the expected image records. The filesystem describes what currently exists. An incomplete acquisition is a normal state, not an error by itself.

Reconciliation states should include at least:

- `READY`: an expected image has one accepted physical-file match.
- `EXPECTED_NOT_PRESENT`: expected by V10 but no matching file is currently present.
- `AMBIGUOUS`: more than one plausible file maps to one expected image, or the mapping is otherwise unsafe.
- `UNMAPPED_FILE`: a physical file is present but no V10 record safely claims it.

Preflight should summarize these states and allow processing of `READY` images after confirmation even when other expected images are absent.

## File matching

Match physical files to `Image UID` using controlled evidence, not arbitrary fuzzy matching. Preferred evidence order:

1. existing workflow-C provenance mapping;
2. exact `Original` within the connected session folder;
3. exact `Working filename`;
4. a controlled derivative of `Working filename` using explicitly supported transformations such as known prefixes and extension changes;
5. otherwise mark ambiguous/unmapped and request confirmation.

Examples of controlled derivative matching may include a known `PROCESSED ` or `ANNOTATED ` prefix and a change from `.jpg` to `.tif`/`.tiff`, provided the remaining normalized name maps uniquely.

Do not delete arbitrary words or use broad similarity matching. If two candidates normalize to the same expected record, do not guess.

Legal Windows filename characters such as commas and `%` should not be prohibited solely because a fragile parser dislikes them. Fix transport/parsing instead: use structured CSV handling, safe Python path objects, `subprocess` argument lists with `shell=False`, or internal transport aliases where an external tool requires them.

## Local session-folder mapping

workflow-C should maintain a local mapping from `sessionUID` to the source/acquisition folder. Do not write absolute local source paths into V10 by default.

Example:

```text
E1_14.08.26_24h -> D:\Acquisitions\14.08.26_24h
E1_15.08.26_48h -> D:\Acquisitions\15.08.26_48h
```

Within each connected session folder, `Original` can resolve repeated camera names safely because the `sessionUID` scopes them.

## Annotation-derived physical grid

For the current supported scope, the workbook does not need a separate grid table. Derive the physical grid from annotation metadata.

### Vertical profile scope

Current scope supports one assigned vertical profile per annotationSet for grid derivation. Multiple vertical-profile blocks are deferred until there is a real need.

A vertical profile may be reused by different experiments/annotation sets.

**Ignore the `Set` column inside the vertical-profile table.** It remains present because removing it currently disrupts workbook behavior, but workflow-C must not use it to filter, partition, or otherwise interpret vertical labels. Treat the selected vertical profile's ordered nonblank `labels_vertical` / `Pos` records as one reusable physical row sequence.

For the currently supported shape:

```text
GridRows = maximum applicable vertical Pos
```

The current sample profile is eight rows (`Pos` 1-8), so it defines an 8-row physical grid wherever that vertical profile is assigned.

### Strain profiles and strain label bands

One assigned strain profile may contain one or more `Set` blocks in the strain-label table. In the current workbook these strain-table `Set` values are **label-band grouping markers**, not filters against the Master Registry image `Set`.

Therefore:

- do not choose strain labels by comparing the image's Master Registry `Set` to the strain-profile table `Set`;
- within the assigned strain profile, each distinct populated strain-table `Set` block defines one ordered strain-label band;
- strain-table blocks are interpreted top-to-bottom in their workbook order for the current scope;
- within each block, `Pos` defines logical columns and `labels_strain` supplies the labels;
- `GridCols` is the maximum `Pos` across all strain-label bands in the assigned strain profile.

If the assigned strain profile has one strain-label band, that band spans the full physical row range.

If it has multiple strain-label bands and the number of physical rows divides evenly by the number of bands, allocate equal contiguous row bands from top to bottom. For the current 8-row, two-band case:

```text
band 1 -> rows 1-4
band 2 -> rows 5-8
```

If row allocation is not deterministic, flag metadata validation instead of guessing.

The widest strain-label band defines the overall physical grid width. A shorter lower band does not shrink the global grid; it means that row band has fewer occupied logical columns.

Current intended examples:

```text
annotationSet 1 -> Strain 1
Strain 1 band A -> strain1 ... strain12, Pos 1-12
Vertical 1 -> Pos 1-8
=> 8 x 12 grid, one strain-label band spanning all rows
```

```text
annotationSet 2 -> Strain 2
Strain 2 band A -> exp2_strain1 ... exp2_strain10, Pos 1-10
Strain 2 band B -> exp2_culture1 ... exp2_culture10, Pos 1-10
Vertical 1 -> Pos 1-8
=> 8 x 10 grid, band A rows 1-4, band B rows 5-8
```

### Four-click geometry implication

The eventual V10-aware four-click alignment should carry the true logical row/column coordinate for every click rather than assuming both reference rows share the same last column.

For the common one-band 8-row layout, the reference rows remain row 1 and row 5 (`ceil(GridRows / 2) + 1` for the current even-row cases), using the first and last occupied columns on each reference row.

For a two-band 8 x 10 layout whose two bands both contain ten columns, the four reference clicks are naturally:

```text
R1C1
R1C10
R5C1
R5C10
```

If a lower band is shorter, use its true last occupied logical column rather than pretending it spans the full grid width.

The geometry solver should use known row/column intervals to estimate per-column and per-row vectors.

## Other labels

`other` annotation labels are out of current scope and should be ignored for now. Do not spend implementation effort on them until requested.

## Compatibility projections

The current processing code may temporarily need generated CSV-shaped handoffs. These are implementation projections from the canonical V10-derived model, not parallel metadata authorities.

Where current code still expects fields such as `Filename`, `Experiment`, `Type`, `GridCols`, `Column` or `Strain`, generate them from the canonical model as needed while gradually adopting V10 naming in new code.

The user should not normally need to maintain those generated handoff files manually when using V10.

## Provenance

workflow-C should keep local provenance keyed by `Image UID`, including accepted observed source path/name and derived output paths/stages. Once a derived file has been registered, provenance should outrank future filename guessing.

Provenance must remain image-blind: model-facing records may contain paths, names, checksums, counts, dimensions, stage/status and other non-pixel metadata, but never image content/previews.

## Validation posture

Validate the workbook/model before processing and surface concise actionable issues. Do not silently infer ambiguous biological/layout semantics. Missing physical image files are allowed; malformed/ambiguous metadata should be reported separately from simply not-yet-present acquisitions.
