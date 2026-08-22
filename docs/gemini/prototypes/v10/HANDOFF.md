# V10 adapter prototype handoff

Status: Planned

## Goal

Build an isolated, read-only V10 workbook adapter that converts the synthetic V10 workbook into the shared canonical project model without touching the current Fiji/AHK/controller runtime. The adapter should absorb workbook-specific structure and naming so downstream components do not need to understand worksheet quirks, mirrored human/machine columns, formulas, or Excel-specific layout.

Primary interface:

`load_v10(path) -> ProjectModel`

The first useful proof is metadata parsing and normalization only. Do not integrate with Fiji, image processing, controller state, or live file discovery during this prototype.

## Source and privacy constraints

- Use only the sanitized synthetic V10 fixture committed under `fixtures/v10/` and synthetic/generated test data.
- Treat the workbook as read-only. Never write back into the fixture as part of normal adapter operation.
- Do not inspect real experimental images or depend on pixel data.
- Do not introduce absolute machine paths, personal metadata, or local-environment assumptions into committed outputs/tests.

## Canonical identity semantics

These semantics are important and should not be inferred differently downstream:

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

At minimum, normalize the fields/concepts needed for the current intended workflow:

- experiment (`Exp`);
- date;
- time where present;
- experiment/session/name fields needed to distinguish records;
- `sessionUID`;
- `Image #`;
- `Image UID`;
- `Original`;
- `Working filename`;
- `Set` where it is semantically relevant to images/experiments;
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

## Annotation assignment semantics

The workbook currently supports annotation-set assignments such as:

- annotation set -> strain profile(s), each with an `Order`;
- annotation set -> one vertical profile;
- annotation set -> optional other profile(s), currently ignored.

One strain profile may span the full physical plate. Multiple strain profiles in one annotation set represent ordered top-to-bottom physical row bands. `Order=1` is the upper band, `Order=2` the next band, etc.

The adapter should preserve enough normalized information for the layout prototype to derive those bands; it does not need to decide actual pixel coordinates.

For the current workflow, support **one vertical profile per annotation set/use case**. The workbook may retain a `Set` column in vertical-profile tables because removing it currently causes workbook issues, but the adapter must **ignore vertical-profile `Set` values for current semantics**. A vertical profile can be reused across multiple experiments/annotation sets.

## Incomplete datasets are valid

Workbook metadata may describe more expected images than are physically present later. This is not an adapter error.

The V10 model should therefore represent expected image records independently of physical availability. Missing physical files must not make workbook parsing invalid. Later runtime reconciliation can classify images as present/missing/ambiguous.

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

The adapter should prove the currently discussed synthetic V10 cases, including:

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
- intended downstream physical interpretation is top 4 rows for order 1 and bottom 4 rows for order 2 when the vertical profile has 8 total rows;
- overall column count remains 10.

The adapter should expose normalized profile assignments; the separate layout derivation component is responsible for converting these into explicit row bands/grid dimensions.

## Validation and failure behavior

Prefer explicit validation/reporting over silent guesses. Examples of conditions that should be surfaced clearly:

- duplicate `Image UID` where uniqueness is required;
- assignment references to missing profiles;
- duplicate/non-sensical `Pos` entries within one profile;
- multiple vertical-profile assignments where current semantics permit only one;
- ambiguous/missing `Order` for multiple strain profiles;
- malformed required identifiers.

Do not reject harmless unused workbook columns merely because the adapter does not consume them.

## Shared-contract expectations

Use the versioned schemas under `contracts/` as the cross-component boundary. Keep workbook-specific structures inside the adapter.

The downstream layout/annotation components should be able to consume the normalized model without opening the workbook.

If the current contract is insufficient, propose the smallest explicit change in this HANDOFF rather than silently inventing incompatible fields.

## Implementation posture

- Prefer mature Excel-reading libraries already suitable for `.xlsx` parsing; avoid Excel automation unless required by evidence.
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
3. identity and filename fields remain distinct as specified above;
4. the 14.08.26, 15.08.26 and 16.08.26 synthetic cases are represented correctly;
5. multiple ordered strain profiles and a single reusable vertical profile are represented without Fiji/controller dependencies;
6. incomplete expected image sets remain valid metadata;
7. targeted synthetic tests pass;
8. a concise JSON/text dump demonstrates the normalized records/layout-source information without exposing private data.

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
