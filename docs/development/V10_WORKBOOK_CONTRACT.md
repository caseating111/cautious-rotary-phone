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

Current scope supports one assigned/resolved vertical profile per annotationSet for grid derivation. Multiple vertical-profile blocks are deferred until there is a real need.

A vertical profile may be reused by different experiments/annotation sets.

The resolved vertical `Pos` sequence defines physical grid rows. For the currently supported shape:

```text
GridRows = maximum resolved vertical Pos
```

### Strain profiles

One or more strain profiles may be assigned to one annotationSet.

For the current image/Set, resolve the applicable strain-label rows and use:

```text
GridCols = maximum resolved strain Pos across assigned strain profiles
```

If one strain profile is assigned, it spans the full physical row range.

If multiple strain profiles are assigned, `Order` defines their top-to-bottom ordering. Infer their physical row bands only when the vertical-label sequence provides a clear deterministic repeated-block structure. If the band assignment is ambiguous, flag metadata validation instead of guessing.

The widest strain profile defines the overall physical grid width. A shorter lower profile does not shrink the global grid; it means that row band has fewer occupied logical columns.

### Four-click geometry implication

The eventual V10-aware four-click alignment should carry the true logical row/column coordinate for every click rather than assuming both reference rows share the same last column.

Example:

```text
rows 1-3: 10-column strain profile
rows 4-6: 4-column strain profile

reference clicks:
R1C1
R1C10
R4C1
R4C4
```

The geometry solver should use known row/column intervals to estimate per-column and per-row vectors. `R4C4` is not the right edge of a 10-column grid; it is logical column 4 on the lower reference row.

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
