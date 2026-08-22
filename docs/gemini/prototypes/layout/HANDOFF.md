# Grid/layout derivation prototype handoff

Status: Planned

## Goal

Derive a deterministic `PlateLayout` from normalized project/annotation metadata without depending on Fiji, image pixels, or the current controller. This component translates annotation profile structure (`Pos`, vertical labels, strain-profile `Order`) into logical grid dimensions and row bands that downstream alignment/annotation tools can use.

Primary interface:

`derive_plate_layout(project, image_uid) -> PlateLayout`

## Core rules

### Rows

For the current workflow, one vertical profile defines the physical row count. Its `Pos` values determine row ordering/occupation. Example: positions 1-8 mean an 8-row physical grid, regardless of repeated label text such as `0, -1, -2, -3, 0, -1, -2, -3`.

Do not infer row count from unique label values; repeated labels still occupy separate physical rows.

Current semantics support one vertical profile. Ignore workbook vertical-profile `Set` values. Multiple vertical-profile assignments should be reported as unsupported/ambiguous rather than guessed.

### Columns

Each strain profile's highest valid `Pos` defines that profile's logical width. The **widest assigned strain profile defines overall `grid_cols`**.

Examples:

- one strain profile with positions 1-12 -> 12 columns;
- two profiles where one has positions 1-10 and another 1-4 -> overall grid width remains 10;
- two profiles each positions 1-10 -> 10 columns.

Do not add profile widths together when profiles occupy different row bands.

### Multiple strain profiles / row bands

When an annotation set has multiple strain profiles, assignment `Order` defines top-to-bottom physical ordering:

- `Order=1` -> upper band;
- `Order=2` -> next band;
- additional orders, if later supported, continue downward.

For the currently required 8-row/two-profile case, two ordered strain profiles divide the plate into top 4 rows and bottom 4 rows.

If total rows divide evenly by the number of ordered strain profiles, distribute rows evenly. If not, do not silently invent a scientifically meaningful grouping unless the metadata/contract explicitly defines it. Surface ambiguity or use a documented deterministic policy only if later approved.

For the discussed alignment helper, the second alignment/reference row can be derived from vertical-row count as `ceil(rows * 0.5) + 0` in 1-based practical terms equivalent to `(0.5 * total_rows) + 1` rounded up where needed; e.g. 8 rows -> row 5. The exact alignment UI remains outside this prototype, but `PlateLayout` should expose row bands/reference information cleanly enough for downstream code to choose top row plus the first row of the lower half/band.

## Required cases

### Single-profile 8 x 12

- vertical profile positions 1-8 -> `grid_rows=8`;
- strain profile positions 1-12 -> `grid_cols=12`;
- one strain band spans rows 1-8;
- strain positions map columns 1-12.

This represents the 14.08.26 / 15.08.26 style case.

### Two-profile 8 x 10

- vertical profile positions 1-8 -> 8 rows;
- strain profile A positions 1-10, `Order=1` -> rows 1-4;
- strain profile B positions 1-10, `Order=2` -> rows 5-8;
- overall grid width = 10.

This represents the 16.08.26 style case.

### Unequal widths across bands

Example:

- upper band positions 1-10;
- lower band positions 1-4;
- overall `grid_cols=10`;
- lower band remains a 4-column band within that wider logical grid rather than forcing the whole grid to 4 columns.

Downstream alignment should be able to use a row/band with fewer columns for local positioning/rotation references while retaining the widest grid for overall physical width. Therefore preserve each band's own width separately from `grid_cols`.

## Label ordering

- `Pos` is authoritative for within-profile logical order.
- Labels may repeat; repeated text does not collapse positions.
- Missing/duplicate positions that prevent deterministic ordering should be surfaced clearly.
- Do not sort label text alphabetically.
- Preserve display text exactly; normalized comparison keys may be separate if needed.

## Suggested `PlateLayout` information

The exact schema is governed by `contracts/plate_layout.schema.json`, but the model should be able to represent at least:

- `layout_id` / annotation-set identity;
- `grid_rows`;
- `grid_cols`;
- ordered vertical positions/labels;
- strain bands;
- for each strain band: assignment order, profile identity, row start/end, local column count, ordered strain positions/labels;
- enough logical row/column information for downstream annotation, composition, and alignment components without reopening V10.

If the current schema cannot represent unequal band widths or ordered row bands cleanly, propose a minimal contract revision rather than embedding workbook-specific assumptions in downstream tools.

## Validation/failure behavior

Report rather than guess when any of these prevent deterministic layout derivation:

- no vertical profile when row count is required;
- more than one active vertical profile under current semantics;
- zero/invalid positions;
- duplicate conflicting `Pos` values;
- multiple strain profiles without unique usable `Order` values;
- non-contiguous/ambiguous ordering where the intended physical layout cannot be established;
- annotation set references to missing profiles.

Harmless gaps may be represented if they have a clear logical meaning, but do not silently renumber user positions.

## Relationship to four-click alignment

This prototype does **not** implement the current Fiji four-click route. It only provides logical geometry metadata that can later inform alignment:

- overall row/column counts;
- widest overall width;
- which rows belong to which strain profile;
- local width of each band;
- sensible logical reference rows.

The current production alignment implementation remains owned by `workflow-C` and must not be modified here.

## Implementation posture

- Pure Python/model logic is appropriate here; no image-processing dependency should be required.
- Keep the component deterministic and easy to synthetic-test.
- Do not create GUI/controller dependencies.
- Do not over-generalize for hypothetical plate geometries before the required cases work.

## Out of scope

- pixel coordinates;
- Fiji ROI creation;
- physical plate rotation estimation;
- annotation rendering;
- composition/image cropping;
- multiple vertical-profile-set behavior;
- arbitrary scientific interpretation of ambiguous row-band allocations.

## Success criteria

The prototype is `Proven` when targeted synthetic tests demonstrate:

1. 8x12 single-band derivation;
2. 8x10 two-band top/bottom derivation using `Order`;
3. widest-band-wins overall columns;
4. unequal-width bands preserve both overall and local widths;
5. repeated vertical label text still yields separate rows via `Pos`;
6. ambiguous inputs fail/report clearly rather than guessing;
7. output validates against the shared `PlateLayout` contract or a narrowly proposed revision.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface: `derive_plate_layout(project, image_uid) -> PlateLayout`
- Tests:
- Dependencies:
- Proven cases:
- Ambiguity behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
