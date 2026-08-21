# Automatic project layout

The active extended controller can derive a complete working folder layout from one selected **Image root**.

## Default layout

With source folder:

`.../MyImages`

and the default prefix on 21 August 2026:

`21.08.26`

initialization creates:

```text
.../21.08.26_MyImages/
    Raw/
        MyImages/          <- original selected image-root folder, moved intact
    Crops/
    Matrices/
    Metadata/
```

The controller then sets:
- `image_root` -> `Raw/MyImages`
- `crop_output` -> `Crops`
- `matrix_output` -> `Matrices`

Existing exact-named project CSVs are also picked up automatically when found in `Metadata`, the project root, or the original image-root parent. Existing nonblank CSV selections are preserved. If a configured CSV path was physically inside the selected image root, that path is rebased to the same relative file under the moved `Raw/MyImages` folder so the move does not leave a broken config path. External CSV paths are unchanged.

## Prefix

The GUI prefix defaults to the local current date in `dd.mm.yy` form. It is deliberately free text rather than a date-only field; examples such as `ATTEMPT1` are valid and produce `ATTEMPT1_MyImages`.

Windows-invalid characters and semicolons are rejected because they are unsafe for the existing Fiji/path handoffs.

## Source safety

Initialization does **not** rewrite, rotate, recompress or individually copy source images. The project folder is created beside the selected image root, then the selected folder itself is renamed/moved into `Raw`. On the same filesystem this is a directory rename; image bytes are untouched.

Because the source path changes, external shortcuts or unrelated software that refers to the old absolute path may need updating. The controller therefore shows the exact planned paths and asks once before performing a new move.

Selecting an already initialized `.../Raw/<ImageRootName>` is idempotent: the controller reconnects `Crops`, `Matrices` and `Metadata` rather than nesting or moving the raw folder again.

If the target project folder already exists, initialization refuses to merge/overwrite it automatically.

## Implementation

- `tools/project_layout.py`
- `tools/workflow_controller_extended.py`
- `tests/test_project_layout.py`
- `tests/test_project_layout_controller_contract.py`
