# Project setup / UID-safe working-copy renaming handoff

Status: Planned

## Goal

Create a focused project-setup component that uses canonical V10 metadata to prepare the working project tree and optionally rename working copies of raw images without altering the raw originals.

This replaces the old need to manually/script-rename source files before downstream processing while preserving a simple audit trail.

## Required folder behavior

The project root should support sibling working areas such as:

- `raw/` — authoritative untouched source images, retaining names such as `image1.jpg`, `image2.jpg`, etc.;
- `working/` — duplicated working copies that may receive V10-derived human-readable names;
- later output parents such as crops/matrices/processed/annotated according to the production integration.

The setup component should not move/rename the authoritative raw originals merely to make downstream matching easier.

## Renaming is optional

Renaming must remain optional.

Downstream identity should rely on structured `Image UID`/session metadata rather than requiring every physical file to have a descriptive filename. A project containing repeated generic source names such as `image1.jpg` in different raw date/session folders must still be processable when V10 assigns unique identities.

If renaming is enabled, rename/copy the **working copies**, not the raw originals.

## V10-derived names

Working filenames should use the intended V10 `Working filename`/nomenclature rather than inventing a second naming scheme.

The exact human-readable filename may contain experiment/media/condition/etc. according to V10, but `Image UID` remains the identity. Similar-looking names must therefore not create ambiguity internally.

Comparison should be case-insensitive where semantically appropriate while preserving original display capitalization.

## Conversion/audit text file

At project root, generate/update a small human-readable text mapping that records raw-to-working name conversions, for example conceptually:

`image1.jpg -> ypda+type1,01.jpg`

Requirements:

- group entries with clear dividers/headings by experiment and Set for easy visual checking;
- include enough identity information (preferably Image UID and/or sessionUID) to disambiguate similar filenames;
- preserve original raw relative path/name;
- preserve working relative path/name;
- deterministic ordering;
- append/regenerate safely rather than silently losing prior mappings;
- no private absolute machine paths.

This file is a human QC aid, not the canonical machine database.

## Reconciliation behavior

The component should be able to match V10 expected image records to raw files using structured metadata/known folder context without requiring the final working filename to already exist.

Incomplete image sets are valid. Expected-but-missing files should be reported rather than blocking creation of working copies for the images that are present.

Ambiguous matches must be surfaced, not guessed.

## Safety/idempotence

Running setup repeatedly should not create endless duplicate working copies or rename chains.

Before copying/renaming:

- detect whether the target working copy already corresponds to the same Image UID/source;
- avoid overwriting a different image merely because its proposed filename collides;
- produce clear collision/ambiguity diagnostics;
- preserve raw originals unchanged.

## Interface

Conceptually:

`prepare_working_copy(project_model, raw_root, working_root, options) -> RenameResult`

Result should include per-image disposition such as copied/unchanged/missing/ambiguous/collision plus conversion-map output path.

## Mini-app option

A small setup applet may show:

- project/V10 source;
- raw and working roots;
- rename-working-copies toggle;
- preview of proposed mappings;
- missing/ambiguous records;
- apply/setup action.

Preview should not modify files.

## Out of scope

- pixel processing;
- plate orientation/cropping;
- four-click grid registration;
- annotation rendering;
- modifying raw filenames in place by default;
- forcing descriptive filenames as identity.

## Required proofs

1. generic `image1/image2/...` raw files remain untouched;
2. optional working copies receive V10-derived names;
3. Image UID keeps similar names unambiguous;
4. conversion text file is grouped by experiment/Set and human-readable;
5. rerunning is idempotent;
6. incomplete expected set does not block present images;
7. collision/ambiguity is reported safely;
8. preview performs no writes.

## Completion record

When proven, update with:

- Branch:
- Commit:
- Interface:
- Tests:
- Dependencies:
- Folder behavior proven:
- Mapping-file format:
- Collision/idempotence behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
