# Shared prototype contract

These schemas are the versioned handshake between integrated applet cores, durable project state, and production adapters. They remain intentionally narrower than GUI/runtime implementation details.

Current contract version: **1**.

## Core flow

```text
V10 adapter -> ProjectModel + PlateLayout
                  -> WorkflowProjectState
image -> RotationResult / CropResult / VisibilityResult / AnnotationResult
accepted four-point registration -> GridCoordinateAsset
                  -> visibility / annotation / CultureCropExport
recorded culture crops -> MixedTierMatrix
```
The contracts describe stable data boundaries, not GUI/runtime implementation details.

## ProjectModel

`project_model.schema.json` contains sessions/images and the metadata required by downstream tools. V10 terminology is preserved where practical. Image identity is `image_uid`; `original` and `working_filename` are locators/names rather than identity.

Filesystem source paths, Fiji handles, AHK state, temporary macro paths, window coordinates and other runtime-specific state do not belong here.

## PlateLayout

`plate_layout.schema.json` is normalized/derived layout data. It should hide workbook-specific quirks from downstream annotation and processing components.

For current prototype scope:

- one vertical profile is used for grid-row derivation;
- workbook `Set` values in vertical-profile tables are ignored;
- a single strain band may span all rows;
- multiple strain-label bands are ordered top-to-bottom;
- the widest strain band determines `grid_cols`;
- two-band 8-row layouts may resolve to rows 1-4 / 5-8 when the source metadata makes that deterministic.

## GridCoordinateAsset

`grid_coordinate_asset.schema.json` persists accepted source-image geometry independently of immediate crop export. It declares pixel-axis semantics and dimensions, the four measured reference points, interpolation provenance, row and column coordinates, and every named `rNcM` spot. Runtime adapters expose the same asset as ordered spots or `(row, column)` mappings for mature existing consumers.

## WorkflowProjectState and derivative contracts

`workflow_project_state.schema.json` is the durable integration manifest. It embeds canonical project/layout data and records per-image setup, orientation, crop, grid, visibility, annotation, and culture-export state plus project-level matrix exports.

`crop_size_calibration.schema.json`, `crop_result.schema.json`, `visibility_result.schema.json`, `annotation_request.schema.json`, and `annotation_result.schema.json` keep each applet boundary explicit. `culture_crop_export.schema.json` records immutable later exports with source/grid/layout provenance. `mixed_tier_matrix.schema.json` records verified per-cell crop choices, including mixed Top/Low tiers, layout, and immutable output provenance.

## RotationResult

`rotation_result.schema.json` intentionally knows nothing about colony/grid alignment. It represents an isolated estimate of physical whole-plate rotation so the integration layer can decide whether/how to apply it later.

## Contract changes

Do not expand these schemas pre-emptively. If a prototype needs a new shared field:

1. document the actual use case in the prototype HANDOFF;
2. propose the smallest backward-compatible addition where practical;
3. do not silently redefine an existing field;
4. increment `contract_version` only for genuinely incompatible structural/semantic changes.

Prototype-internal settings and implementation details should remain outside the shared contract.