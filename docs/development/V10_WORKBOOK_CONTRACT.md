# V10 workbook contract for workflow-C

V10 is the preferred human-facing metadata source for full experiments. workflow-C should consume V10 into one canonical internal project model and keep V10 terminology wherever practical.

This contract is deliberately scoped to the intended workflow. Do not generalize biological/layout semantics beyond it without a real use case.

See also:

- `FUTURE_WORKFLOW_CONTRACT.md` for the end-to-end user workflow;
- `PROJECT_ASSET_CONTRACT.md` for reusable geometric/project state.

## Core principles

- Read the existing workbook read-only and preserve formulas/VBA; do not convert formats merely for machine convenience unless a test fixture explicitly uses `.xlsx`.
- Prefer resolved machine-readable workbook fields (`*`) where they exist.
- Human-readable cells may intentionally be sparse because the workbook's machine fields expand/fill values for programmatic consumption.
- `Image UID` is canonical image identity.
- `sessionUID*` / normalized `sessionUID` is canonical session identity.
- `Original` and `Working filename` are locators/names, not identity.
- Actual observed files may be raw, working-named or known derivatives; reconcile them to Image UID rather than deriving experiment identity from filenames.
- Machine-specific absolute source paths remain local project state, not workbook metadata.
- Incomplete expected image sets are valid.

## Human-readable versus machine-readable columns

V10 contains user-friendly entry columns and machine-readable mirrored/expanded columns. Machine columns are generally marked with `*`.

The adapter should use the intended machine-readable representation as the row-complete source while preserving human-facing terminology for UI/diagnostics.

### Example: `Set` and `Set*`

A user may enter one human-readable Set value such as `A` once for a logical block. The corresponding machine-readable `Set*` may contain `A` on **every machine row in that block**.

Therefore:

- blank repeated human cells do not automatically mean missing Set metadata;
- code should read the expanded machine value where defined;
- repeated `A` values in `Set*` are not multiple independent human assignments;
- the user should not be required to type `A` repeatedly merely to satisfy the adapter.

Apply the same general principle to other paired human/machine columns where V10 defines them.

## Canonical V10 terminology

Prefer these names externally when the concept matches:

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

Python may use safe snake_case identifiers internally.

## Session and image identity

Each included acquisition/session may restart raw filenames such as `image1.jpg`, `image2.jpg`, etc.

`sessionUID` scopes/disambiguates those repeated raw names. `Image UID` identifies the image record and must remain stable if a physical filename later changes.

`Name` and `Time` are optional disambiguating metadata rather than required identity when the canonical UIDs already distinguish records.

## Media and Condition

`Media` and `Condition` are independently optional. Do not make a flattened `Type` canonical.

Supported states include:

- Media only;
- Condition only;
- both;
- neither where the workbook permits it.

Generate a compatibility display/type key only where legacy code temporarily requires one.

## Expected images versus present files

The workbook describes expected records. The filesystem describes what currently exists.

Reconciliation states should include at least:

- `READY` — one safe physical match;
- `EXPECTED_NOT_PRESENT` — expected but not currently present;
- `AMBIGUOUS` — unsafe/multiple plausible matches;
- `UNMAPPED_FILE` — present physical file with no safe V10 owner.

Missing expected files do not invalidate V10/project setup or block other READY images.

## File matching

Match to Image UID using controlled evidence:

1. saved project provenance;
2. exact `Original` within known session/source context;
3. exact `Working filename`;
4. explicitly supported derivative transformations (known prefixes/extensions);
5. otherwise ambiguous/unmapped.

Case comparisons should be insensitive where semantically appropriate on Windows while preserving original display capitalization.

Do not use arbitrary fuzzy filename matching or strip arbitrary words.

## Optional working-copy renaming

Raw generic source names may remain untouched in `raw/`.

Later project setup may optionally create a parallel `working/` tree using V10 `Working filename` nomenclature. Descriptive renaming is not required for processing because UID remains identity.

If proposed human-readable names collide, use UID-aware project state/collision handling rather than overwriting.

## AnnotationSet/profile model

For current intended semantics, an `annotationSet` supplies the logical labeling/layout definition used by one or more images/experiments.

It may reference:

- **one or more strain profiles**;
- **one current vertical profile**;
- optional `other` label/profile data, currently ignored.

### Vertical profile

Current scope supports one effective vertical profile per annotation layout.

The `Set` column physically present in the vertical-profile table is ignored for current image-processing semantics. It remains in V10 because removing it currently causes workbook issues.

A vertical profile may be reused across multiple annotationSets/experiments.

`Pos` gives physical row order. Repeated `labels_vertical` values remain separate positions.

For current grid derivation:

`GridRows = maximum valid applicable vertical Pos`

so Pos 1..8 yields 8 physical rows.

### Strain profile `Pos`

Within each strain profile:

- numeric `Pos` defines logical strain/column position;
- `labels_strain` supplies display/biological label;
- maximum/extent of valid `Pos` gives that profile's **local column width**;
- do not infer position by sorting label text.

Example: Pos 1..12 means local width 12.

### Multiple strain profiles and `Order`

When more than one strain profile is assigned to an annotationSet, `Order` defines **top-to-bottom profile/band order**:

- `Order=1` -> upper row band;
- `Order=2` -> next/lower row band;
- later orders continue downward.

`Order` is not the same as `Pos` and does not define strain-column order.

Overall `GridCols` is the width of the **widest assigned strain profile**. Do not add widths together when profiles occupy different row bands.

Example:

- profile A Pos 1..10;
- profile B Pos 1..4;
- overall grid width = 10;
- lower/local band width remains 4.

### Default row-band mapping + override

When several ordered strain profiles need physical row bands and no explicit row-band mapping exists, **even contiguous row distribution is the default** when it divides sensibly.

For 8 rows + 2 ordered profiles:

- Order 1 -> rows 1-4;
- Order 2 -> rows 5-8.

However, equal distribution is a default, not an immutable scientific rule. The canonical layout/result must support explicit/manual row-band override later.

If row distribution is not deterministically resolvable, report ambiguity rather than silently invent a scientifically meaningful mapping.

## Required current examples

### 8x12 single profile

- one vertical profile Pos 1..8;
- one strain profile Pos 1..12;
- one band rows 1..8;
- overall grid 8x12.

### 8x10 two strain profiles

- vertical profile Pos 1..8;
- strain profile A Pos 1..10, Order 1;
- strain profile B Pos 1..10, Order 2;
- default row bands 1..4 / 5..8;
- overall grid 8x10.

### Unequal-width synthetic case

- upper strain profile width 10;
- lower strain profile width 4;
- overall grid columns 10;
- lower band retains local width 4.

This case should be tested even if not represented by the current fixture because it proves the intended widest-profile semantics.

## Four-click/grid integration

The current four-click grid route is already working and should not be redesigned merely for V10.

V10-aware grid registration should receive logical row/column/band information from the canonical `PlateLayout` and persist the accepted measured grid/spot coordinates as a reusable project asset.

Do not assume every row band necessarily has the same local final occupied column. If a future lower band is narrower, logical metadata must retain that fact.

Do not bake a specific four-click reference-row choice into the V10 adapter itself; the production alignment layer may select practical reference rows using the known layout.

## Reusable measured grid coordinates

After alignment accepts a grid, preserve coordinates/transform independently of crop export. Later operations should reuse them for:

- unprocessed culture crops;
- processed culture crops after visibility processing;
- overall-grid ROI statistics;
- automatic strain/vertical annotation placement;
- QC overlays;
- selected-strain/matrix resolution.

See `PROJECT_ASSET_CONTRACT.md`.

## Other labels

`other` labels remain out of current scope.

## Compatibility projections

Legacy CSV-shaped handoffs may be generated from the canonical V10 model where existing Fiji/Pillow components still need them. They are compatibility projections, not parallel metadata authorities.

The user should not maintain them manually when running through V10.

The active implementation snapshots `v10_master_registry.csv` and lossless `v10_plate_layout.csv` on setup, together with compatible `images.csv` and `condition_order.csv`. It emits the five-column legacy `grid.csv` only when all row bands share the same column labels; otherwise emitting it would silently discard V10 label meaning. Snapshots are immutable and may be pinned, compared, or explicitly regenerated from the linked workbook.

## Provenance

Keep local provenance keyed by Image UID, including accepted source/working/processed/annotated paths and stage states. Once a derived file is registered, provenance outranks future filename guessing.

Provenance remains image-blind: model-facing state may store paths, checksums, dimensions, coordinates and text/numeric metadata, but not image previews/pixels.

## Validation posture

Surface concise actionable metadata errors rather than silently infer ambiguous biological/layout semantics. Distinguish malformed/ambiguous metadata from merely missing physical files.

## Basic CSV compatibility boundary

The currently working basic CSV route intentionally remains a simpler baseline. Do **not** retrofit V10 `Set`/annotationSet/profile-order semantics into that route just to make the inputs structurally identical.

V10 is the richer metadata adapter feeding shared downstream image-processing/state contracts.
