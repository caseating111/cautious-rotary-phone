# Image-blind local Fiji testing contract

This is a hard privacy/testing rule for local Codex work on `workflow-C`.

## Inviolable model-input rule

Real/sample experimental images and any pixel-bearing derivatives must **not** be opened, rendered, previewed, OCRed, screenshotted, encoded, attached, summarized visually, or otherwise supplied to Codex/another model context.

The agent may pass filesystem paths to local programs such as Fiji/ImageJ, AutoHotkey v2, Python subprocesses, or deterministic utilities **without reading image pixels itself**. The agent may consume only non-pixel telemetry such as:

- existence / open-success / exit status;
- filename/basename and sanitized path references;
- width, height, bit depth, channel/slice/frame counts;
- ROI count, ROI bounds, centres, angles and other numeric geometry;
- crop/output counts and expected-vs-actual filenames;
- Fiji/ImageJ textual logs, parser errors, stack traces and macro line numbers;
- generated macro/AHK/Python source text;
- window titles, handles, coordinates and dimensions;
- timing, return codes and deterministic checksums where useful;
- CSV/JSON/text metadata that the user has deliberately made non-sensitive.

If a decision genuinely requires seeing pixels, the agent must stop that sub-check, write a concise `MANUAL_VISUAL_VALIDATION_REQUIRED` item in `docs/development/MANUAL_VALIDATION_BACKLOG.md`, and continue with any remaining image-blind checks/work that is not blocked by it.

## Mandatory preflight before every real-image/Fiji verification

Before **every** check that will cause real/sample images to be opened or processed by Fiji or another local image tool, Codex must first run:

```powershell
python .\tools\check_image_blind_paths.py C:\path\to\the\active\config.json
```

Use the actual active local config path. Codex must report the privacy-check result to the user before starting the real-image verification. Proceed only on `IMAGE-BLIND PRIVACY CHECK: PASS`.

If the privacy check fails, do not launch/process the real images. Fix the path/Git/privacy issue if it is safely within scope, or log the blocker. Continue unrelated safe work within the current task where possible rather than stopping the whole session.

The privacy preflight itself must remain image-blind: it may inspect paths, config text and Git metadata, but not image pixels.

## Storage boundary

Pixel-bearing files belong outside the Git worktree. Recommended layout:

```text
C:\LocalWorkflowData\
├── Images\                 # optional; real images may live elsewhere
├── PrivateTemp\            # Fiji/Java/OS temp; private/pixel-bearing possible
│   ├── Windows\
│   └── Java\
├── Crops\                  # derived pixel outputs
├── Matrices\               # derived pixel outputs
└── Metadata\               # user-sanitized CSV/config files
```

Real images do **not** need to live under `C:\LocalWorkflowData`; any external folder is acceptable as long as the active config points to it and the privacy check passes.

Codex-readable telemetry may be written to the ignored worktree directory:

```text
<repo>\.local-test-telemetry\
```

That directory must contain text/JSON/CSV/log/geometry data only. Never place screenshots, thumbnails, previews, crops or other pixel-bearing files there.

## Temp redirection and default launch path

For privacy-sensitive controller tests, use `start_controller_private_test.cmd` by default. It sets process-local `TEMP`, `TMP`, and Java `java.io.tmpdir` to the external `C:\LocalWorkflowData\PrivateTemp` tree and then invokes the **unified Miniforge-first controller launcher** (`start_controller.cmd`). Child processes launched by the controller inherit these locations.

Do not use Anaconda/conda for the default private-test route. Anaconda integration is deferred unless the user explicitly requests it later.

For a direct Fiji test that does not start through the controller, use `tools/start_fiji_private_test.ps1 -FijiExecutable <path> [Fiji args...]`. It applies the same private TEMP/TMP/java.io.tmpdir boundary to the Fiji process without globally changing Windows or Java settings.

Do not globally modify the user's Windows TEMP/TMP or Java configuration merely for this project.

A Fiji process that was already running before either private launcher started did **not** inherit these process-local temp settings. Both private launch routes therefore refuse an already-running `ImageJ-win64` process. Close Fiji first and let the private launcher start the test instance.

The launchers redirect conventional Windows/Java temporary storage. Fiji plugins can still choose their own explicit output paths; any plugin/script that writes pixel-bearing intermediates must be configured to use the external private tree rather than the repository or telemetry directory.

## Agent behavior around external image paths

The image directories may be outside the Codex worktree. That is intentional. The workflow should pass paths to Fiji rather than copying files into the repository.

If Codex/default sandbox permissions block invocation against an external path, request the narrow permission needed to launch/use that path. Do not solve the permission problem by copying the images into the worktree.

The fact that the agent's OS account technically has filesystem permission to a path is not permission to inspect its pixel contents. The no-view rule still applies.

## Git/exfiltration guard

`.gitignore` rejects common image formats and known local/private test directories. This is defense in depth, not the primary rule. Before any push after privacy-sensitive testing, inspect `git status --short` and the staged diff. Do not stage binary/image files, private local paths containing identifying information, screenshots, or raw Fiji image outputs.

Run `tools/check_image_blind_paths.py <local-config.json>` before privacy-sensitive testing and again before a push after such testing. It checks paths/Git state only and does not open image contents. It fails if configured image/crop/matrix or private temp roots are inside the worktree, or if image-format files are tracked/staged.

External reviewer/model packets (including Antigravity/Gemini) must contain only bounded source diffs, generated script text, sanitized logs, geometry/telemetry and explicit review questions. Never send real/sample images or screenshots of them.

## Manual validation backlog

Manual point placement or visual judgement should be accumulated in `docs/development/MANUAL_VALIDATION_BACKLOG.md` rather than interrupting Codex repeatedly. Codex should continue safe task-relevant work while backlog items are pending whenever those results are not blocking that work, then batch the manual checks for the user at a natural checkpoint.

## What automated testing should produce

Prefer telemetry records such as:

```json
{
  "image_opened": true,
  "width": 1750,
  "height": 1750,
  "channels": 1,
  "roi_count": 4,
  "macro_completed": false,
  "error_line": 388,
  "output_crop_count": 24,
  "window": {"x": 10, "y": 10, "width": 420, "height": 100}
}
```

The model may reason about these values. It must not request or generate a screenshot merely to make automated testing easier.

## Scope and security boundary

This privacy rule outranks convenience, debugging speed and the normal desire to automate desktop validation. A visual-only problem may remain for the user; that is preferable to exposing the images to model context.

This repository policy plus path/Git guards strongly prevents accidental model/Git exposure, but it is not an operating-system access-control boundary: a Codex process running as the same Windows user may technically have filesystem permission to external files. The rule is therefore that the agent must not exercise that capability. A true OS-enforced separation would require a separate Windows identity/sandbox for Fiji versus Codex, which is intentionally not introduced unless the user asks for that additional complexity.
