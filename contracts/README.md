# Shared prototype contract

These schemas are the small versioned handshake between isolated prototype components and the eventual integration layer. They are intentionally narrower than the full application.

Current contract version: **1**.

## Core flow

```text
V10/other metadata adapter
        -> ProjectModel v1
        -> PlateLayout v1
        -> annotation/composition tools

accepted Fiji four-point alignment
        -> GridCoordinateAsset v1
        -> visibility/annotation/crop consumers

image path
        -> whole-plate rotation prototype
        -> RotationResult v1
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

## RotationResult

`rotation_result.schema.json` intentionally knows nothing about colony/grid alignment. It represents an isolated estimate of physical whole-plate rotation so the integration layer can decide whether/how to apply it later.

## Contract changes

Do not expand these schemas pre-emptively. If a prototype needs a new shared field:

1. document the actual use case in the prototype HANDOFF;
2. propose the smallest backward-compatible addition where practical;
3. do not silently redefine an existing field;
4. increment `contract_version` only for genuinely incompatible structural/semantic changes.

Prototype-internal settings and implementation details should remain outside the shared contract.