# Grid/layout derivation prototype handoff

Status: Planned

## Goal

Derive a deterministic `PlateLayout` from normalized project/annotation metadata without depending on Fiji, image pixels, or the current controller. This component translates annotation profile structure (`Pos`, vertical labels, strain-profile `Order`) into logical grid dimensions and row bands that downstream alignment, cropping, adjustment and annotation tools can use.

Primary interface:

`derive_plate_layout(project, image_uid) -> PlateLayout`

## Core rules

### Rows

For the current workflow, one vertical profile defines the physical row count. Its `Pos` values determine row ordering/occupation. Example: positions 1-8 mean an 8-row physical grid, regardless of repeated label text such as `0, -1, -2, -3, 0, -1, -2, -3`.

Do not infer row count from unique label values; repeated labels still occupy separate physical rows.

Current semantics support one vertical profile. Ignore workbook vertical-profile `Set` values. Multiple vertical-profile assignments should be reported as unsupported/ambiguous rather than guessed.

### Columns

Each strain profile's highest/extent of valid `Pos` defines that profile's logical width. The **widest assigned strain profile defines overall `grid_cols`**.

Examples:

- one strain profile with positions 1-12 -> 12 columns;
- two profiles where one has positions 1-10 and another 1-4 -> overall grid width remains 10;
- two profiles each positions 1-10 -> 10 columns.

Do not add profile widths together when profiles occupy different row bands.

### Multiple strain profiles / row bands

When an annotation set has multiple strain profiles, assignment `Order` defines top-to-bottom physical ordering:

- `Order=1` -> upper band;
- `Order=2` -> next band;
- later orders continue downward.

**Default mapping policy:** when the total physical row count divides evenly across the number of ordered strain profiles, distribute rows evenly. For the currently required 8-row/two-profile case, this means rows 1-4 and rows 5-8.

**Override policy:** equal division is a practical default, not an immutable scientific rule. `PlateLayout` or its derivation request must allow an explicit/manual row-band override later. If the total rows do not divide evenly, explicit assignment metadata exists, or the user supplies a manual mapping, use/report that instead of forcing equal division.

Do not infer row bands from strain label text.

## Required cases

### Single-profile 8 x 12

- vertical profile positions 1-8 -> `grid_rows=8`;
- strain profile positions 1-12 -> `grid_cols=12`;
- one strain band spans rows 1-8;
- strain positions map columns 1-12.

This represents the 14.08.26 / 15.08.26 style case.

### Two-profile 8 x 10

- vertical profile positions 1-8 -> 8 rows;
- strain profile A positions 1-10, `Order=1` -> default rows 1-4;
- strain profile B positions 1-10, `Order=2` -> default rows 5-8;
- overall grid width = 10;
- an explicit alternative row-band mapping can override the default.

This represents the 16.08.26 style case.

### Unequal widths across bands

Example:

- upper band positions 1-10;
- lower band positions 1-4;
- overall `grid_cols=10`;
- lower band remains a 4-column band within that wider logical grid rather than forcing the whole grid to 4 columns.

Preserve each band's own width separately from `grid_cols`.

## Label ordering

- `Pos` is authoritative for within-profile logical order.
- Labels may repeat; repeated text does not collapse positions.
- Missing/duplicate positions that prevent deterministic ordering should be surfaced clearly.
- Do not sort label text alphabetically.
- Preserve display text exactly; normalized comparison keys may be separate if needed.

## Grid coordinates as reusable project state

The logical `PlateLayout` and the later measured pixel grid are distinct but should join cleanly.

The production four-click route currently determines real image grid coordinates very well. Once those coordinates are registered for an image, downstream operations should be able to consume them later without rerunning alignment, including:

- whole-plate visibility adjustment using the grid area as the measurement ROI;
- crop export from raw/unprocessed images;
- later crop export from processed images;
- automatic annotation placement;
- matrix/composition selection.

Do not design the coordinate result as a transient side effect of crop export. A later integration should be able to run `align/register now, export later`.

The exact persisted pixel-coordinate schema may be a separate contract from logical `PlateLayout`; propose a narrow contract if needed rather than overloading logical metadata with image-runtime details.

## Relationship to four-click alignment

This prototype does **not** replace or reimplement the current Fiji four-click route. It provides logical geometry metadata that can later inform and consume alignment results:

- overall row/column counts;
- widest overall width;
- which rows belong to which strain profile;
- local width of each band;
- logical row/column identities.

Do not bake the current choice of clicked reference rows/columns into the `PlateLayout` contract. The working production alignment route remains authoritative and may choose suitable reference points independently.

## Basic CSV versus V10

The current basic CSV route has simpler semantics and need not implement V10 `Set`/annotation-set/profile-order behavior. This component is for the richer canonical model and should not force V10 layout semantics back into the basic CSV workflow.

## Suggested `PlateLayout` information

The exact schema is governed by `contracts/plate_layout.schema.json`, but the model should be able to represent at least:

- `layout_id` / annotation-set identity;
- `grid_rows`;
- `grid_cols`;
- ordered vertical positions/labels;
- strain bands;
- for each strain band: assignment order, profile identity, row start/end, local column count, ordered strain positions/labels;
- whether row bands came from default even distribution or an explicit override;
- enough logical row/column information for downstream annotation, composition, and alignment integration without reopening V10.

If the current schema cannot represent unequal band widths or explicit row-band overrides cleanly, propose a minimal contract revision.

## Validation/failure behavior

Report rather than guess when any of these prevent deterministic layout derivation:

- no vertical profile when row count is required;
- more than one active vertical profile under current semantics;
- zero/invalid positions;
- duplicate conflicting `Pos` values;
- multiple strain profiles without unique usable `Order` values;
- row count cannot be mapped by the default and no explicit override exists;
- annotation set references to missing profiles.

Harmless gaps may be represented if they have a clear logical meaning, but do not silently renumber user positions.

## Implementation posture

- Pure Python/model logic is appropriate here; no image-processing dependency should be required.
- Keep the component deterministic and easy to synthetic-test.
- Do not create GUI/controller dependencies.
- Do not over-generalize for hypothetical plate geometries before the required cases work.

## Out of scope

- pixel detection/alignment implementation;
- Fiji ROI creation;
- physical plate rotation estimation;
- annotation rendering;
- composition/image cropping;
- multiple vertical-profile-set behavior;
- arbitrary scientific interpretation of ambiguous row-band allocations.

## Success criteria

The prototype is `Proven` when targeted synthetic tests demonstrate:

1. 8x12 single-band derivation;
2. 8x10 two-band derivation using `Order` and default even row distribution;
3. explicit/manual row-band override;
4. widest-band-wins overall columns;
5. unequal-width bands preserve both overall and local widths;
6. repeated vertical label text still yields separate rows via `Pos`;
7. ambiguous inputs fail/report clearly rather than guessing;
8. output validates against the shared `PlateLayout` contract or a narrowly proposed revision.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface: `derive_plate_layout(project, image_uid) -> PlateLayout`
- Tests:
- Dependencies:
- Proven cases:
- Default/override row-band behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
