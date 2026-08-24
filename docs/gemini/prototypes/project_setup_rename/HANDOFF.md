# Project setup / UID-safe working-copy renaming handoff

Status: INTEGRATED

Integrated on `workflow-integrated` at `c31d4f1`. `ProjectWorkflow` and the V10 applet GUI preview reconciliation, optionally create UID-safe Working copies without changing raw sources, persist dispositions, and write the human audit map.

## Goal

Create a focused project-setup component that uses canonical V10 metadata to prepare the project tree and optionally create human-readable renamed **working copies** of raw images without altering raw originals.

This replaces the old requirement to manually/script-rename source files before downstream processing while preserving an easy human audit trail.

See `docs/gemini/FUTURE_WORKFLOW.md` and `docs/development/PROJECT_ASSET_CONTRACT.md`.

## Intended project tree

The exact names remain configurable, but the project root should conceptually support sibling areas such as:

```text
<project>/
  raw/
  working/
  processed/
  annotated/
  crops/
    unprocessed/
    processed/
  matrices/
  state/            # or another unobtrusive machine-state location
  image_name_conversions.txt
```

Preserve experiment/date/Set/Condition subfolders where they are useful. Do not flatten everything merely because canonical UIDs exist.

The setup component may create only the folders required/selected for the current run, but the structure should be compatible with later stages rather than inventing unrelated trees per mini-app.

## Raw source rule

`raw/` is authoritative untouched input.

Files may retain generic camera/export names such as:

- `image1.jpg`;
- `image2.jpg`;
- repeated generic names in different session/date folders.

Do not rename/move the authoritative raw image merely to make later matching easier.

## Renaming is optional

The user must be able to choose:

- **keep generic names** and process through UID/path mapping; or
- **create renamed working copies** using V10 nomenclature.

Downstream identity relies on structured `Image UID`/session metadata, not on requiring descriptive filenames.

If renaming is enabled, create/copy the `working/` derivative and use V10 `Working filename` semantics. If renaming is disabled, a working copy may keep its original generic filename or downstream steps may operate through the mapped source according to integration policy.

## UID-safe naming and collisions

`Image UID` remains canonical identity even when two human-readable names are similar.

Do not automatically clutter every human filename with a UID if the V10 working name is already unique and readable. Instead:

1. use canonical UID internally;
2. preview proposed names;
3. detect filesystem collisions before writing;
4. if two different UIDs would collide, report clearly and apply a deterministic UID-aware suffix/disambiguation only when needed or after user-approved policy.

Case-only differences should not create accidental Windows collisions.

## Step-by-step intended user function

1. User selects/loads canonical V10 project state.
2. User selects/confirms project root/raw root if not already known.
3. App scans only expected source locations needed for mapping.
4. Reconcile present physical raw files to expected image records/UIDs.
5. Show a concise preview table: raw relative path -> UID -> proposed working relative path/name -> disposition.
6. Missing expected files are listed but do not block present files.
7. Ambiguous/collision records are blocked individually rather than guessed.
8. User chooses whether renamed working copies should be created.
9. Apply setup: create required parent/subfolders and copy/rename working derivatives as selected.
10. Write/update human-readable conversion map at project root.
11. Save machine state so rerunning setup is idempotent and does not create duplicate rename chains.

Preview performs no writes.

## V10-derived names

Use V10 `Working filename`/nomenclature rather than inventing a second unrelated naming scheme.

The adapter/project model supplies Experiment, Set, Media, Condition, replicate, Image UID and other relevant context. The setup component should consume structured fields rather than parse identity back out of a human filename.

Generic raw filenames remain valid because reconciliation maps them to UID before renaming.

## Conversion/audit text file

At project root generate/update a small human-readable conversion file, e.g. `image_name_conversions.txt`.

Conceptual entry:

`image1.jpg -> ypda+type1,01.jpg`

Format requirements:

- clear divider/header for each Experiment;
- within experiment, clear Set headings/dividers when Set exists;
- optionally Condition grouping if it improves readability without duplicating information;
- original raw relative path/name;
- resulting working relative path/name;
- Image UID (and sessionUID when useful) for disambiguation;
- deterministic stable ordering;
- no absolute private machine paths;
- regeneration/update must not silently delete useful historical mapping for the same project state.

This file is for human visual checking, not the canonical machine database.

## Incomplete datasets

Expected-but-missing images are normal. Setup should create working copies for present images while recording missing expected records.

Do not require every expected V10 image before project setup can proceed.

## Idempotence/safety

Repeated setup must not create:

- `working/working/...` chains;
- `RENAMED RENAMED ...` filename chains;
- duplicate copies of the same UID/source;
- overwrites of a different UID because display names collide.

Use UID/source mapping and saved state to decide whether a working copy is already current.

## Output/future integration

Result concept:

`prepare_working_copy(project_model, raw_root, working_root, options) -> RenameResult`

Per image disposition may include:

- `COPIED_RENAMED`;
- `COPIED_ORIGINAL_NAME`;
- `UNCHANGED_CURRENT`;
- `EXPECTED_NOT_PRESENT`;
- `AMBIGUOUS_SOURCE`;
- `TARGET_COLLISION`;
- `SKIPPED`.

Return conversion-map path and created folder information.

Later orientation/crop/grid mini-apps consume Image UID + working path from project state; they do not redo source reconciliation.

## Required proofs

1. generic raw names remain untouched;
2. optional renamed working copies receive V10 working names;
3. rename-disabled mode still produces usable UID/path mapping;
4. similar names stay unambiguous through UID;
5. Windows case-only collision is caught;
6. conversion file grouped by Experiment/Set is easy to scan;
7. rerunning is idempotent;
8. incomplete expected set does not block present images;
9. ambiguous/collision cases are reported, not guessed;
10. preview performs no writes;
11. resulting project tree is compatible with processed/annotated/crop/matrix stages.

## Out of scope

- image pixel processing;
- plate orientation/cropping;
- four-click grid registration;
- annotation rendering;
- modifying raw filenames in place by default;
- forcing descriptive filenames as identity.

## Completion record

- Branch:
- Commit:
- Interface:
- Tests:
- Dependencies:
- Folder tree behavior:
- Rename-disabled behavior:
- Mapping-file format:
- Collision/idempotence behavior:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
