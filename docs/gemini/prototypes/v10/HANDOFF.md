# V10 adapter prototype handoff

Status: INTEGRATED

Integrated on `workflow-integrated` at `246efcb`. The read-only adapter, canonical V10 terminology validation, diagnostics, embedded layouts, canonical multi-profile/Order mapping, and explicit legacy sanitized-fixture compatibility are covered by targeted tests.

## Goal

Build an isolated, read-only V10 workbook adapter that converts the sanitized synthetic V10 workbook into the shared canonical project model without touching the current Fiji/AHK/controller runtime. The adapter should absorb workbook-specific structure and naming so downstream components do not need to understand worksheet quirks, mirrored human/machine columns, formulas, or Excel-specific layout.

Primary interface:

`load_v10(path) -> ProjectModel`

The first useful proof is metadata parsing and normalization only. Do not integrate with Fiji, image processing, controller state, or live file discovery during this prototype.

## Source and privacy constraints

- Use only the sanitized synthetic V10 fixture committed under `fixtures/v10/` and synthetic/generated test data.
- Treat the workbook as read-only. Never write back into the fixture as part of normal adapter operation.
- Do not inspect real experimental images or depend on pixel data.
- Do not introduce absolute machine paths, personal metadata, or local-environment assumptions into committed outputs/tests.

## Human-readable versus machine-readable workbook columns

V10 deliberately contains human-facing entry columns and machine-readable mirrored/expanded columns. In general, machine-readable columns are marked with `*` while human-readable columns are not.

The adapter must prefer the machine-readable representation when it is the canonical expanded form, while preserving enough provenance/diagnostics to explain the corresponding human entry.

Example semantic pattern:

- a human-facing `Set` entry may contain one value such as `A` for a logical block/experiment assignment;
- the machine-facing `Set*` representation may repeat/expand `A` across every relevant row so downstream code has an explicit value per record;
- the fact that the human only typed `A` once must not be interpreted as the other corresponding rows having missing Set values.

Do not infer missing machine-readable values from display formatting when the workbook already provides a machine-readable mirrored column. Conversely, do not treat a repeated `Set*` value as multiple independent human assignments.

This same principle applies wherever V10 uses paired human/machine columns: human entry is optimized for usability; starred columns are optimized for deterministic programmatic consumption.

## Canonical identity semantics

- `Image UID` is the stable image identity.
- `sessionUID` is the stable image-session identity for a run/session grouping.
- `Original` is the original source filename/name recorded for the image, not identity.
- `Working filename` is the intended human-facing/processed working filename, not identity.
- A later physical filename may gain prefixes/suffixes or a different extension without changing `Image UID`.
- Experiment/date/session metadata must remain separate from physical filename identity.
- `Media` and `Condition` are independently optional and must not be collapsed into one field.
- Preserve V10 terminology where practical so workbook-to-model diagnostics remain understandable.

The normalized model should be capable of later reconciling both raw filenames such as `image1.jpg` and processed variants such as `PROCESSED <working filename>.tiff` back to the same image identity, but actual live filesystem matching is out of scope for this prototype.

## Required workbook concepts to parse

At minimum, normalize the fields/concepts needed for the intended workflow:

- experiment (`Exp` / machine-readable equivalent);
- date;
- time where present;
- experiment/session/name fields needed to distinguish records;
- `sessionUID`;
- `Image #`;
- `Image UID`;
- `Original`;
- `Working filename`;
- `Set` / `Set*` where semantically relevant to images/experiments;
- `Media`;
- `Condition`;
- replicate (`Rep #`);
- arrangement/layout reference where present;
- assigned `annotationSet`;
- annotation-set assignments;
- strain profiles and strain labels;
- vertical profiles and vertical labels;
- `Pos` ordering within profiles;
- assignment `Order` for multiple strain profiles.

`other` annotation labels are explicitly out of scope for the current prototype.

## Meaning of `Pos`, `Order`, profiles and annotation sets

`Pos` and `Order` are not interchangeable.

- `Pos` is the logical within-profile position. For a strain profile, positions 1..12 mean strain/column positions 1..12. For a vertical profile, positions 1..8 mean physical row positions 1..8. Display labels may repeat; position remains distinct.
- `Order` applies when more than one strain profile is assigned to the same annotation set. It determines the top-to-bottom band order of those profiles: `Order=1` is the upper band, `Order=2` the next band, etc.
- An `annotationSet` groups the strain-profile assignment(s), one current vertical-profile assignment, and future/ignored other-label assignments for use by one or more experiments/images.
- A profile may be reusable across multiple annotation sets/experiments; reuse does not create a new profile identity merely because the experiment changes.

## Annotation assignment semantics

The workbook currently supports annotation-set assignments such as:

- annotation set -> strain profile(s), each with an `Order`;
- annotation set -> one vertical profile;
- annotation set -> optional other profile(s), currently ignored.

One strain profile may span the full physical plate. Multiple strain profiles in one annotation set represent ordered top-to-bottom physical row bands.

For the current workflow, support **one vertical profile per annotation set/use case**. The workbook may retain a `Set` column in vertical-profile tables because removing it currently causes workbook glitches, but the adapter must **ignore vertical-profile `Set` values for current semantics**. A vertical profile can be reused across multiple experiments/annotation sets.

## Grid-size information derivable from workbook metadata

The adapter does not itself need to finalize `PlateLayout`, but it must preserve the information required for deterministic derivation:

- total row count comes from vertical-profile physical `Pos` positions, not from the number of unique vertical label strings;
- each strain profile's highest/extent of valid `Pos` values defines that profile's logical width;
- the widest assigned strain profile defines the overall logical grid column count;
- widths of multiple strain profiles are **not added together** when those profiles occupy different row bands;
- each strain band's local width must remain available even if the overall grid is wider.

Example: an 8-position vertical profile plus two ordered strain profiles each with positions 1..10 yields an 8x10 overall layout source, not 8x20.

## Multi-strain-profile row mapping

For the currently required 8-row/two-profile case:

- `Order=1` is the upper strain band;
- `Order=2` is the lower strain band;
- default downstream mapping is an even split: rows 1-4 and rows 5-8.

Even distribution should be the default when multiple ordered strain profiles need row bands and the total row count divides cleanly. However, that is a default mapping policy, not an immutable scientific truth. The normalized model/layout contract should permit an explicit/manual row-band override later rather than forcing equal division forever.

If the row count cannot be evenly divided, or explicit assignment metadata later exists, do not silently invent a mapping. Preserve enough information for the layout layer to surface/resolve it.

## Basic CSV mode is intentionally simpler

The currently working basic CSV/Fiji workflow does not implement the richer V10 `Set`/annotation-set/profile-order semantics. That is intentional and should not be treated as a defect.

Do not retrofit V10 semantics into the basic CSV mode as part of this prototype. V10 integration is the structured path that will later provide those semantics to downstream components.

## Incomplete datasets are valid

Workbook metadata may describe more expected images than are physically present later. This is not an adapter error.

The V10 model should represent expected image records independently of physical availability. Missing physical files must not make workbook parsing invalid. Later runtime reconciliation can classify images as present/missing/ambiguous.

Do not make the adapter require a complete image directory or complete set of raw files.

## Filename behavior the model must enable later

The model should retain sufficient canonical names/identities for later reconciliation logic to support:

- original raw names such as `image1`, `image2`, etc.;
- working filenames generated/recorded in V10;
- processed variants with additional prefixes such as `PROCESSED `;
- changed extensions (`.jpg`, `.jpeg`, `.tif`, `.tiff`, etc.);
- Windows-legal punctuation including spaces, commas, `%`, and similar characters;
- semantically case-insensitive comparison where appropriate while preserving original capitalization for display.

Do not solve this by reparsing human-readable filenames into identity when `Image UID`/structured metadata already provide identity.

## Required synthetic proof cases

### 14.08.26
- experiment 1;
- annotation set 1;
- one strain profile;
- 12 strain positions/columns;
- one vertical profile;
- 8 physical rows;
- expected layout source equivalent to 8 x 12.

### 15.08.26
- experiment 1;
- annotation set 1 reused;
- one strain profile with 12 positions;
- one vertical profile with 8 row positions;
- supports multiple images/sessions without assuming the complete physical image set is present.

### 16.08.26
- experiment 2;
- annotation set containing two strain profiles;
- each strain profile has positions 1-10;
- assignment `Order` determines top/bottom order;
- default downstream physical interpretation is top 4 rows for order 1 and bottom 4 rows for order 2 when the vertical profile has 8 total rows;
- overall column count remains 10;
- row-band override must remain possible later.

## Validation and failure behavior

Prefer explicit validation/reporting over silent guesses. Surface clearly:

- duplicate `Image UID` where uniqueness is required;
- assignment references to missing profiles;
- duplicate/non-sensical `Pos` entries within one profile;
- multiple vertical-profile assignments where current semantics permit only one;
- ambiguous/missing `Order` for multiple strain profiles;
- malformed required identifiers;
- disagreement between authoritative machine-readable and human-facing values where that disagreement cannot be resolved deterministically.

Do not reject harmless unused workbook columns merely because the adapter does not consume them.

## Shared-contract expectations

Use the versioned schemas under `contracts/` as the cross-component boundary. Keep workbook-specific structures inside the adapter.

The downstream layout/annotation/project-setup components should be able to consume the normalized model without reopening the workbook.

If the current contract is insufficient, propose the smallest explicit change in this HANDOFF rather than silently inventing incompatible fields.

## Implementation posture

- Prefer mature Excel-reading libraries suitable for `.xlsx` parsing; avoid Excel automation unless required by evidence.
- Keep parsing deterministic and testable without desktop Excel.
- Avoid broad abstraction layers or a generic spreadsheet framework.
- A small adapter plus canonical model is the goal.
- Use targeted synthetic tests rather than broad application regression tests.

## Out of scope for this prototype

- current CSV/Fiji/AHK workflow integration;
- image pixels or image processing;
- physical file scanning/reconciliation implementation;
- controller GUI changes;
- annotation rendering;
- plate/grid pixel alignment;
- `other` labels;
- multiple vertical-profile-set behavior beyond reporting unsupported/ambiguous input.

## Success criteria

The prototype is `Proven` when:

1. the sanitized synthetic V10 workbook loads read-only;
2. it produces a deterministic `ProjectModel`/normalized representation;
3. human versus machine-readable column semantics are handled correctly, including expanded `Set*`-style values;
4. identity and filename fields remain distinct;
5. the 14.08.26, 15.08.26 and 16.08.26 synthetic cases are represented correctly;
6. `Pos`, `Order`, profile reuse and annotation-set assignments retain their intended meanings;
7. incomplete expected image sets remain valid metadata;
8. targeted synthetic tests pass;
9. a concise JSON/text dump demonstrates normalized records/layout-source information without exposing private data.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface: `load_v10(path) -> ProjectModel`
- Tests:
- Dependencies:
- Proven workbook/cases:
- Canonical model fields produced:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
