# Workflow controller

`tools/workflow_controller.py` is intentionally orchestration-only. The active Windows launcher uses `tools/workflow_controller_extended.py`, which subclasses that base controller and adds lightweight project/output conveniences. Paths/settings are stored in `~/.cautious-rotary-phone/config.json`; Fiji, AHK, ROI 1-click Tools and Pillow remain the processing tools.

Current required runtime target is **Windows + Miniforge `workflow-c` Python 3.11**. The unified launcher chooses that runtime first; fallback interpreters are used only if it is unavailable.

Current controls include CSV validation/metadata review, ROI presets, batch preflight, single-image and batch four-point alignment/export, the safe staged Pillow jobs, focused/custom composition, preferred-WT output, processing-log navigation, runtime reset/reboot controls, and direct opening of routine folders.

## Automatic project layout

The extended controller can derive routine filesystem paths from one selected **Image root**. A project prefix defaults to local `dd.mm.yy` but accepts ordinary text such as `ATTEMPT1`.

For source folder `MyImages` and prefix `21.08.26`:

```text
21.08.26_MyImages/
    Raw/MyImages/      <- original selected folder moved intact here
    Crops/
    Matrices/
    Metadata/
```

The controller fills `image_root`, `crop_output` and `matrix_output` automatically. It shows the planned move and asks before changing the source path. No image is rewritten/recompressed/copied; the source folder is moved/renamed on the same filesystem. Existing initialized Raw layouts reconnect idempotently and existing destination projects are never merged automatically.

Configured CSV paths inside a moved source tree are rebased to their new Raw location; external CSV paths remain unchanged. Project CSV folder discovery supports case-insensitive longer filenames containing `grid.csv`, `images.csv` or `condition_order.csv`, and ambiguous matches fail closed.

Detailed contract: `docs/development/PROJECT_LAYOUT.md`.

## Processing / ROI settings

Processing settings remain simple persisted values rather than a processing subsystem. Downstream launch wrappers still validate their own inputs.

ROI presets refer to the small per-culture box used by the mature ROI 1-click route/QC geometry. The one-plate proof does **not** create its own 108x108 click box. The installed ROI 1-click Rotated Rectangle Click Tool supplies the selection and the patched plugin restores saved rectangle/shared click preferences on fresh Fiji sessions. Optional workflow presets may override only width/height/angle.

## One-plate four-point proof — current desktop priority

`Run one-plate 4-point proof (choose plate)` is the active desktop validation route. It preserves the established four-point mathematical geometry using R1C1, R1C(last), R5C1 and R5C(last), then shows a full-grid QC before crop export.

Current proof behavior:
- block only if the exact selected proof-plate window is already open; unrelated Fiji images do not block;
- launch the prepared macro through the configured Fiji/Jaunch executable with `--no-splash` and rely on the installation's intentional single-instance behavior;
- use the mature ROI 1-click custom Rotated Rectangle Click Tool, not ImageJ's built-in rotated rectangle;
- make a disposable alignment duplicate and run whole-image CLAHE twice; there is **no central sampling ROI**;
- CLAHE uses `max(400, round(4 * max(rect.width, rect.height)))`, histogram 256, maximum slope 1000;
- calculate the full 8 x N grid mathematically from the four clicks;
- draw QC boxes/lines from the grid vectors so they rotate/skew with the plate rather than remaining screen-axis aligned;
- export fixed-size crops from the unchanged original source image after QC acceptance.

Existing-Fiji reuse remains a real desktop validation point. Repeated launcher invocation has produced delayed status windows and Macro Runner lifecycle problems, so do not claim ownership/control is proven until the architecture proof in `docs/research/fiji-four-point-runtime.md` succeeds.

## Batch preflight and alignment routes

Batch preflight keeps modal feedback short and writes the detailed report to the configured/global application area. A project-local report destination is a future convenience, not a current blocker.

The active batch route is **Run all 4-point** or **Run subfolder**. It prepares the current four-point macro, starts the AHK helper when needed, and launches the configured Fiji executable. Batch controls retain Skip done, accepted-grid replacement, optional grid QC, source hiding, cancellation cleanup, and explicit stale-marker reset.

## AHK v2 helper

The alignment helper is AutoHotkey **v2** and must stay thin. It recognizes placement dialogs for both alignment routes, uses a bounded three-second catch-up scan to move delayed Java dialogs upper-left, positions the already-visible Fiji toolbar upper-right, and hides/lowers the Jaunch launcher status window. It is convenience window management, not Fiji process/session authority.

Z advances/accepts recognized dialogs, X selects Retry on either `Alignment QC` or `Full-grid QC`, and Esc exits the helper. Do not reintroduce AHK v1 syntax; v2 output variables such as `WinGetPos` outputs require `&`.

## Pillow / output orchestration

Pillow output jobs run through `tools/run_existing_pillow_from_config.py`. The wrapper validates readiness, stages only exact current crops in a disposable directory, normalizes orientation on copies, and runs the established Pillow composition scripts. Missing/duplicate/incompatible crop errors are surfaced and real `crop_output` images are not rotated or rewritten.

The retired direct matrix launcher remains intentionally absent; the controller must not bypass validated staging. Focused/custom composition stays a thin adapter over the mature renderer rather than becoming a replacement figure editor.

## Windows launchers

`start_controller.cmd` is the single production controller launcher. It uses Miniforge `workflow-c` Python 3.11 first, with availability-only compatible fallbacks. A failure or Ctrl+C ends that launch cleanly; it does not start another interpreter.

`start_controller_private_test.cmd` sets isolated temporary paths for image-blind validation, then delegates to the same production launcher. `start_custom_matrix.cmd` is separate because it opens the Custom matrices mini-app, but follows the same Miniforge-first selection policy.